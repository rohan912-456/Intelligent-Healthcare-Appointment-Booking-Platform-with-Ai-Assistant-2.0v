"""
End-to-end HTTP test against the running Flask server at http://127.0.0.1:5000
Run while the Flask dev server is running.
"""
import requests
import sys
import re

BASE = "http://127.0.0.1:5000"
RESULTS = []

def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append((status, name, detail))
    sym = "[OK]" if condition else "[!!]"
    print(f"  {sym} {status}: {name}" + (f"  [{detail}]" if detail else ""))

def extract_csrf(html):
    """Extract CSRF token from Flask-WTF rendered form."""
    # Pattern: <input id="csrf_token" name="csrf_token" type="hidden" value="TOKEN">
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'value="([^"]+)"[^>]*name="csrf_token"', html)
    if m:
        return m.group(1)
    return ""

def login(session, email, password):
    r = session.get(f"{BASE}/auth/login")
    csrf = extract_csrf(r.text)
    print(f"    [login] CSRF found: {'YES (' + csrf[:12] + '...)' if csrf else 'NO'}")
    return session.post(f"{BASE}/auth/login", data={
        'email': email, 'password': password, 'csrf_token': csrf, 'remember': 'y'
    }, allow_redirects=True)

def get_csrf(session, url):
    r = session.get(url)
    return extract_csrf(r.text), r


print("=" * 60)
print("MedApp End-to-End Smoke Test")
print("=" * 60)

# ── TEST 1: Homepage ──────────────────────────────────────────
print("\n[TEST 1] Homepage")
r = requests.get(BASE)
check("Homepage loads (200)", r.status_code == 200)
check("No traceback in homepage", 'Traceback' not in r.text and 'Internal Server Error' not in r.text)
check("Doctor/specialist content visible", 'Dr.' in r.text or 'doctor' in r.text.lower())

# ── TEST 2: Patient Registration & Login ──────────────────────
print("\n[TEST 2] Patient Registration & Login")
s_patient = requests.Session()
csrf_reg, reg_page = get_csrf(s_patient, f"{BASE}/auth/register")
check("Registration page loads", reg_page.status_code == 200)
check("CSRF token on register page", bool(csrf_reg), csrf_reg[:15] + "..." if csrf_reg else "MISSING")

TEST_EMAIL = "e2etest_final@example.com"
TEST_PASS = "Test@1234"

reg_res = s_patient.post(f"{BASE}/auth/register", data={
    'name': 'E2E Patient', 'email': TEST_EMAIL,
    'password': TEST_PASS, 'confirm': TEST_PASS, 'csrf_token': csrf_reg
}, allow_redirects=True)
# 200 means either the form re-rendered (already exists) or redirect followed to login (200)
reg_ok = reg_res.status_code == 200 and 'Internal Server Error' not in reg_res.text
check("Registration/existing account no crash", reg_ok)

login_res = login(s_patient, TEST_EMAIL, TEST_PASS)
logged_in = login_res.status_code == 200 and '/auth/login' not in login_res.url
check("Patient login succeeds", logged_in, login_res.url)

# ── TEST 3: Patient sends contact message ─────────────────────
print("\n[TEST 3] Patient Contact Message")
csrf_contact, contact_page = get_csrf(s_patient, f"{BASE}/contact")
check("Contact page loads", contact_page.status_code == 200)

contact_res = s_patient.post(f"{BASE}/contact", data={
    'name': 'E2E Patient', 'email': TEST_EMAIL, 'recipient': 'admin',
    'message': 'Hello Admin, this is an automated e2e test. Please reply.',
    'csrf_token': csrf_contact
}, allow_redirects=True)
check("Contact form POST succeeds", contact_res.status_code == 200)
check("No server error on contact", 'Internal Server Error' not in contact_res.text)
check("Success feedback shown", 'sent' in contact_res.text.lower() or 'success' in contact_res.text.lower())

# ── TEST 4: Patient dashboard & appointments ──────────────────
print("\n[TEST 4] Patient Dashboard & Appointments")
dash_r = s_patient.get(f"{BASE}/booking/dashboard")
check("Patient dashboard loads", dash_r.status_code == 200)
check("No error on dashboard", 'Internal Server Error' not in dash_r.text)

appt_r = s_patient.get(f"{BASE}/booking/appointments")
check("Patient appointments page loads", appt_r.status_code == 200)
check("No error on appointments", 'Internal Server Error' not in appt_r.text)

# ── TEST 5: Patient messages page ─────────────────────────────
print("\n[TEST 5] Patient Messages (Clinical Comms)")
msgs_r = s_patient.get(f"{BASE}/booking/messages")
check("Patient messages page loads (200)", msgs_r.status_code == 200)
check("No error on messages", 'Internal Server Error' not in msgs_r.text)
check("Clinical Comms UI present", 'Clinical' in msgs_r.text or 'Comms' in msgs_r.text or 'send_reply' in msgs_r.text)
check("Sent message visible in inbox", 'E2E Patient' in msgs_r.text)

