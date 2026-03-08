import logging
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
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
    form.doctor_id.choices = [(d.id, f"{d.name} — {d.hospital}") for d in doctors]

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
        logger.info("Booking created: ID=%s for %s", booking.id, booking.patient_email)

        # Email confirmation
        if current_app.config.get("MAIL_ENABLED"):
            try:
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
                mail.send(msg)
            except Exception as e:
                logger.warning("Could not send confirmation email: %s", e)

        flash("Appointment booked successfully! A confirmation has been sent to your email.", "success")
        return redirect(url_for("booking.my_bookings"))

    # Pre-fill name/email from current user
    if not form.patient_name.data:
        form.patient_name.data = current_user.name
        form.patient_email.data = current_user.email

    return render_template("book.html", form=form, doctors=doctors)


@booking_bp.route("/my-bookings")
@login_required
def my_bookings():
    bookings = (
        Booking.query
        .filter_by(user_id=current_user.id)
        .order_by(Booking.appointment_date.desc())
        .all()
    )
    return render_template("my_bookings.html", bookings=bookings)


@booking_bp.route("/cancel/<int:booking_id>", methods=["POST"])
@login_required
def cancel(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash("Unauthorized.", "danger")
        return redirect(url_for("booking.my_bookings"))
    booking.status = "cancelled"
    db.session.commit()
    flash("Appointment cancelled.", "info")
    return redirect(url_for("booking.my_bookings"))
