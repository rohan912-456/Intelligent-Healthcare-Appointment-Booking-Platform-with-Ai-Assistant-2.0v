import logging
import csv
import io
from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, jsonify
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
        "completed": Booking.query.filter_by(status="completed").count(),
    }
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(10).all()
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, recent_bookings=recent_bookings, messages=messages)


@admin_bp.route("/messages")
@admin_required
def messages():
    page = request.args.get("page", 1, type=int)
    all_messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).paginate(page=page, per_page=15)
    return render_template("admin/messages.html", messages=all_messages)


@admin_bp.route("/messages/delete/<int:message_id>", methods=["POST"])
@admin_required
def delete_message(message_id):
    msg = ContactMessage.query.get_or_404(message_id)
    db.session.delete(msg)
    db.session.commit()
    flash("Message deleted successfully.", "success")
    return redirect(url_for("admin.messages"))


@admin_bp.route("/messages/reply/<int:message_id>", methods=["POST"])
@admin_required
def reply_message(message_id):
    """Admin replies to a patient's contact message."""
    parent_msg = ContactMessage.query.get_or_404(message_id)
    reply_text = request.form.get("message", "").strip()
    if not reply_text:
        flash("Reply cannot be empty.", "warning")
        return redirect(url_for("admin.messages"))

    reply = ContactMessage(
        name="Admin (MedApp Support)",
        email=current_user.email,
        message=reply_text,
        sender_id=current_user.id,
        parent_id=parent_msg.id,
        is_read=False
    )
    db.session.add(reply)
    db.session.commit()
    flash("Reply sent to patient.", "success")
    return redirect(url_for("admin.messages"))


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


@admin_bp.route("/logs")
@admin_required
def logs():
    # Simple mock logs or filtered messages as requested
    system_logs = [
        {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "event": "Admin logged in", "status": "Secure"},
        {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "event": "Database Schema Synced", "status": "Fixed"},
        {"timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "event": "Patient Message Received", "status": "Unread"},
    ]
    return render_template("admin/logs.html", logs=system_logs)


@admin_bp.route("/export-report")
@admin_required
def export_report():
    bookings = Booking.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Patient Name', 'Doctor', 'Date', 'Time', 'Status', 'Reason'])
    
    for b in bookings:
        writer.writerow([b.id, b.patient_name, b.doctor.name, b.appointment_date, b.appointment_time, b.status, b.reason])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=clinical_report.csv"}
    )


# ── Admin Bell Notifications API ─────────────────────────────
@admin_bp.route("/notifications")
@admin_required
def notifications():
    """Return unread contact messages count + snippets for the admin bell icon."""
    unread = ContactMessage.query.filter_by(
        parent_id=None, is_read=False
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
