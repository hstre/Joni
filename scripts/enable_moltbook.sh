#!/usr/bin/env bash
# Wire Joni's relay to Moltbook and go live - run ON THE BOX, as root:
#
#   sudo bash enable_moltbook.sh <moltbook_api_key> [submolt]
#
# The key is taken as an argument so it NEVER lives in this (public) script - it goes only
# into the root-only relay.env on this box. The relay then posts to Moltbook, but still ONLY
# drafts a human approved (the moderation gate stays on). Idempotent.
set -euo pipefail

KEY="${1:?usage: sudo bash enable_moltbook.sh <moltbook_api_key> [submolt]}"
SUBMOLT="${2:-m/ai}"
USER_NAME="joni"
HOME_DIR="/home/${USER_NAME}"
APP_DIR="${HOME_DIR}/joni/repo"
ENVF="${HOME_DIR}/joni/relay.env"
UNIT="/etc/systemd/system/joni-relay.service"

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo bash enable_moltbook.sh <key> [submolt])"; exit 1; }

echo "== 1) key + submolt into ${ENVF} (root-only) =="
touch "${ENVF}"
grep -v '^MOLTBOOK_' "${ENVF}" > "${ENVF}.tmp" 2>/dev/null || true
{ echo "MOLTBOOK_API_KEY=${KEY}"; echo "MOLTBOOK_SUBMOLT=${SUBMOLT}"; } >> "${ENVF}.tmp"
mv "${ENVF}.tmp" "${ENVF}"
chown "${USER_NAME}:${USER_NAME}" "${ENVF}"
chmod 600 "${ENVF}"

echo "== 2) pull the latest code (with the Moltbook adapter) =="
sudo -u "${USER_NAME}" git -C "${APP_DIR}" pull --ff-only --quiet || true
sudo -u "${USER_NAME}" "${APP_DIR}/.venv/bin/pip" install --quiet -e "${APP_DIR}" || true

echo "== 3) flip the relay to --live (only implemented+credentialed adapters can post) =="
grep -q -- '--live' "${UNIT}" || sed -i 's/-m joni.relay /-m joni.relay --live /' "${UNIT}"
systemctl daemon-reload
systemctl restart joni-relay

echo
echo "== done =="
echo "Relay is now --live with Moltbook wired (submolt ${SUBMOLT})."
echo "It still posts ONLY drafts you approved. To approve one:"
echo "  cd ${APP_DIR} && sudo -u ${USER_NAME} .venv/bin/python -m joni.autonomy approve <draft-id>"
echo "Watch it:  journalctl -u joni-relay -f"
systemctl is-active joni-relay