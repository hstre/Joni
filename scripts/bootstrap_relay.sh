#!/usr/bin/env bash
# Bootstrap the Joni relay on a FRESH Ubuntu 24.04 box. Run as root, once.
#
#   ssh root@<box>            # after rebuilding the server to Ubuntu 24.04
#   curl -fsSL https://raw.githubusercontent.com/hstre/Joni/main/scripts/bootstrap_relay.sh | bash
#   # (or: scp this file over and `bash bootstrap_relay.sh`)
#
# It hardens the box, installs Joni, and starts the relay in DRY-RUN (posts nothing). It does
# NOT add any secrets - you do that afterwards in /home/joni/joni/relay.env. Idempotent.
set -euo pipefail

REPO="${JONI_REPO:-https://github.com/hstre/Joni.git}"
USER_NAME="joni"
HOME_DIR="/home/${USER_NAME}"
APP_DIR="${HOME_DIR}/joni/repo"

[ "$(id -u)" -eq 0 ] || { echo "run as root"; exit 1; }

echo "== packages =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3-venv python3-pip ufw fail2ban unattended-upgrades

echo "== unprivileged user =="
id -u "${USER_NAME}" >/dev/null 2>&1 || adduser --disabled-password --gecos "" "${USER_NAME}"
install -d -o "${USER_NAME}" -g "${USER_NAME}" -m 700 "${HOME_DIR}/.ssh"
if [ -f /root/.ssh/authorized_keys ]; then
  install -o "${USER_NAME}" -g "${USER_NAME}" -m 600 \
    /root/.ssh/authorized_keys "${HOME_DIR}/.ssh/authorized_keys"
fi

echo "== ssh hardening (keys only, no root login) =="
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart ssh || systemctl restart sshd || true

echo "== firewall: only SSH in, all out =="
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable
systemctl enable --now fail2ban

echo "== clone + venv (as ${USER_NAME}) =="
sudo -u "${USER_NAME}" bash -s <<EOF
set -euo pipefail
mkdir -p "${HOME_DIR}/joni"
if [ -d "${APP_DIR}/.git" ]; then
  git -C "${APP_DIR}" pull --ff-only --quiet
else
  git clone --quiet "${REPO}" "${APP_DIR}"
fi
python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --quiet --upgrade pip
"${APP_DIR}/.venv/bin/pip" install --quiet -e "${APP_DIR}[dev,llm,pdf,embed]"
# a secrets file you fill in later; root-readable only
[ -f "${HOME_DIR}/joni/relay.env" ] || printf '# fill per platform you enable; never commit\n' > "${HOME_DIR}/joni/relay.env"
chmod 600 "${HOME_DIR}/joni/relay.env"
EOF

echo "== systemd unit (DRY-RUN by default) =="
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

echo
echo "== done =="
echo "Relay is running in DRY-RUN (posts nothing). Watch it:  journalctl -u joni-relay -f"
echo "Next: put credentials in ${HOME_DIR}/joni/relay.env, then we wire the first adapter."
echo "Approve a draft (from anywhere with the repo):  python -m joni.autonomy approve <id>"
