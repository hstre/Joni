#!/usr/bin/env bash
# One-off fix for a box already provisioned on Ubuntu 22.04, where the relay failed to
# install because the system Python is 3.10 but joni needs >=3.11. Installs Python 3.11,
# rebuilds the joni venv with it, and installs+starts the relay service. Run as root:
#   sudo bash fix_python311.sh
set -euo pipefail

USER_NAME="joni"
HOME_DIR="/home/${USER_NAME}"
APP_DIR="${HOME_DIR}/joni/repo"

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo bash fix_python311.sh)"; exit 1; }

echo "== install Python 3.11 (deadsnakes) =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -y
apt-get install -y python3.11 python3.11-venv

echo "== rebuild venv + install joni (as ${USER_NAME}) =="
sudo -u "${USER_NAME}" bash -s <<EOF
set -euo pipefail
cd "${APP_DIR}"
git pull --ff-only --quiet || true
rm -rf .venv
python3.11 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -e .
EOF

echo "== install + start service =="
cat > /etc/systemd/system/joni-relay.service <<EOF
[Unit]
Description=Joni forum relay (moderated, dry-run by default)
After=network-online.target
Wants=network-online.target

[Service]
User=${USER_NAME}
WorkingDirectory=${APP_DIR}
Environment=JONI_AUTONOMY_ROOT=${APP_DIR}
EnvironmentFile=-${HOME_DIR}/joni/relay.env
ExecStart=${APP_DIR}/.venv/bin/python -m joni.relay --interval 300
Restart=on-failure
RestartSec=30
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=${APP_DIR}
ProtectHome=read-only
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now joni-relay
sleep 2
echo "== result =="
systemctl is-active joni-relay
