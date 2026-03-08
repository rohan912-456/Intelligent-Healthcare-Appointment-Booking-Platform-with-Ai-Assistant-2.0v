"""
pytest tests/test_app.py
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from extensions import db as _db


@pytest.fixture(scope="session")
def app():
    os.environ["FLASK_ENV"] = "development"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["SECRET_KEY"] = "test-secret"
    application = create_app("development")
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    yield application


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def db(app):
    with app.app_context():
        _db.create_all()
        yield _db


# ── Route Tests ───────────────────────────────────────

def test_home_loads(client):
    rv = client.get("/")
    assert rv.status_code == 200
    assert b"MedApp" in rv.data or b"medapp" in rv.data.lower()


def test_contact_get(client):
    rv = client.get("/contact")
    assert rv.status_code == 200


def test_login_get(client):
    rv = client.get("/auth/login")
    assert rv.status_code == 200


def test_register_get(client):
    rv = client.get("/auth/register")
    assert rv.status_code == 200


def test_register_and_login(client, db):
    # Register
    rv = client.post("/auth/register", data={
        "name": "Test User",
        "email": "test@example.com",
        "password": "Secure123",
        "confirm": "Secure123",
    }, follow_redirects=True)
    assert rv.status_code == 200

    # Login
    rv = client.post("/auth/login", data={
        "email": "test@example.com",
        "password": "Secure123",
    }, follow_redirects=True)
    assert rv.status_code == 200


def test_booking_requires_login(client):
    rv = client.get("/booking/book", follow_redirects=False)
    assert rv.status_code in (302, 401)


def test_my_bookings_requires_login(client):
    rv = client.get("/booking/my-bookings", follow_redirects=False)
    assert rv.status_code in (302, 401)


def test_admin_requires_login(client):
    rv = client.get("/admin/", follow_redirects=False)
    assert rv.status_code in (302, 401)


def test_chat_endpoint(client):
    rv = client.post("/chat/message",
                     json={"message": "Hello"},
                     content_type="application/json")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "reply" in data


def test_chat_empty_message(client):
    rv = client.post("/chat/message",
                     json={"message": ""},
                     content_type="application/json")
    assert rv.status_code == 400


def test_chat_reset(client):
    rv = client.post("/chat/reset")
    assert rv.status_code == 200
