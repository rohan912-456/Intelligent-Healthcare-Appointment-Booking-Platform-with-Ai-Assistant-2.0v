from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, TextAreaField,
    SelectField, DateField, SubmitField, BooleanField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo,
    ValidationError, Regexp
)
from models import User


class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[DataRequired(), Length(2, 120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[
        DataRequired(), Length(8, 128),
        Regexp(r"(?=.*[A-Z])(?=.*\d)", message="Must contain a capital letter and a number.")
    ])
    confirm = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("Create Account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Email already registered.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class BookingForm(FlaskForm):
    doctor_id = SelectField("Doctor", coerce=int, validators=[DataRequired()])
    patient_name = StringField("Your Name", validators=[DataRequired(), Length(2, 120)])
    patient_email = StringField("Email", validators=[DataRequired(), Email()])
    patient_phone = StringField("Phone", validators=[
        DataRequired(),
        Regexp(r"^\+?[\d\s\-]{7,20}$", message="Enter a valid phone number.")
    ])
    appointment_date = DateField("Date", validators=[DataRequired()])
    appointment_time = SelectField("Time", choices=[
        ("09:00", "09:00 AM"), ("09:30", "09:30 AM"), ("10:00", "10:00 AM"),
        ("10:30", "10:30 AM"), ("11:00", "11:00 AM"), ("11:30", "11:30 AM"),
        ("14:00", "02:00 PM"), ("14:30", "02:30 PM"), ("15:00", "03:00 PM"),
        ("15:30", "03:30 PM"), ("16:00", "04:00 PM"), ("16:30", "04:30 PM"),
    ])
    reason = TextAreaField("Reason for Visit", validators=[Length(0, 500)])
    submit = SubmitField("Confirm Appointment")


class ContactForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(2, 120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    recipient = SelectField("Recipient", coerce=str, validators=[DataRequired()])
    message = TextAreaField("Message", validators=[DataRequired(), Length(10, 2000)])
    submit = SubmitField("Send Message")
