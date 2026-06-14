#!/usr/bin/env bash
# Install Stage Digger (the location-based adventure PWA) alongside Joni on this box.
# Phase 1: build the static frontend (with seeded demo regional packages) and serve it via
# nginx on port 80. The FastAPI backend (write/check endpoints) is a later step.
#
# Self-checks free disk and aborts if there is not enough room. Run as root:
#   sudo bash install_stagedigger.sh
set -euo pipefail

USER_NAME="joni"
HOME_DIR="/home/${USER_NAME}"
APP_DIR="${HOME_DIR}/stagedigger"
WEBROOT="/var/www/stagedigger"
REPO="https://github.com/hstre/Stagedigger-.git"
NEED_GB=3

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo bash install_stagedigger.sh)"; exit 1; }

echo "== disk space check (need ${NEED_GB} GB free) =="
avail=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
echo "   free on /: ${avail} GB"
[ "${avail:-0}" -ge "${NEED_GB}" ] || { echo "   not enough space - aborting, nothing changed."; exit 1; }

echo "== packages: nginx, Node.js 20, build tools =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx git curl python3.11 python3.11-venv
if ! command -v node >/dev/null 2>&1 || [ "$(node -v 2>/dev/null | cut -dv -f2 | cut -d. -f1)" -lt 18 ] 2>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/nodesource.sh
  bash /tmp/nodesource.sh
  apt-get install -y nodejs
fi
echo "   node $(node -v) / npm $(npm -v)"

echo "== clone + build (as ${USER_NAME}) =="
sudo -u "${USER_NAME}" bash -s <<EOF
set -euo pipefail
if [ -d "${APP_DIR}/.git" ]; then git -C "${APP_DIR}" pull --ff-only --quiet || true
else git clone --quiet "${REPO}" "${APP_DIR}"; fi

# backend deps (needed to render the demo regional packages)
cd "${APP_DIR}/backend"
python3.11 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/python seed.py        # renders /v1/<geohash>.json into ../frontend/public/v1/

# frontend build -> dist/
cd "${APP_DIR}/frontend"
npm install --no-audit --no-fund --silent
npm run build
EOF

echo "== publish static site to ${WEBROOT} =="
rm -rf "${WEBROOT}"
mkdir -p "${WEBROOT}"
cp -r "${APP_DIR}/frontend/dist/." "${WEBROOT}/"
chown -R www-data:www-data "${WEBROOT}"

echo "== nginx site (port 80, SPA fallback) =="
cat > /etc/nginx/sites-available/stagedigger <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    root ${WEBROOT};
    index index.html;
    # static regional packages: long cache; the service worker revalidates
    location /v1/ { try_files \$uri =404; add_header Cache-Control "public, max-age=300"; }
    location / { try_files \$uri \$uri/ /index.html; }
}
EOF
ln -sf /etc/nginx/sites-available/stagedigger /etc/nginx/sites-enabled/stagedigger
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "== open the firewall for HTTP =="
ufw allow 80/tcp || true

echo
echo "== done =="
echo "Stage Digger is live at:  http://$(curl -fsS ifconfig.me 2>/dev/null || echo YOUR_IP)/"
echo "(static demo + offline PWA; backend write-endpoints are a later step)"
