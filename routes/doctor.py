import logging
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import Booking, db

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

    stats = {
        "total": len(bookings),
        "upcoming": sum(1 for b in bookings if b.status == "confirmed"),
        "completed": sum(1 for b in bookings if b.status == "completed"),
        "cancelled": sum(1 for b in bookings if b.status == "cancelled"),
    }

    return render_template("doctor/dashboard.html", bookings=bookings, stats=stats)


@doctor_bp.route("/status/<int:booking_id>", methods=["POST"])
@doctor_required
def update_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    # Verify this booking belongs to the current doctor
    if not current_user.doctor_profile or booking.doctor_id != current_user.doctor_profile.id:
        flash("Unauthorized.", "danger")
        return redirect(url_for("doctor.dashboard"))

    new_status = request.form.get("status")
    if new_status in ["confirmed", "completed", "cancelled"]:
        booking.status = new_status
        db.session.commit()
        flash(f"Appointment status updated to {new_status}.", "success")
    else:
        flash("Invalid status.", "danger")

    return redirect(url_for("doctor.dashboard"))
