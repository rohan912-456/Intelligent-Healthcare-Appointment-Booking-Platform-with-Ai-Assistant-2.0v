import logging
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from models import Doctor, ContactMessage
from forms import ContactForm
from extensions import db

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


@main_bp.route("/")
def index():
    doctors = Doctor.query.filter_by(available=True).all()
    doctors_json = [d.to_dict() for d in doctors]
    maps_key = current_app.config.get("GOOGLE_MAPS_KEY", "")
    return render_template("index.html", doctors=doctors, doctors_json=doctors_json, maps_key=maps_key)


@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    # Populate recipients
    doctors = Doctor.query.all()
    form.recipient.choices = [("admin", "System Administrator")] + [
        (str(d.id), d.name) for d in doctors
    ]
    if form.validate_on_submit():
        recipient_val = form.recipient.data
        doctor_id = None if recipient_val == "admin" else int(recipient_val)

        from flask_login import current_user
        sender_id = current_user.id if current_user.is_authenticated else None

        msg_obj = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            message=form.message.data,
            doctor_id=doctor_id,
            sender_id=sender_id
        )
        db.session.add(msg_obj)
        db.session.commit()

        # Send email if configured
        if current_app.config.get("MAIL_ENABLED"):
            # ... (rest of email logic remains same or can be updated)
            pass

        flash("Your message has been sent! We'll get back to you shortly.", "success")
        return redirect(url_for("main.contact"))
    return render_template("contact.html", form=form)
