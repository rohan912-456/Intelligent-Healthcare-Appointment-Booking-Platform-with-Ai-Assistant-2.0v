import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # Mail
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "MedApp <noreply@medapp.com>")
    MAIL_ENABLED = bool(os.getenv("MAIL_USERNAME"))

    # API keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY", "")

    # Admin seed
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@medapp.com")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@1234")

    # Rate limiting
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_DEFAULT = "200 per day;50 per hour"


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///medical_dev.db")


class ProductionConfig(Config):
    DEBUG = False
    # Vercel is a read-only filesystem except for /tmp
    if os.getenv("VERCEL"):
        SQLALCHEMY_DATABASE_URI = "sqlite:////tmp/medical.db"
    else:
        SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///medical.db")


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
