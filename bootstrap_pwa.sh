#!/usr/bin/env bash
# Fit4Academy — one-shot bootstrap to bring up the PWA locally.
#
# Run from the project root:
#   bash bootstrap_pwa.sh
#
# This script:
#   1. Installs Homebrew if missing (needs your admin password ONCE)
#   2. Installs Node.js 20 via brew
#   3. Installs the mobile app's npm packages
#   4. Builds the static web bundle (mobile/dist)
#   5. Starts the Flask backend on port 8080
#
# After it finishes, open http://localhost:8080/app/ in your browser
# (Safari or Chrome on the same Mac, or your phone if it's on the same Wi-Fi
# at http://<your-mac-ip>:8080/app/).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN="\033[1;32m"
RED="\033[1;31m"
YELLOW="\033[1;33m"
RESET="\033[0m"

step() { echo -e "${GREEN}▶${RESET} $*"; }
warn() { echo -e "${YELLOW}!${RESET} $*"; }
fail() { echo -e "${RED}✗${RESET} $*"; exit 1; }

# 1. Homebrew
if ! command -v brew >/dev/null 2>&1; then
    step "Installing Homebrew (this will ask for your admin password)…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for this shell
    if [ -d /opt/homebrew/bin ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [ -d /usr/local/bin ]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
else
    step "Homebrew already installed"
fi

# 2. Node.js
if ! command -v node >/dev/null 2>&1; then
    step "Installing Node.js 20…"
    brew install node@20
    brew link --overwrite --force node@20 || true
else
    NODE_VER=$(node --version)
    step "Node.js already installed ($NODE_VER)"
fi

# 3. Python deps for the backend
step "Installing Python dependencies (Flask, jwt, etc.)…"
pip3 install --user --quiet -r requirements.txt 2>/dev/null || \
    pip3 install --user --quiet flask flask-cors pyjwt python-dotenv requests bcrypt psycopg2-binary apscheduler stripe qrcode Pillow cloudinary twilio anthropic gunicorn

# 4. mobile/ npm install
step "Installing mobile app dependencies (≈3 minutes)…"
cd "$SCRIPT_DIR/mobile"
if [ ! -d node_modules ]; then
    npm install
else
    warn "mobile/node_modules already present; skipping npm install"
fi

# 5. Expo web build
step "Building the PWA (mobile/dist)…"
npx expo export -p web

cd "$SCRIPT_DIR"

# 6. Start Flask
step "Starting backend at http://localhost:8080"
echo
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${RESET}"
echo -e "${GREEN} Fit4Academy is up.${RESET}"
echo
echo -e "  Admin web:   ${GREEN}http://localhost:8080/${RESET}"
echo -e "  PWA (aluno): ${GREEN}http://localhost:8080/app/${RESET}"
echo
echo -e "  Staff login: seeds13 / Seeds2026!"
echo -e "  Member sign-up: create a member at /members/add, get the PIN from /members/<id>/qr,"
echo -e "                  then sign up in the PWA at /app/ using that PIN + an email."
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${RESET}"
echo

export FLASK_DEBUG=1
python3 app.py
