import logging
from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request, Response
from flask_login import login_required, current_user
from flask_mail import Message
from models import Doctor, Booking
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
