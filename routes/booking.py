import logging
from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request, Response, jsonify
from flask_login import login_required, current_user
from flask_mail import Message
from models import Doctor, Booking, ContactMessage, User
from forms import BookingForm
from extensions import db, mail

booking_bp = Blueprint("booking", __name__, url_prefix="/booking")
logger = logging.getLogger(__name__)


@booking_bp.route("/book", methods=["GET", "POST"])
@login_required
def book():
    form = BookingForm()
    doctors = Doctor.query.filter_by(available=True).all()
    form.doctor_id.choices = [
        (d.id, f"{d.name} — {d.hospital}") for d in doctors]

    if form.validate_on_submit():
        booking = Booking(
            user_id=current_user.id,
            doctor_id=form.doctor_id.data,
            patient_name=form.patient_name.data,
            patient_email=form.patient_email.data,
            patient_phone=form.patient_phone.data,
            appointment_date=form.appointment_date.data,
            appointment_time=form.appointment_time.data,
            reason=form.reason.data,
        )
        db.session.add(booking)
        db.session.commit()
        logger.info("Booking created: ID=%s for %s",
                    booking.id, booking.patient_email)

        # Email confirmation
        if current_app.config.get("MAIL_ENABLED"):
            doctor = Doctor.query.get(form.doctor_id.data)
            msg = Message(
                subject="Your Appointment Confirmation – MedApp",
                recipients=[booking.patient_email],
                html=render_template(
                    "email/confirm.html",
                    booking=booking,
                    doctor=doctor,
                ),
            )

            # Send asynchronously
            import threading
            app = current_app._get_current_object()

            def send_async_email(app_obj, message):
                with app_obj.app_context():
                    try:
                        mail.send(message)
                    except Exception as e:
                        app_obj.logger.warning(
                            "Could not send confirmation email: %s", e)

            threading.Thread(target=send_async_email, args=(app, msg)).start()

        flash("Appointment booked successfully! A confirmation has been sent to your email.", "success")
        return redirect(url_for("booking.confirmation", booking_id=booking.id))

    # Pre-fill name/email from current user
    if not form.patient_name.data:
        form.patient_name.data = current_user.name
        form.patient_email.data = current_user.email

    return render_template("book.html", form=form, doctors=doctors)


@booking_bp.route("/dashboard")
@login_required
def dashboard():
    my_bookings = (
        Booking.query
        .filter_by(user_id=current_user.id)
        .order_by(Booking.appointment_date.desc(), Booking.appointment_time.desc())
        .all()
    )

    queue_filter = request.args.get('queue_filter', 'today')
    today_date = date.today()
    if queue_filter == 'today':
        start_date = today_date
        end_date = today_date
    elif queue_filter == 'tomorrow':
        start_date = today_date + timedelta(days=1)
        end_date = today_date + timedelta(days=1)
    elif queue_filter == '7days':
        start_date = today_date
        end_date = today_date + timedelta(days=7)
    else:
        start_date = today_date
        end_date = today_date

    # Appointment Queue Visibility Logic
    queue_bookings = []
    if current_user.is_admin:
        queue_bookings = Booking.query.filter(
            Booking.appointment_date >= start_date,
            Booking.appointment_date <= end_date,
            Booking.status == 'confirmed'
        ).order_by(Booking.appointment_date, Booking.appointment_time).all()

    elif current_user.role == 'doctor' and current_user.doctor_profile:
        hospital = current_user.doctor_profile.hospital
        hospital_doctors = Doctor.query.filter_by(hospital=hospital).all()
        doc_ids = [d.id for d in hospital_doctors]
        if doc_ids:
            queue_bookings = Booking.query.filter(
                Booking.doctor_id.in_(doc_ids),
                Booking.appointment_date >= start_date,
                Booking.appointment_date <= end_date,
                Booking.status == 'confirmed'
            ).order_by(Booking.appointment_date, Booking.appointment_time).all()

    else:  # patient
        upcoming = [b for b in my_bookings if b.status == 'confirmed' and b.appointment_date >= today_date]
        doc_ids = list(set([b.doctor_id for b in upcoming]))
        if doc_ids:
            queue_bookings = Booking.query.filter(
                Booking.doctor_id.in_(doc_ids),
                Booking.appointment_date >= start_date,
                Booking.appointment_date <= end_date,
                Booking.status == 'confirmed'
            ).order_by(Booking.appointment_date, Booking.appointment_time).all()

    # Pre-compute masked queue positions for patients
    masked_queue = []
    for doc_id in set([b.doctor_id for b in queue_bookings]):
        doc_queue = [b for b in queue_bookings if b.doctor_id == doc_id]
        # sort doc queue
        doc_queue.sort(key=lambda x: (x.appointment_date, x.appointment_time))
        for idx, q_b in enumerate(doc_queue):
            q_b.queue_number = idx + 1
            if current_user.role not in ['admin', 'doctor']:
                q_b.masked_name = f"Patient {idx + 1}"
            masked_queue.append(q_b)

    # sort back masked_queue by date/time
    masked_queue.sort(key=lambda x: (x.appointment_date, x.appointment_time))

    return render_template(
        "booking_dashboard.html",
        my_bookings=my_bookings,
        queue_bookings=masked_queue,
        queue_filter=queue_filter,
        today_date=today_date
    )


