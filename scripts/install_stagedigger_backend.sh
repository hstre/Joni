#!/usr/bin/env bash
# Phase 2: bring up the Stage Digger FastAPI backend and wire it behind nginx.
#
# The built frontend already calls same-origin /api/... , so we only need to:
#   * run uvicorn (app.main:app) on 127.0.0.1:8000 as a systemd service (real AUTH_SECRET);
#   * let the backend re-render region packages into the nginx-served /v1 dir;
#   * add an nginx  location /api/ -> 127.0.0.1:8000  proxy (static app + /v1 unchanged).
# The backend is NOT exposed directly (loopback only) - only reachable through nginx.
#
# Run after install_stagedigger.sh, as root:  sudo bash install_stagedigger_backend.sh
set -euo pipefail

USER_NAME="joni"
HOME_DIR="/home/${USER_NAME}"
BACKEND="${HOME_DIR}/stagedigger/backend"
WEBROOT="/var/www/stagedigger"
V1="${WEBROOT}/v1"

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo bash install_stagedigger_backend.sh)"; exit 1; }
[ -x "${BACKEND}/.venv/bin/uvicorn" ] || { echo "backend venv missing - run install_stagedigger.sh first"; exit 1; }

echo "== generate a real AUTH_SECRET =="
SECRET="$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 48)"

echo "== make the served /v1 dir writable by the backend (for re-rendered packages) =="
mkdir -p "${V1}"
chown -R "${USER_NAME}:${USER_NAME}" "${V1}"     # backend (joni) writes, nginx (www-data) reads

echo "== systemd service: uvicorn on 127.0.0.1:8000 =="
cat > /etc/systemd/system/stagedigger-backend.service <<EOF
[Unit]
Description=Stage Digger backend (FastAPI / uvicorn)
After=network-online.target
Wants=network-online.target

[Service]
User=${USER_NAME}
WorkingDirectory=${BACKEND}
Environment=AUTH_SECRET=${SECRET}
Environment=STAGEDIGGER_PACKAGE_DIRS=${V1}
ExecStart=${BACKEND}/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
NoNewPrivileges=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now stagedigger-backend

echo "== nginx: add /api/ proxy (static app + /v1 stay as-is) =="
cat > /etc/nginx/sites-available/stagedigger <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    root ${WEBROOT};
    index index.html;

    # dynamic API -> FastAPI backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # static regional packages (re-rendered by the backend on writes)
    location /v1/ { try_files \$uri =404; add_header Cache-Control "public, max-age=60"; }

    # SPA
    location / { try_files \$uri \$uri/ /index.html; }
}
EOF
ln -sf /etc/nginx/sites-available/stagedigger /etc/nginx/sites-enabled/stagedigger
nginx -t
systemctl reload nginx

echo
echo "== verify =="
sleep 2
echo -n "backend /health (direct):  "; curl -fsS --max-time 8 http://127.0.0.1:8000/health || echo "FAILED"
echo
echo -n "via nginx /api/auth/me (401 = reachable, ok): "
curl -s -o /dev/null -w "HTTP %{http_code}\n" --max-time 8 http://127.0.0.1/api/auth/me
echo
echo "== done =="
echo "Backend live behind nginx. Register/login/create-digs now work at http://<your-ip>/"
echo "Service:  systemctl status stagedigger-backend --no-pager"
