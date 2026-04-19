import logging
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from forms import LoginForm, RegisterForm, DirectResetPasswordForm
from extensions import db

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif current_user.role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(name=form.name.data, email=form.email.data.lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        logger.info("New user registered: %s", user.email)
        flash("Account created! Please sign in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif current_user.role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            logger.info("User logged in: %s", user.email)
            next_page = request.args.get("next")
            if next_page:
                return redirect(next_page)
            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            elif user.role == "doctor":
                return redirect(url_for("doctor.dashboard"))
            else:
                return redirect(url_for("main.index"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html", form=form)


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        elif current_user.role == "doctor":
            return redirect(url_for("doctor.dashboard"))
        return redirect(url_for("main.index"))
    form = DirectResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            user.set_password(form.password.data)
            db.session.commit()
            logger.info("Password directly reset for user: %s", user.email)
            flash("Your password has been successfully reset. Please sign in.", "success")
            return redirect(url_for("auth.login"))
        else:
            # For security, we usually don't want to confirm if an email exists
            # but to ensure UX for this specific direct reset flow, we'll flash an error
            flash("Email not found in our records.", "danger")
    return render_template("reset_password.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
