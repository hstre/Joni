#!/usr/bin/env bash
# Mirror Joni's memory onto this server as a durable, independent backup.
#
# Joni's memory is authored in ONE place (the autonomy loop -> main). This sets up a
# read-only mirror on the server so the brain also lives on hardware you own:
#   * a full-history clone of main, refreshed every 15 min (separate from the relay clone,
#     so nothing collides);
#   * one snapshot per day of the authoritative core + ledger + extensions, kept 30 days,
#     as easy point-in-time restore points.
# It never writes back - there is exactly one writer of memory, so no conflicts.
#
# Run as root:  sudo bash mirror_memory.sh
set -euo pipefail

USER_NAME="joni"
HOME_DIR="/home/${USER_NAME}"
REPO="${JONI_REPO:-https://github.com/hstre/Joni.git}"
MIRROR="${HOME_DIR}/joni/memory"            # full-history clone of main (the live memory)
SNAPS="${HOME_DIR}/joni/memory-snapshots"   # daily restore points

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo bash mirror_memory.sh)"; exit 1; }

echo "== clone/refresh the memory mirror (as ${USER_NAME}) =="
sudo -u "${USER_NAME}" bash -s <<EOF
set -euo pipefail
mkdir -p "${SNAPS}"
if [ -d "${MIRROR}/.git" ]; then
  git -C "${MIRROR}" fetch --quiet origin main && git -C "${MIRROR}" reset --hard --quiet origin/main
else
  git clone --quiet --branch main "${REPO}" "${MIRROR}"
fi
EOF

echo "== install the updater =="
cat > /usr/local/bin/joni-memory-mirror <<EOF
#!/usr/bin/env bash
# Refresh the mirror from main, then keep one snapshot per day (core + ledger + extensions).
set -euo pipefail
MIRROR="${MIRROR}"
SNAPS="${SNAPS}"
git -C "\${MIRROR}" fetch --quiet origin main
git -C "\${MIRROR}" reset --hard --quiet origin/main
day="\$(date -u +%Y-%m-%d)"
d="\${SNAPS}/\${day}"
mkdir -p "\${d}"
for f in state/layer9.json state/extensions.json state/joni_state.json protocol/protocol.jsonl; do
  [ -f "\${MIRROR}/\${f}" ] && cp -f "\${MIRROR}/\${f}" "\${d}/\$(basename "\${f}")" || true
done
# keep the 30 most recent days
ls -1dt "\${SNAPS}"/*/ 2>/dev/null | tail -n +31 | xargs -r rm -rf
EOF
chmod +x /usr/local/bin/joni-memory-mirror
chown -R "${USER_NAME}:${USER_NAME}" "${MIRROR}" "${SNAPS}"

echo "== systemd timer (every 15 min, runs as ${USER_NAME}) =="
cat > /etc/systemd/system/joni-memory.service <<EOF
[Unit]
Description=Mirror Joni's memory from main + daily snapshot
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${USER_NAME}
ExecStart=/usr/local/bin/joni-memory-mirror
EOF
cat > /etc/systemd/system/joni-memory.timer <<EOF
[Unit]
Description=Refresh Joni's memory mirror every 15 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now joni-memory.timer
systemctl start joni-memory.service

echo "== result =="
if [ -f "${MIRROR}/state/layer9.json" ]; then
  echo "memory mirror OK: $(du -h "${MIRROR}/state/layer9.json" | cut -f1) layer9.json"
  echo "snapshots so far:"; ls -1 "${SNAPS}" 2>/dev/null | tail -3
else
  echo "!! mirror missing state/layer9.json - check ${MIRROR}"
fi
