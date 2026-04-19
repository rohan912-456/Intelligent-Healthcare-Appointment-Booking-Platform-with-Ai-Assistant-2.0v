# 🏥 Clinical Couture — Smart Medical Appointment Platform

[![CI](https://github.com/YOUR_USERNAME/clinical_couture/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/clinical_couture/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)](https://flask.palletsprojects.com)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docker.com)

A production-grade Flask application for medical appointment booking with AI-assisted chat, built for Nagpur, India.

---

## 🚀 One-Step GitHub Deployment

> **Prerequisites:** [git](https://git-scm.com) and [GitHub CLI](https://cli.github.com) installed.

```bash
bash push_to_github.sh
```

This single command will:
1. Check prerequisites
2. Log you in to GitHub (if needed)
3. Ask for a repo name + visibility
4. `git init` → commit all code → create GitHub repo → push
5. Print the Secrets to add for CI/CD
6. Open the repo in your browser

---

## ⚡ Run Locally

```bash
bash setup.sh           # Local Python (auto venv)
bash setup.sh --docker  # Docker Compose
bash setup.sh --test    # Run pytest first, then launch
```

App: **http://localhost:5000** | Admin: **http://localhost:5000/admin/**

---

## 🔑 Configuration

Edit `.env` (auto-created from `.env.example` on first run):

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Long random string |
| `OPENAI_API_KEY` | Recommended | Enables AI chatbot |
| `GOOGLE_MAPS_KEY` | Optional | Enables interactive map |
| `MAIL_USERNAME` | Optional | Gmail for confirmations |
| `MAIL_PASSWORD` | Optional | Gmail App Password |
| `ADMIN_EMAIL` | Optional | Default: admin@clinicalcouture.com |
| `ADMIN_PASSWORD` | Optional | Default: Admin@1234 |

### GitHub Actions Secrets

Add in **Settings → Secrets and variables → Actions**:

| Secret | Description |
|---|---|
| `SECRET_KEY` | Flask session secret |
| `OPENAI_API_KEY` | OpenAI key |
| `GOOGLE_MAPS_KEY` | Maps key |
| `MAIL_USERNAME` | Gmail username |
| `MAIL_PASSWORD` | Gmail App Password |
| `DEPLOY_HOST` | (Optional) VPS IP |
| `DEPLOY_USER` | (Optional) VPS SSH user |
| `DEPLOY_KEY` | (Optional) VPS SSH private key |
| `DEPLOY_PATH` | (Optional) Path on VPS |

---

## 🏗️ CI/CD Pipeline

```
push to main / PR
      │
      ├─ ci.yml ── pytest · flake8 · docker build check
      │
      └─ deploy.yml (main only)
          ├── Push Docker image → ghcr.io/YOUR_USERNAME/clinical_couture:latest
          └── (Optional) SSH deploy to VPS
```

---

## 📁 Project Structure

```
medical_app/
├── app.py                    # App factory + DB seeding
├── config.py                 # Dev / Prod config classes
├── extensions.py             # Flask extensions
├── models.py                 # SQLAlchemy models
├── forms.py                  # WTForms with full validation
├── routes/
│   ├── main.py               # Home + Contact
│   ├── auth.py               # Register / Login / Logout
│   ├── booking.py            # Book / My Bookings / Cancel
│   ├── chat.py               # AI Chat API (rate-limited)
│   └── admin.py              # Admin panel
├── templates/                # Jinja2 templates
├── static/                   # CSS + JS
├── tests/test_app.py         # pytest suite
├── .github/workflows/
│   ├── ci.yml                # Test + lint + Docker build
│   └── deploy.yml            # Push to GHCR + optional SSH
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── setup.sh                  # One-step local launcher
└── push_to_github.sh         # One-step GitHub push script
```

---

## 🔒 Security

- Passwords hashed with Werkzeug
- CSRF tokens on every form
- XSS prevention: `bleach` + `textContent`
- Rate limiting on AI chat endpoint
- `.env` excluded from git
- Non-root user in Docker container

---

## 🧪 Tests

```bash
source venv/bin/activate && pytest tests/ -v
```

---

## 🐳 Deploy to a VPS

```bash
git clone https://github.com/YOUR_USERNAME/clinical_couture.git
cd medical_app && cp .env.example .env
nano .env   # fill in your keys
bash setup.sh --docker
```
