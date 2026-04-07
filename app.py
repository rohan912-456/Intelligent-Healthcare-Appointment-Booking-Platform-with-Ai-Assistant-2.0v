import os
import logging
from flask import Flask
from config import config_map
from extensions import db, login_manager, mail, csrf, migrate, limiter


def create_app(env=None):
    app = Flask(__name__)

    # Load config
    env = env or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_map.get(env, config_map["default"]))

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Register blueprints
    from routes import main_bp, auth_bp, booking_bp, chat_bp, admin_bp, doctor_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(doctor_bp)

    # Exempt chat from CSRF (JSON API)
    csrf.exempt(chat_bp)

    # Seed DB on first run
    with app.app_context():
        db.create_all()
        _seed_data(app)

    return app


def _seed_data(app):
    from models import Doctor, User
    from extensions import db

    # Seed admin first
    admin_email = app.config["ADMIN_EMAIL"]
    if not User.query.filter_by(email=admin_email).first():
        admin = User(name="Admin", email=admin_email,
                     is_admin=True, role="admin")
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
        app.logger.info("Admin account created: %s", admin_email)

    # Seed doctors and their users
    if Doctor.query.count() == 0:
        base_hospitals = [
            ("Indira Gandhi Govt Medical College", 21.1435, 79.0850),
            ("Gandhi Hospital", 21.1410, 79.0710),
            ("Deshmukh Hospital", 21.1230, 79.0420),
            ("Nectar Hospital", 21.13438, 79.07505),
            ("Orange City Hospital", 21.1088, 79.0511),
            ("Wockhardt Hospital", 21.1402, 79.0683)
        ]

        doc_data = [
            ("Dr. Mehta", "Cardiologist", 0),
            ("Dr. Rao", "General Physician", 1),
            ("Dr. Kapoor", "Orthopedic Surgeon", 2),
            ("Dr. Singh", "Neurologist", 3),
            ("Dr. Iyer", "Pulmonologist", 4),
            ("Dr. Joshi", "General Physician", 5),
            ("Dr. Patil", "Pediatrician", 0),
            ("Dr. Kulkarni", "Dermatologist", 1),
            ("Dr. Sharma", "General Physician", 2),
            ("Dr. Verma", "Psychiatrist", 3),
            ("Dr. Desai", "Cardiologist", 4),
            ("Dr. Gupta", "Pediatrician", 5),
            ("Dr. Naidu", "General Physician", 0),
            ("Dr. Reddy", "Neurologist", 1),
            ("Dr. Chauhan", "Orthopedic Surgeon", 2),
        ]

        for i, (d_name, d_spec, h_idx) in enumerate(doc_data):
            h_name, lat, lng = base_hospitals[h_idx]
            doc_email = f"doctor{i + 1}@medapp.com"
            doc_user = User(name=d_name, email=doc_email, role="doctor")
            doc_user.set_password("Doctor@123")
            db.session.add(doc_user)
            db.session.flush()  # Flush to get doc_user.id

            doc = Doctor(
                name=d_name,
                specialty=d_spec,
                hospital=h_name,
                lat=lat,
                lng=lng,
                user_id=doc_user.id
            )
            db.session.add(doc)

        db.session.commit()
        app.logger.info(
            "Seeded %d doctors with login accounts.", len(doc_data))


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, host="0.0.0.0", port=5000)
