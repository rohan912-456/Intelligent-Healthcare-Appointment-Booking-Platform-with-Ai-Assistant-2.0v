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
    from routes import main_bp, auth_bp, booking_bp, chat_bp, admin_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp)

    # Exempt chat from CSRF (JSON API)
    csrf.exempt(chat_bp)

    # Seed DB on first run
    with app.app_context():
        db.create_all()
        _seed_data(app)

    return app


def _seed_data(app):
    from models import Doctor, User

    # Seed doctors
    if Doctor.query.count() == 0:
        doctors = [
            Doctor(name="Dr. Mehta", specialty="Cardiologist",
                   hospital="Indira Gandhi Govt Medical College & Hospital", lat=21.1435, lng=79.0850),
            Doctor(name="Dr. Rao", specialty="General Physician",
                   hospital="Gandhi Hospital", lat=21.1410, lng=79.0710),
            Doctor(name="Dr. Kapoor", specialty="Orthopedic Surgeon",
                   hospital="Deshmukh Hospital", lat=21.1230, lng=79.0420),
            Doctor(name="Dr. Singh", specialty="Neurologist",
                   hospital="Nectar Hospital", lat=21.13438, lng=79.07505),
            Doctor(name="Dr. Iyer", specialty="Pulmonologist",
                   hospital="Orange City Hospital & Research Institute", lat=21.1088, lng=79.0511),
        ]
        from extensions import db
        db.session.add_all(doctors)
        db.session.commit()
        app.logger.info("Seeded %d doctors.", len(doctors))

    # Seed admin
    admin_email = app.config["ADMIN_EMAIL"]
    if not User.query.filter_by(email=admin_email).first():
        from extensions import db
        admin = User(name="Admin", email=admin_email, is_admin=True)
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
        app.logger.info("Admin account created: %s", admin_email)


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, host="0.0.0.0", port=5000)
