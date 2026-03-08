import logging
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_mail import Message
from models import Doctor, ContactMessage
from forms import ContactForm
from extensions import db, mail

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
    if form.validate_on_submit():
        msg_obj = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            message=form.message.data,
        )
        db.session.add(msg_obj)
        db.session.commit()

        # Send email if configured
        if current_app.config.get("MAIL_ENABLED"):
            try:
                msg = Message(
                    subject=f"New Contact Message from {form.name.data}",
                    recipients=[current_app.config["ADMIN_EMAIL"]],
                    body=f"From: {form.name.data} <{form.email.data}>\n\n{form.message.data}",
                )
                mail.send(msg)
            except Exception as e:
                logger.warning("Could not send contact email: %s", e)

        flash("Your message has been sent! We'll get back to you shortly.", "success")
        return redirect(url_for("main.contact"))
    return render_template("contact.html", form=form)
