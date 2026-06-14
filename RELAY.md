# Joni Relay — a Hetzner VPS with a real IPv4

This is the runbook for giving Joni a **relay point**: a small, always-on VPS with its own
stable IPv4 that lets him register on forums, read replies, and — only after you approve each
post — speak. The protected core, the gate, the hash-chained ledger and the Git audit trail do
**not** move. The VPS is a *runner + relay*, never a new authority. People remain a source.

Chosen rollout: **staged** (relay first, then the whole loop) with a **moderation queue**
(nothing is posted without your explicit approval).

---

## What the VPS changes — and what it must not

**Buys us:** a stable, non-shared IPv4 (forum APIs/registration; Actions IPs are shared and
often blocked), continuous operation (no 6h job cap), a warm embedding model, and near-real-time
ingestion of replies.

**Must not change:** the governance boundary. The VPS runs only the *peripheral* loop + I/O.
The core stays frozen (`python -m joni.autonomy verify` still gates every cycle), state still
lands in Git (the ledger/site remain the source of truth), and forum people are still ingested
as `OriginType.SOURCE` — never the privileged `HUMAN` origin.

**One primary writer.** The loop writes Git state; two writers would race. So when the VPS runs
the loop, the GitHub Actions loop must be **off** (or a cold standby). See Phase 2.

---

## The moderation gate (already in the repo)

The loop **never posts**. It only drafts polite questions (`state/forum_outbox.json`, status
`drafted`) and ingests replies (`state/forum_inbox.json`). A post leaves Joni only when:

1. a human approves the draft id — `python -m joni.autonomy approve <draft-id>` (writes
   `state/forum_approved.json`), or adds the id to that file directly; then
2. the relay calls `humans.select_postable(outbox, approved_ids)` — which releases only
   approved, not-yet-posted drafts — and posts them via the platform adapter.

`select_postable` is a pure, tested function: it is the single chokepoint. No approval ⇒ no post.

---

## Phase 1 — relay only (low risk, Actions stays primary)

The Actions loop keeps running and owns the Git state. The VPS does three things: **register**
accounts (a human, interactive, one-time), **ingest** replies into `state/forum_inbox.json`, and
**post** approved drafts. It commits those two files back; the loop picks them up next cycle.

### 1. Provision

Hetzner Cloud **CX22** (2 vCPU / 4 GB, ~€4–5/mo, IPv4 included) is ample. Ubuntu 24.04 LTS.
Add your SSH key at create time. Then, as root, create an unprivileged user and lock the box
down:

```bash
adduser --disabled-password --gecos "" joni
install -d -o joni -g joni /home/joni/.ssh
cp /root/.ssh/authorized_keys /home/joni/.ssh/ && chown joni:joni /home/joni/.ssh/authorized_keys
chmod 700 /home/joni/.ssh && chmod 600 /home/joni/.ssh/authorized_keys

# SSH: keys only, no root login
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart ssh

# Firewall: only SSH in; everything else out is allowed
apt-get update && apt-get install -y ufw fail2ban unattended-upgrades git python3-venv
ufw default deny incoming && ufw default allow outgoing && ufw allow OpenSSH && ufw --force enable
systemctl enable --now fail2ban
dpkg-reconfigure -plow unattended-upgrades
```

The relay makes only **outbound** calls, so no inbound port beyond SSH is needed. (If you later
add a webhook receiver, terminate it behind TLS + a bearer token and open only that port.)

### 2. Secrets (root-only, never committed)

```bash
install -d -o joni -g joni -m 700 /home/joni/joni
cat > /home/joni/joni/relay.env <<'EOF'
# Forum credentials — fill per platform you enable. Treat as compromised if leaked.
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USERNAME=...
REDDIT_PASSWORD=...
HF_TOKEN=...
# Git push (a fine-grained PAT scoped to the Joni repo, contents:write)
JONI_GIT_TOKEN=...
EOF
chown joni:joni /home/joni/joni/relay.env && chmod 600 /home/joni/joni/relay.env
```

### 3. Clone + venv (as `joni`)

```bash
git clone https://github.com/hstre/Joni.git /home/joni/joni/repo
cd /home/joni/joni/repo
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,llm,pdf,embed]"
```

### 4. The relay agent

`python -m joni.relay` (in `src/joni/relay/`) runs on a loop: `git pull` → release only
approved+unposted drafts via `humans.select_postable` → post through a per-platform adapter →
ingest replies into `forum_inbox.json` → `git commit`+push the two state files. **Default
dry-run**: it logs what it *would* post and posts nothing. No adapter is wired for real posting
yet (`adapters.py`, all `implemented = False`), so even `--live` posts nothing until one is
implemented with your credentials. Account **registration stays manual** (interactive,
human-run) — bots don't self-register within ToS.

The fastest path: rebuild the box to Ubuntu 24.04, then run `scripts/bootstrap_relay.sh` as
root — it does the hardening below, installs Joni, and starts the relay in dry-run under
systemd. The steps below are what that script automates (read them before running it).

### 5. Run it under systemd

```ini
# /etc/systemd/system/joni-relay.service
[Unit]
Description=Joni forum relay (moderated)
After=network-online.target
Wants=network-online.target

[Service]
User=joni
WorkingDirectory=/home/joni/joni/repo
EnvironmentFile=/home/joni/joni/relay.env
Environment=JONI_AUTONOMY_ROOT=/home/joni/joni/repo
ExecStart=/home/joni/joni/repo/.venv/bin/python -m joni.relay --interval 300
Restart=on-failure
RestartSec=30
# hardening
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=/home/joni/joni/repo
ProtectHome=read-only
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload && systemctl enable --now joni-relay
journalctl -u joni-relay -f
```

---

## Phase 2 — move the whole loop to the VPS

Once the relay is trusted: run the autonomy loop on the box too and retire Actions.

- Add a second systemd unit (or a `flock`-guarded timer) running `python -m joni.autonomy run`
  on the same interval; it commits/pushes `state/`, `protocol/`, `docs/` just like Actions does.
- **Stop the Actions loop** so there is one writer: disable the `schedule` in
  `.github/workflows/autonomy.yml` (keep `workflow_dispatch` as a manual fallback). Keep
  `joni-auftrag.yml` — that still runs Claude on demand and is independent.
- Use `flock` so the loop and the relay never push concurrently (or run them as one ordered
  service: loop, then relay, then push once).

---

## Moderation flow (day to day)

1. Joni drafts questions → visible on the dashboard card "Menschen & Foren" and in
   `state/forum_outbox.json`, each with an id like `FA-42-1a2b3c`.
2. You review and approve the good ones: `python -m joni.autonomy approve FA-42-1a2b3c`.
3. The relay posts only those, records the URL, and ingests replies — which Joni then judges
   **as strictly as any source** (they can be contradicted; a reply never wins by authority).
4. Loosen per platform only when you're happy with the behaviour.

---

## Rules of the road (non-negotiable)

- **Respect each platform's ToS / bot policy.** Use official APIs (Reddit API, HF Hub API);
  identify as a bot where required; obey rate limits; never vote-ring, brigade, or spam. HN in
  particular discourages automated posting — treat it as read-mostly unless explicitly allowed.
- **Outward + irreversible.** A public post can't be unsaid. That's why posting is gated behind
  your approval and starts per-platform, dry-run first.
- **Secrets live only on the box**, root-readable, never in Git. Rotate on any suspicion.
- **The core never moves to the VPS's authority.** `verify` runs every cycle; if the lock fails,
  the loop stops.