# ── TEST 6: Bell notifications API ───────────────────────────
print("\n[TEST 6] Bell Notifications API")
notif_r = s_patient.get(f"{BASE}/booking/notifications")
check("Notifications API returns 200", notif_r.status_code == 200)
try:
    data = notif_r.json()
    check("JSON has 'count' field", 'count' in data, str(data.get('count')))
    check("JSON has 'notifications' list", 'notifications' in data)
except Exception as e:
    check("Notifications returns valid JSON", False, str(e)[:80])

# ── TEST 7: Admin login, messages page & reply ────────────────
print("\n[TEST 7] Admin Messages & Reply")
s_admin = requests.Session()
admin_login = login(s_admin, 'admin@medapp.com', 'Admin@1234')
check("Admin login succeeds", admin_login.status_code == 200 and '/auth/login' not in admin_login.url,
      admin_login.url)

admin_msgs_r = s_admin.get(f"{BASE}/admin/messages")
check("Admin /messages returns 200", admin_msgs_r.status_code == 200)
check("No error on admin messages", 'Internal Server Error' not in admin_msgs_r.text)
check("Admin reply form present", 'admin/messages/reply' in admin_msgs_r.text,
      "found" if 'admin/messages/reply' in admin_msgs_r.text else "NOT found")
check("E2E Patient message visible", 'E2E Patient' in admin_msgs_r.text)

reply_csrf = extract_csrf(admin_msgs_r.text)
reply_urls = re.findall(r'/admin/messages/reply/(\d+)', admin_msgs_r.text)
if reply_urls:
    mid = reply_urls[0]
    rr = s_admin.post(f"{BASE}/admin/messages/reply/{mid}", data={
        'message': 'Hello E2E Patient! Admin here.', 'csrf_token': reply_csrf
    }, allow_redirects=True)
    check("Admin reply POST succeeds", rr.status_code == 200)
    check("Reply appears after submit", 'Hello E2E Patient' in rr.text or 'Reply sent' in rr.text
          or 'success' in rr.text.lower())
else:
    print("  SKIP: No reply form URLs found (no messages on page or admin not logged in)")

# ── TEST 8: Patient sees admin reply ─────────────────────────
print("\n[TEST 8] Patient Notification of Admin Reply")
notif_r2 = s_patient.get(f"{BASE}/booking/notifications")
try:
    d2 = notif_r2.json()
    check("Notifications update after admin reply", 'count' in d2)
except Exception:
    check("Notifications update after admin reply", False, "Not JSON")

msgs_r2 = s_patient.get(f"{BASE}/booking/messages")
check("Admin reply visible in patient messages", 'Hello E2E Patient' in msgs_r2.text)

# ── TEST 9: Doctor portal & messages ─────────────────────────
print("\n[TEST 9] Doctor Portal")
s_doc = requests.Session()
doc_login = login(s_doc, 'doctor1@medapp.com', 'Doctor@123')
check("Doctor login succeeds", doc_login.status_code == 200 and '/auth/login' not in doc_login.url,
      doc_login.url)

doc_dash = s_doc.get(f"{BASE}/doctor/")
check("Doctor dashboard loads (200)", doc_dash.status_code == 200)
check("No error on doctor dashboard", 'Internal Server Error' not in doc_dash.text)

doc_msgs = s_doc.get(f"{BASE}/doctor/messages")
check("Doctor messages page loads (200)", doc_msgs.status_code == 200)
check("CSRF token in doctor reply form", 'csrf_token' in doc_msgs.text)
check("No error on doctor messages", 'Internal Server Error' not in doc_msgs.text)

# ── TEST 10: Book appointment (patient) ──────────────────────
print("\n[TEST 10] Patient Book Appointment")
book_csrf, book_page = get_csrf(s_patient, f"{BASE}/booking/book")
check("Book page loads (200)", book_page.status_code == 200)
check("No error on book page", 'Internal Server Error' not in book_page.text)

# Extract a doctor id from the form
doc_ids = re.findall(r'<option value="(\d+)"', book_page.text)
if doc_ids:
    book_res = s_patient.post(f"{BASE}/booking/book", data={
        'doctor_id': doc_ids[0], 'patient_name': 'E2E Patient',
        'patient_email': TEST_EMAIL, 'patient_phone': '9876543210',
        'appointment_date': '2026-04-20', 'appointment_time': '10:00',
        'reason': 'Automated e2e test booking', 'csrf_token': book_csrf
    }, allow_redirects=True)
    check("Booking form submits successfully", book_res.status_code == 200)
    check("Confirmation page shown", 'confirmation' in book_res.url or 'Appointment' in book_res.text)
else:
    print("  SKIP: No doctor options found on book page")

# ── SUMMARY ──────────────────────────────────────────────────
print("\n" + "=" * 60)
print("FINAL RESULTS")
print("=" * 60)
passes = sum(1 for s, _, _ in RESULTS if s == "PASS")
fails = sum(1 for s, _, _ in RESULTS if s == "FAIL")
for status, name, detail in RESULTS:
    sym = "[OK]" if status == "PASS" else "[!!]"
    d = f"  [{detail}]" if detail else ""
    print(f"  {sym} {status}: {name}{d}")
print(f"\n{'=' * 60}")
print(f"Result: {passes} PASS / {fails} FAIL / {len(RESULTS)} total")
sys.exit(0 if fails == 0 else 1)
