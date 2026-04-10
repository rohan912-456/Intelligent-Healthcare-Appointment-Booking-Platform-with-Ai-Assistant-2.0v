from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(20), default="patient")
    phone = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship("Booking", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


class Doctor(db.Model):
    __tablename__ = "doctors"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, unique=True)
    user = db.relationship("User", backref=db.backref("doctor_profile", uselist=False))
    name = db.Column(db.String(120), nullable=False)
    specialty = db.Column(db.String(100), default="General Physician")
    hospital = db.Column(db.String(200), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    available = db.Column(db.Boolean, default=True)
    bookings = db.relationship("Booking", backref="doctor", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "specialty": self.specialty,
            "hospital": self.hospital,
            "lat": self.lat,
            "lng": self.lng,
        }

    def __repr__(self):
        return f"<Doctor {self.name}>"


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)
    patient_name = db.Column(db.String(120), nullable=False)
    patient_email = db.Column(db.String(150), nullable=False)
    patient_phone = db.Column(db.String(20), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.String(10), nullable=False)
    reason = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="confirmed")  # confirmed, cancelled, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Booking {self.id} – {self.patient_name}>"


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("contact_messages.id"), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    replies = db.relationship("ContactMessage", backref=db.backref("parent", remote_side=[id]), lazy="dynamic")
    sender_relation = db.relationship("User", backref="sent_messages", foreign_keys=[sender_id])
    doctor_relation = db.relationship("Doctor", backref="received_messages", foreign_keys=[doctor_id])

    def get_replies(self):
        return self.replies.order_by(ContactMessage.created_at.asc()).all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
