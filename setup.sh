#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#   Clinical Couture — One-Step Setup & Launch
#   Usage:  bash setup.sh [--docker] [--test]
# ═══════════════════════════════════════════════════════════
set -euo pipefail

BLUE='\033[1;34m'; GREEN='\033[1;32m'; YELLOW='\033[1;33m'; RED='\033[1;31m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

DOCKER=false
RUN_TESTS=false
for arg in "$@"; do
  case $arg in
    --docker) DOCKER=true ;;
    --test)   RUN_TESTS=true ;;
  esac
done

echo ""
echo -e "${BLUE}╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Clinical Couture — Setup & Launch  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# ── Docker path ───────────────────────────────────────
if $DOCKER; then
  command -v docker >/dev/null 2>&1 || error "Docker not found. Install Docker first."
  command -v docker-compose >/dev/null 2>&1 || error "docker-compose not found."

  if [ ! -f ".env" ]; then
    cp .env.example .env
    warn ".env created from .env.example — edit your API keys before production use."
  fi

  mkdir -p data
  info "Building and starting Docker containers…"
  docker-compose up --build -d
  success "Clinical Couture is running at http://localhost:5000"
  echo ""
  echo -e "  Admin login: check ADMIN_EMAIL / ADMIN_PASSWORD in your .env"
  echo -e "  Logs:  ${YELLOW}docker-compose logs -f${NC}"
  echo -e "  Stop:  ${YELLOW}docker-compose down${NC}"
  exit 0
fi

# ── Local Python path ─────────────────────────────────
command -v python3 >/dev/null 2>&1 || error "python3 not found."
PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python $PYTHON_VER detected."

# Create virtual environment
if [ ! -d "venv" ]; then
  info "Creating virtual environment…"
  python3 -m venv venv
  success "Virtual environment created."
else
  info "Virtual environment already exists."
fi

# Activate
source venv/bin/activate

# Install dependencies
info "Installing dependencies…"
pip install --upgrade pip -q
pip install -r requirements.txt -q
success "Dependencies installed."

# Set up .env
if [ ! -f ".env" ]; then
  cp .env.example .env
  warn ".env created from .env.example"
  warn "Edit .env and add your OPENAI_API_KEY and GOOGLE_MAPS_KEY before use."
else
  info ".env already exists."
fi

# Run tests
if $RUN_TESTS; then
  info "Running tests…"
  pip install pytest -q
  pytest tests/ -v --tb=short
  success "All tests passed."
fi

# Launch
success "Setup complete! Starting Clinical Couture…"
echo ""
echo -e "  🌐  App:    ${GREEN}http://localhost:5000${NC}"
echo -e "  🔑  Admin:  ${GREEN}http://localhost:5000/admin/${NC}"
echo -e "  📧  Admin credentials: see ADMIN_EMAIL / ADMIN_PASSWORD in .env"
echo ""
echo -e "  To stop: ${YELLOW}Ctrl+C${NC}"
echo -e "  For Docker: ${YELLOW}bash setup.sh --docker${NC}"
echo ""

export FLASK_ENV=development
python3 app.py
