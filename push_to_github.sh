#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#   MedApp — One-Step GitHub Deployment
#   Usage:  bash push_to_github.sh
#
#   What this does:
#     1. Checks git + gh CLI are installed
#     2. Logs you in to GitHub (if needed)
#     3. Creates a new GitHub repo
#     4. Initialises git, commits all code
#     5. Pushes to GitHub
#     6. Opens the repo in your browser
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Colours ──────────────────────────────────────────
BLUE='\033[1;34m'; GREEN='\033[1;32m'
YELLOW='\033[1;33m'; RED='\033[1;31m'
CYAN='\033[1;36m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }
step()    { echo -e "\n${CYAN}▶ $*${NC}"; }

# ─────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    MedApp — Push to GitHub in One Step       ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Check prerequisites ───────────────────────
step "Checking prerequisites…"

command -v git >/dev/null 2>&1  || error "git not found. Install from https://git-scm.com"
success "git found: $(git --version)"

if ! command -v gh >/dev/null 2>&1; then
  echo ""
  warn "GitHub CLI (gh) is not installed."
  echo -e "  Install it from: ${CYAN}https://cli.github.com${NC}"
  echo ""
  echo -e "  ${YELLOW}macOS:${NC}    brew install gh"
  echo -e "  ${YELLOW}Windows:${NC}  winget install GitHub.cli"
  echo -e "  ${YELLOW}Ubuntu:${NC}   sudo apt install gh"
  echo ""
  error "Please install gh and re-run this script."
fi
success "GitHub CLI found: $(gh --version | head -1)"

# ── Step 2: GitHub authentication ─────────────────────
step "Checking GitHub authentication…"

if ! gh auth status >/dev/null 2>&1; then
  warn "Not logged in to GitHub. Starting login…"
  gh auth login
else
  GH_USER=$(gh api user --jq .login 2>/dev/null || echo "unknown")
  success "Logged in as: ${GH_USER}"
fi

# ── Step 3: Configure repo ────────────────────────────
step "Repository configuration…"

# Detect if we're already in the project folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DEFAULT_REPO="medapp"
echo -e "  Enter a GitHub repository name (default: ${CYAN}${DEFAULT_REPO}${NC}):"
read -r REPO_NAME
REPO_NAME="${REPO_NAME:-$DEFAULT_REPO}"
REPO_NAME=$(echo "$REPO_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

echo -e "  Repository visibility — ${CYAN}public${NC} or ${CYAN}private${NC}? (default: public):"
read -r VISIBILITY
VISIBILITY="${VISIBILITY:-public}"
if [[ "$VISIBILITY" != "private" ]]; then VISIBILITY="public"; fi

echo -e "  Short description (optional):"
read -r REPO_DESC
REPO_DESC="${REPO_DESC:-Medical appointment booking app built with Flask}"

# ── Step 4: Initialise git ────────────────────────────
step "Initialising git repository…"

if [ -d ".git" ]; then
  warn ".git already exists — skipping git init."
else
  git init
  success "Initialised git repository."
fi

# Set default branch to main
git checkout -B main 2>/dev/null || true

# ── Step 5: First commit ──────────────────────────────
step "Staging and committing files…"

# Ensure .env is never committed
if [ ! -f ".gitignore" ]; then
  echo ".env" > .gitignore
fi

git add -A
git diff --cached --quiet && warn "Nothing new to commit." || {
  git commit -m "🏥 Initial commit — MedApp production-ready Flask app

Features:
- Flask Blueprints architecture (auth, booking, chat, admin)
- SQLAlchemy + SQLite with auto-migration
- User authentication (Flask-Login + Werkzeug)
- Appointment booking with email confirmation
- AI chatbot (OpenAI GPT-3.5, conversation history, rate-limited)
- XSS protection via bleach + textContent rendering
- CSRF protection on all forms
- Admin dashboard with stats, doctor/booking/user management
- Google Maps integration
- Docker + docker-compose support
- GitHub Actions CI/CD (test + lint + Docker build + push)
- pytest suite with 10 tests"
  success "Code committed."
}

# ── Step 6: Create GitHub repo ────────────────────────
step "Creating GitHub repository '${REPO_NAME}' (${VISIBILITY})…"

if gh repo view "$REPO_NAME" >/dev/null 2>&1; then
  warn "Repository '${REPO_NAME}' already exists on GitHub. Skipping creation."
  REPO_URL=$(gh repo view "$REPO_NAME" --json url --jq .url)
else
  gh repo create "$REPO_NAME" \
    --${VISIBILITY} \
    --description "$REPO_DESC" \
    --source=. \
    --remote=origin \
    --push

  REPO_URL=$(gh repo view "$REPO_NAME" --json url --jq .url)
  success "Repository created: ${REPO_URL}"
fi

# ── Step 7: Push code ─────────────────────────────────
step "Pushing code to GitHub…"

# Set upstream if not already set
if ! git remote get-url origin >/dev/null 2>&1; then
  GH_USER=$(gh api user --jq .login)
  git remote add origin "https://github.com/${GH_USER}/${REPO_NAME}.git"
fi

git push -u origin main
success "Code pushed to GitHub."

# ── Step 8: Set up GitHub Secrets prompt ──────────────
step "GitHub Secrets — for CI/CD to work, add these in your repo settings:"
echo ""
echo -e "  ${YELLOW}Settings → Secrets and variables → Actions → New repository secret${NC}"
echo ""
echo -e "  ${CYAN}SECRET_KEY${NC}          →  $(python3 -c 'import secrets; print(secrets.token_hex(32))' 2>/dev/null || echo 'your-long-random-secret')"
echo -e "  ${CYAN}OPENAI_API_KEY${NC}      →  sk-... (your OpenAI key)"
echo -e "  ${CYAN}GOOGLE_MAPS_KEY${NC}     →  (optional, for maps)"
echo -e "  ${CYAN}MAIL_USERNAME${NC}       →  (optional, Gmail)"
echo -e "  ${CYAN}MAIL_PASSWORD${NC}       →  (optional, Gmail App Password)"
echo ""

# ── Done ──────────────────────────────────────────────
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         ✅  All Done!                        ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  🔗  Repo:      ${CYAN}${REPO_URL}${NC}"
echo -e "  ⚙️   Actions:   ${CYAN}${REPO_URL}/actions${NC}"
echo -e "  🔑  Secrets:   ${CYAN}${REPO_URL}/settings/secrets/actions${NC}"
echo ""
echo -e "  To run locally:"
echo -e "    ${YELLOW}bash setup.sh${NC}"
echo ""
echo -e "  To deploy with Docker:"
echo -e "    ${YELLOW}bash setup.sh --docker${NC}"
echo ""

# Open in browser (optional)
echo -e "  Open repo in browser? (y/N):"
read -r OPEN_BROWSER
if [[ "${OPEN_BROWSER,,}" == "y" ]]; then
  gh repo view "$REPO_NAME" --web
fi
