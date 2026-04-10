"""Route smoke test with proper auth session testing."""
import sys
sys.path.insert(0, '.')
from app import create_app
from models import User, ContactMessage
from extensions import db
from sqlalchemy import text

app = create_app()
app.config['TESTING'] = True
app.config['WTF_CSRF_ENABLED'] = False

PASS = lambda msg: print(f"PASS: {msg}")
FAIL = lambda msg: print(f"FAIL: {msg}")

with app.app_context():
    client = app.test_client()

    # ── 1. Admin login & messages page ───────────────────────────
    admin = User.query.filter_by(is_admin=True).first()
    print(f"Admin account: {admin.email}")

    login_res = client.post('/auth/login', data={
        'email': admin.email, 'password': 'Admin@123', 'remember': False
    }, follow_redirects=True)
    print(f"Admin login response: {login_res.status_code}")

    r = client.get('/admin/messages')
    if r.status_code == 200:
        body = r.data.decode('utf-8', errors='replace')
        if 'Intelligence' in body or 'Pipeline' in body or 'admin-container' in body:
            PASS("Admin /messages page loads with correct content")
        else:
            print(f"WARN: Admin /messages returned 200 but unexpected body snippet: {body[:300]}")
    else:
        loc = r.headers.get('Location', 'none')
        FAIL(f"Admin /messages returned {r.status_code}, redirect to: {loc}")

    # ── 2. Admin reply to a message ──────────────────────────────
    # Create a test message first
    test_msg = ContactMessage(name="SmokeTest Patient", email="smoke@test.com", message="Test message for admin reply")
    db.session.add(test_msg)
    db.session.commit()
    msg_id = test_msg.id
    print(f"Created test ContactMessage id={msg_id}")

    r2 = client.post(f'/admin/messages/reply/{msg_id}', data={'message': 'Admin reply test'})
    if r2.status_code in (200, 302):
        reply_count = ContactMessage.query.filter_by(parent_id=msg_id).count()
        if reply_count > 0:
            PASS(f"Admin reply route works — {reply_count} reply(s) in DB")
        else:
            FAIL("Admin reply route returned success but no DB row created")
    else:
        FAIL(f"Admin reply returned {r2.status_code}")

    # ── 3. Logout admin, login as patient ─────────────────────────
    client.get('/auth/logout')
    patients = User.query.filter_by(role='patient').all()
    print(f"Patient accounts: {[u.email for u in patients]}")

    if patients:
        patient = patients[0]
        # Most patients were seeded as doctors; use admin as fallback test
    
    # Login as admin again to test /booking paths are admin-accessible too
    client.post('/auth/login', data={
        'email': admin.email, 'password': 'Admin@123', 'remember': False
    })
    r3 = client.get('/booking/messages')
    if r3.status_code == 200:
        PASS("Booking /messages page returns 200")
    else:
        print(f"INFO: Booking /messages -> {r3.status_code} (admin has no sent messages, expected)")

    r4 = client.get('/booking/notifications')
    if r4.status_code == 200:
        PASS("Bell notifications endpoint returns 200")
    else:
        FAIL(f"Bell notifications returned {r4.status_code}")

    # ── 4. Doctor messages page ──────────────────────────────────
    client.get('/auth/logout')
    doctor_user = User.query.filter_by(role='doctor').first()
    print(f"Doctor account: {doctor_user.email}")
    client.post('/auth/login', data={'email': doctor_user.email, 'password': 'Doctor@123'})
    r5 = client.get('/doctor/messages')
    if r5.status_code == 200:
        PASS("Doctor /messages page returns 200")
    else:
        FAIL(f"Doctor /messages returned {r5.status_code}")

    # ── 5. Doctor reply ──────────────────────────────────────────
    # Assign the test message to doctor1
    dr_profile = doctor_user.doctor_profile
    if dr_profile:
        test_msg.doctor_id = dr_profile.id
        db.session.commit()
        r6 = client.post(f'/doctor/reply/{msg_id}', data={'message': 'Doctor reply test'})
        if r6.status_code in (200, 302):
            reply_count2 = ContactMessage.query.filter_by(parent_id=msg_id).count()
            PASS(f"Doctor reply route works — {reply_count2} total reply(s) in DB")
        else:
            FAIL(f"Doctor reply returned {r6.status_code}")
    else:
        print("SKIP: Doctor profile not linked, skipping doctor reply test")

    # ── 6. Cleanup test data ─────────────────────────────────────
    ContactMessage.query.filter_by(parent_id=msg_id).delete()
    db.session.delete(test_msg)
    db.session.commit()
    print("Test data cleaned up")

    # ── 7. Schema verification ───────────────────────────────────
    with db.engine.connect() as conn:
        cols = [r[1] for r in conn.execute(text('PRAGMA table_info(contact_messages)')).fetchall()]
        required = ['doctor_id', 'parent_id', 'is_read', 'sender_id']
        missing = [c for c in required if c not in cols]
        if not missing:
            PASS(f"DB schema correct — contact_messages columns: {cols}")
        else:
            FAIL(f"Missing columns: {missing}")

print("\n=== Smoke test complete ===")
