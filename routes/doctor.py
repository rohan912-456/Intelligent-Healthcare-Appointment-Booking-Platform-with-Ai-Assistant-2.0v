import logging
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Booking, ContactMessage, db

doctor_bp = Blueprint("doctor", __name__, url_prefix="/doctor")
logger = logging.getLogger(__name__)

def doctor_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != "doctor":
            flash("Doctor access required.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated

@doctor_bp.route("/")
@doctor_required
def dashboard():
    if not current_user.doctor_profile:
        flash("No doctor profile linked to this account.", "danger")
        return redirect(url_for("main.index"))

    doctor_id = current_user.doctor_profile.id
    bookings = Booking.query.filter_by(doctor_id=doctor_id).order_by(
        Booking.appointment_date.desc()).all()

    # Fetch clinical messages for this doctor
    messages = ContactMessage.query.filter_by(doctor_id=doctor_id, parent_id=None).order_by(
        ContactMessage.created_at.desc()).all()

    stats = {
        "total": len(bookings),
        "upcoming": sum(1 for b in bookings if b.status == "confirmed"),
        "completed": sum(1 for b in bookings if b.status == "completed"),
        "cancelled": sum(1 for b in bookings if b.status == "cancelled"),
        "messages": len(messages)
    }

    return render_template("doctor/dashboard.html", bookings=bookings, stats=stats, messages=messages)


@doctor_bp.route("/appointments")
@doctor_required
def appointments():
    if not current_user.doctor_profile:
        flash("No doctor profile linked.", "danger")
        return redirect(url_for("main.index"))

    doctor_id = current_user.doctor_profile.id
    active_filter = request.args.get("filter", "all")

    base_query = Booking.query.filter_by(doctor_id=doctor_id)

    if active_filter == "upcoming":
        bookings = base_query.filter_by(status="confirmed").order_by(
            Booking.appointment_date.asc(), Booking.appointment_time.asc()).all()
    elif active_filter == "completed":
        bookings = base_query.filter_by(status="completed").order_by(
            Booking.appointment_date.desc()).all()
    elif active_filter == "cancelled":
        bookings = base_query.filter_by(status="cancelled").order_by(
            Booking.appointment_date.desc()).all()
    else:
        bookings = base_query.order_by(Booking.appointment_date.desc()).all()

    all_bookings = base_query.all()
    upcoming_count  = sum(1 for b in all_bookings if b.status == "confirmed")
    completed_count = sum(1 for b in all_bookings if b.status == "completed")
    cancelled_count = sum(1 for b in all_bookings if b.status == "cancelled")

    return render_template(
        "doctor/appointments.html",
        bookings=bookings,
        active_filter=active_filter,
        upcoming_count=upcoming_count,
        completed_count=completed_count,
        cancelled_count=cancelled_count
    )


@doctor_bp.route("/messages")
@doctor_required
def messages():
    if not current_user.doctor_profile:
        flash("No doctor profile linked.", "danger")
        return redirect(url_for("main.index"))
    
    doctor_id = current_user.doctor_profile.id
    all_messages = ContactMessage.query.filter_by(doctor_id=doctor_id, parent_id=None).order_by(
        ContactMessage.created_at.desc()).all()
    
    return render_template("doctor/messages.html", messages=all_messages)

@doctor_bp.route("/status/<int:booking_id>", methods=["POST"])
@doctor_required
def update_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if not current_user.doctor_profile or booking.doctor_id != current_user.doctor_profile.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("doctor.dashboard"))

    new_status = request.form.get("status")
    if new_status in ["confirmed", "completed", "cancelled"]:
        booking.status = new_status
        db.session.commit()
        flash(f"Appointment marked as {new_status}.", "success")
    else:
        flash("Invalid status.", "danger")
    # Return to wherever the doctor came from
    next_url = request.referrer or url_for("doctor.dashboard")
    return redirect(next_url)

@doctor_bp.route("/reply/<int:message_id>", methods=["POST"])
@doctor_required
def reply_message(message_id):
    parent_msg = ContactMessage.query.get_or_404(message_id)
    if parent_msg.doctor_id != current_user.doctor_profile.id:
        flash("Unauthorized reply attempt.", "danger")
        return redirect(url_for("doctor.dashboard"))

    reply_text = request.form.get("message")
    if reply_text:
        reply = ContactMessage(
            name=f"{current_user.doctor_profile.name} (Reply)",
            email=current_user.email,
            message=reply_text,
            doctor_id=current_user.doctor_profile.id,
            sender_id=current_user.id,
            parent_id=parent_msg.id
        )
        db.session.add(reply)
        db.session.commit()
        flash("Reply transmitted successfully.", "success")
    return redirect(url_for("doctor.dashboard"))


# ── Doctor Bell Notifications API ────────────────────────────
@doctor_bp.route("/notifications")
@doctor_required
def notifications():
    """Return unread clinical messages count + snippets for the doctor bell icon."""
    if not current_user.doctor_profile:
        return jsonify({"count": 0, "notifications": []})

    doctor_id = current_user.doctor_profile.id
    unread = ContactMessage.query.filter_by(
        doctor_id=doctor_id, parent_id=None, is_read=False
    ).order_by(ContactMessage.created_at.desc()).limit(5).all()

    result = [
        {
            "id": m.id,
            "sender": m.name,
            "snippet": m.message[:80] + "..." if len(m.message) > 80 else m.message,
            "time": m.created_at.strftime("%b %d, %I:%M %p")
        }
        for m in unread
    ]
    return jsonify({"count": len(result), "notifications": result})

