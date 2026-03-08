import logging
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import User, Doctor, Booking, ContactMessage
from extensions import db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
logger = logging.getLogger(__name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/")
@admin_required
def dashboard():
    stats = {
        "users": User.query.count(),
        "doctors": Doctor.query.count(),
        "bookings": Booking.query.count(),
        "messages": ContactMessage.query.count(),
        "confirmed": Booking.query.filter_by(status="confirmed").count(),
        "cancelled": Booking.query.filter_by(status="cancelled").count(),
    }
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, recent_bookings=recent_bookings, messages=messages)


@admin_bp.route("/doctors")
@admin_required
def doctors():
    all_doctors = Doctor.query.all()
    return render_template("admin/doctors.html", doctors=all_doctors)


@admin_bp.route("/doctors/toggle/<int:doctor_id>", methods=["POST"])
@admin_required
def toggle_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.available = not doctor.available
    db.session.commit()
    status = "available" if doctor.available else "unavailable"
    flash(f"{doctor.name} is now {status}.", "info")
    return redirect(url_for("admin.doctors"))


@admin_bp.route("/bookings")
@admin_required
def bookings():
    page = request.args.get("page", 1, type=int)
    all_bookings = Booking.query.order_by(Booking.created_at.desc()).paginate(page=page, per_page=20)
    return render_template("admin/bookings.html", bookings=all_bookings)


@admin_bp.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)