@booking_bp.route("/cancel/<int:booking_id>", methods=["POST"])
@login_required
def cancel(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash("Unauthorized.", "danger")
        return redirect(url_for("booking.dashboard"))
    booking.status = "cancelled"
    db.session.commit()
    flash("Appointment cancelled.", "info")
    return redirect(url_for("booking.dashboard"))


@booking_bp.route("/ics/<int:booking_id>")
@login_required
def export_ics(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash("Unauthorized.", "danger")
        return redirect(url_for("booking.dashboard"))

    try:
        start_time = datetime.strptime(
            booking.appointment_time, "%H:%M").time()
    except ValueError:
        start_time = datetime.strptime(
            booking.appointment_time, "%H:%M:%S").time()

    start_dt = datetime.combine(booking.appointment_date, start_time)
    end_dt = start_dt + timedelta(minutes=30)

    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    dtstart = start_dt.strftime("%Y%m%dT%H%M%S")
    dtend = end_dt.strftime("%Y%m%dT%H%M%S")

    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//MedApp//NONSGML v1.0//EN
BEGIN:VEVENT
UID:{booking.id}@medapp.local
DTSTAMP:{dtstamp}
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:Dr. {booking.doctor.name} Appointment
DESCRIPTION:Appointment at {booking.doctor.hospital}
LOCATION:{booking.doctor.hospital}
END:VEVENT
END:VCALENDAR"""

    response = Response(ics_content.strip(), mimetype='text/calendar')
    response.headers[
        "Content-Disposition"] = f"attachment; filename=medapp_appointment_{booking.id}.ics"
    return response


@booking_bp.route("/reschedule/<int:booking_id>", methods=["GET", "POST"])
@login_required
def reschedule(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash("Unauthorized.", "danger")
        return redirect(url_for("booking.dashboard"))

    form = BookingForm(obj=booking)
    doctors = Doctor.query.filter_by(available=True).all()
    form.doctor_id.choices = [
        (d.id, f"{d.name} — {d.hospital}") for d in doctors]

    if request.method == "GET":
        form.doctor_id.data = booking.doctor_id

    if form.validate_on_submit():
        booking.doctor_id = form.doctor_id.data
        booking.patient_name = form.patient_name.data
        booking.patient_email = form.patient_email.data
        booking.patient_phone = form.patient_phone.data
        booking.appointment_date = form.appointment_date.data
        booking.appointment_time = form.appointment_time.data
        booking.reason = form.reason.data
        booking.status = "confirmed"
        db.session.commit()
        flash("Appointment rescheduled successfully!", "success")
        return redirect(url_for("booking.dashboard"))

    return render_template("booking_reschedule.html", form=form, booking=booking)


@booking_bp.route("/confirmation/<int:booking_id>")
@login_required
def confirmation(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash("Unauthorized.", "danger")
        return redirect(url_for("booking.dashboard"))
    return render_template("booking_confirmation.html", booking=booking)


# ── Patient Appointments Page ──────────────────────────────────
@booking_bp.route("/appointments")
@login_required
def appointments():
    """Patient Appointments page with My Appointments and Appointment Queue sub-tabs."""
    today_date = date.today()
    tomorrow_date = today_date + timedelta(days=1)
    week_end = today_date + timedelta(days=7)

    # My Appointments: today, tomorrow, next 7 days
    my_today = Booking.query.filter_by(user_id=current_user.id, appointment_date=today_date).order_by(Booking.appointment_time).all()
    my_tomorrow = Booking.query.filter_by(user_id=current_user.id, appointment_date=tomorrow_date).order_by(Booking.appointment_time).all()
    my_week = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.appointment_date > tomorrow_date,
        Booking.appointment_date <= week_end
    ).order_by(Booking.appointment_date, Booking.appointment_time).all()

    # Appointment Queue: all bookings for doctors the patient has appointments with (today, tomorrow, next 7 days)
    my_confirmed = Booking.query.filter(
        Booking.user_id == current_user.id,
        Booking.status == 'confirmed',
        Booking.appointment_date >= today_date,
        Booking.appointment_date <= week_end
    ).all()
    doc_ids = list(set([b.doctor_id for b in my_confirmed]))

    queue_today = []
    queue_tomorrow = []
    queue_week = []

    if doc_ids:
        queue_today = Booking.query.filter(
            Booking.doctor_id.in_(doc_ids),
            Booking.appointment_date == today_date,
            Booking.status == 'confirmed'
        ).order_by(Booking.appointment_time).all()

        queue_tomorrow = Booking.query.filter(
            Booking.doctor_id.in_(doc_ids),
            Booking.appointment_date == tomorrow_date,
            Booking.status == 'confirmed'
        ).order_by(Booking.appointment_time).all()

        queue_week = Booking.query.filter(
            Booking.doctor_id.in_(doc_ids),
            Booking.appointment_date > tomorrow_date,
            Booking.appointment_date <= week_end,
            Booking.status == 'confirmed'
        ).order_by(Booking.appointment_date, Booking.appointment_time).all()

    # Mask queue entries for patients
    def mask_queue(q_list):
        for idx, b in enumerate(q_list):
            b.queue_number = idx + 1
            b.masked_name = "You" if b.user_id == current_user.id else f"Patient {idx + 1}"
        return q_list

    queue_today = mask_queue(queue_today)
    queue_tomorrow = mask_queue(queue_tomorrow)
    queue_week = mask_queue(queue_week)

    active_tab = request.args.get('tab', 'my_appointments')

    return render_template(
        "patient_appointments.html",
        my_today=my_today,
        my_tomorrow=my_tomorrow,
        my_week=my_week,
        queue_today=queue_today,
        queue_tomorrow=queue_tomorrow,
        queue_week=queue_week,
        today_date=today_date,
        active_tab=active_tab
    )


# ── Patient Messages Page ──────────────────────────────────────
@booking_bp.route("/messages")
@login_required
def messages():
    """Patient messages: show replies from doctors/admin to patient's contact messages."""
    # Get all messages where the patient was the sender (top-level only)
    sent_messages = ContactMessage.query.filter_by(
        sender_id=current_user.id,
        parent_id=None
    ).order_by(ContactMessage.created_at.desc()).all()

    all_replies = []
    for msg in sent_messages:
        replies = msg.get_replies()
        all_replies.extend(replies)

    # Mark unread replies as read when visiting this page
    unread_replies = [r for r in all_replies if not r.is_read]
    for r in unread_replies:
        r.is_read = True
    if unread_replies:
        db.session.commit()

    return render_template(
        "patient_messages.html",
        sent_messages=sent_messages,
        all_replies=all_replies
    )


# ── Patient Send Reply ─────────────────────────────────────────
@booking_bp.route("/messages/send-reply", methods=["POST"])
@login_required
def send_reply():
    """Patient replies to an existing message thread."""
    parent_id = request.form.get("parent_id", type=int)
    reply_text = request.form.get("message", "").strip()

    if not parent_id or not reply_text:
        flash("Reply cannot be empty.", "danger")
        return redirect(url_for("booking.messages"))

    parent_msg = ContactMessage.query.get(parent_id)
    if not parent_msg or parent_msg.sender_id != current_user.id:
        flash("Message thread not found.", "danger")
        return redirect(url_for("booking.messages"))

    reply = ContactMessage(
        name=current_user.name,
        email=current_user.email,
        message=reply_text,
        sender_id=current_user.id,
        parent_id=parent_id,
        is_read=False
    )
    db.session.add(reply)
    db.session.commit()
    flash("Reply sent successfully.", "success")
    return redirect(url_for("booking.messages"))


# ── Bell Notifications API ──────────────────────────────────────
@booking_bp.route("/notifications")
@login_required
def notifications():
    """Return unread notification count and recent snippets for bell icon."""
    sent_msgs = ContactMessage.query.filter_by(sender_id=current_user.id, parent_id=None).all()
    unread_replies = []
    for msg in sent_msgs:
        replies = msg.get_replies()
        for r in replies:
            if not r.is_read:
                unread_replies.append({
                    "id": r.id,
                    "sender": r.name,
                    "snippet": r.message[:80] + "..." if len(r.message) > 80 else r.message,
                    "time": r.created_at.strftime("%b %d, %I:%M %p")
                })
    return jsonify({"count": len(unread_replies), "notifications": unread_replies})


# ── Profile Update ─────────────────────────────────────────────
@booking_bp.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    """Update patient profile (name, phone)."""
    new_name = request.form.get("name", "").strip()
    new_phone = request.form.get("phone", "").strip()

    if new_name:
        current_user.name = new_name
    if new_phone:
        current_user.phone = new_phone
    
    db.session.commit()
    flash("Profile updated successfully!", "success")
    return redirect(url_for("booking.dashboard"))


# ── My Doctors ────────────────────────────────────────────────
@booking_bp.route("/my-doctors")
@login_required
def my_doctors():
    """Show all unique doctors the patient has previously booked with."""
    all_bookings = Booking.query.filter_by(user_id=current_user.id).all()

    # Group by doctor
    doctor_map = {}
    for b in all_bookings:
        did = b.doctor_id
        if did not in doctor_map:
            doctor_map[did] = {
                "doctor": b.doctor,
                "bookings": [],
            }
        doctor_map[did]["bookings"].append(b)

    # Build summary list sorted by most recent booking
    doctor_list = []
    for did, data in doctor_map.items():
        latest = max(data["bookings"], key=lambda x: x.appointment_date)
        doctor_list.append({
            "doctor": data["doctor"],
            "total": len(data["bookings"]),
            "completed": sum(1 for b in data["bookings"] if b.status == "completed"),
            "upcoming": sum(1 for b in data["bookings"] if b.status == "confirmed"),
            "latest_date": latest.appointment_date,
        })
    doctor_list.sort(key=lambda x: x["latest_date"], reverse=True)

    return render_template("patient_my_doctors.html", doctor_list=doctor_list)

