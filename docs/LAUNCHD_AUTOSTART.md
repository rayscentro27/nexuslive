# Nexus AI — launchd Autostart

## What launchd Is Doing

macOS **launchd** is the system's service manager. Nexus registers user-level
services that run under `raymonddavis` — not root — and restart automatically
if they crash.

All services bind to **localhost only** (`127.0.0.1`). Nothing is exposed to
the LAN or internet unless explicitly tunnelled (e.g. Tailscale, ngrok).

---

## Services That Start Automatically on Boot

| Service | Port | Label | Managed by |
|---|---|---|---|
| OpenClaw gateway | 18789 | `ai.openclaw.gateway` | OpenClaw's own plist |
| Telegram monitor | — | `com.raymonddavis.nexus.telegram` | Nexus plist |
| Dashboard | 3000 (localhost) | `com.raymonddavis.nexus.dashboard` | Nexus plist |
| Signal router | 8000 (localhost) | `com.nexus.signal-router` | Nexus plist |
| Signal review poller | — | `com.nexus.signal-review` | Nexus plist |
| Strategy Lab | scheduled | `com.nexus.strategy-lab` | Nexus plist (interval job) |
| Bootstrap | — | `com.raymonddavis.nexus` | Nexus plist (one-shot) |

**What does NOT happen automatically (by design):**
- Live broker execution — blocked by `DRY_RUN=True`
- Automated trade execution — blocked unless the engine is deliberately reconfigured

### Network binding

| Service | Binds to | Why |
|---|---|---|
| OpenClaw gateway | `127.0.0.1` (loopback) | OpenClaw default |
| Dashboard | `127.0.0.1` | hardened, localhost only |
| Signal router | `127.0.0.1` | hardened, localhost only |

> If you need TradingView webhooks to reach the signal router from outside,
> use a reverse proxy (nginx, Caddy) or a tunnel (ngrok, Tailscale) — do not
> change the bind address to `0.0.0.0`.

---

## Security Notes

- **Rotate the Telegram bot token** if it was ever committed to git, shared in
  logs, or visible in screenshots. Revoke at https://t.me/BotFather and update
  `TELEGRAM_BOT_TOKEN` in `~/nexus-ai/.env`.
- Secrets live in `~/nexus-ai/.env` only — never in plist files or source code.
- The `.env` file is in `.gitignore` and should never be committed.

## Telegram Inbound Authority

- Canonical inbound command consumer: `telegram_bot.py --monitor`
- Launchd label: `com.raymonddavis.nexus.telegram`
- Canonical inbound token source: `TELEGRAM_INBOUND_BOT_TOKEN`
- Recommended token for local polling: the webhook-free Hermes bot token
- `NEXUS_ONE_BOT_TOKEN` should remain available for the existing NexusOne webhook/outbound path unless you intentionally migrate that bot off webhook delivery.

Safe defaults:
- `TELEGRAM_DELETE_WEBHOOK_ON_START=false`
- `TELEGRAM_ALLOW_MUTATING_COMMANDS=false`
- `HERMES_STATUS_POLLING_ENABLED=false`

Operator fallback:
- `python3 scripts/hermes_status.py`
- Control Center health and growth pages

---

## File Locations

```
~/nexus-ai/scripts/
├── start_nexus_stack.sh        — bootstrap helper (called by launchd)
├── stop_nexus_stack.sh         — graceful shutdown
├── check_nexus_stack.sh        — full status report
├── install_launchd_service.sh  — one-time install / reload all plists
└── restart_launchd_service.sh  — restart all Nexus services

~/nexus-ai/signal_review/launchd/
└── com.nexus.signal-review.plist          — signal review poller daemon template

~/Library/LaunchAgents/
├── com.nexus.signal-review.plist          — Signal review poller daemon
├── com.raymonddavis.nexus.plist            — one-shot bootstrap
├── com.raymonddavis.nexus.telegram.plist   — Canonical Telegram inbound monitor
└── com.raymonddavis.nexus.dashboard.plist  — Dashboard daemon

~/nexus-ai/openclaw/logs/
├── gateway.log
├── telegram.log / telegram.err.log
├── dashboard.log / dashboard.err.log
├── launchd.out.log
└── launchd.err.log
```

---

## Install the Service (First Time or After Plist Changes)

```bash
cd ~/nexus-ai
chmod +x scripts/*.sh
./scripts/install_launchd_service.sh
./scripts/check_nexus_stack.sh
```

---

## Stop the Stack

```bash
# Stop processes (KeepAlive will restart them — unload first to prevent that)
launchctl unload ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist
launchctl unload ~/Library/LaunchAgents/com.raymonddavis.nexus.dashboard.plist
launchctl unload ~/Library/LaunchAgents/com.nexus.signal-review.plist
launchctl unload ~/Library/LaunchAgents/com.raymonddavis.nexus.plist
~/nexus-ai/scripts/stop_nexus_stack.sh
```

---

## Restart All Services

```bash
~/nexus-ai/scripts/restart_launchd_service.sh
```

Or individually:
```bash
launchctl kickstart -k gui/$(id -u)/com.raymonddavis.nexus.telegram
launchctl kickstart -k gui/$(id -u)/com.raymonddavis.nexus.dashboard
launchctl kickstart -k gui/$(id -u)/com.nexus.signal-review
launchctl kickstart -k gui/$(id -u)/com.nexus.strategy-lab
```

---

## Inspect Logs

```bash
tail -f ~/nexus-ai/openclaw/logs/telegram.log
tail -f ~/nexus-ai/openclaw/logs/dashboard.log
tail -f ~/nexus-ai/openclaw/logs/signal-review.log
tail -f ~/nexus-ai/openclaw/logs/launchd.out.log

# Full status report
~/nexus-ai/scripts/check_nexus_stack.sh

# Safe local fallback for Hermes command status
python3 ~/nexus-ai/scripts/hermes_status.py

# Archive stale / oversized runtime logs
~/nexus-ai/scripts/prune_runtime_logs.sh
```

---

## Disable Autostart

```bash
launchctl unload ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist
launchctl unload ~/Library/LaunchAgents/com.raymonddavis.nexus.dashboard.plist
launchctl unload ~/Library/LaunchAgents/com.nexus.signal-review.plist
launchctl unload ~/Library/LaunchAgents/com.raymonddavis.nexus.plist

# Verify
launchctl list | grep nexus
```

To re-enable: `./scripts/install_launchd_service.sh`

---

## Trading Safety

> **Live trading is disabled.**
>
> `DRY_RUN = True` is hardcoded in `trading-engine/nexus_trading_engine.py`.
> The trading engine may still be loaded as a local service for webhook intake and
> manual/demo handling, but broker execution remains blocked while `DRY_RUN` stays true.
>
> Enable live trading only after:
> - Completing 24h+ of demo signal monitoring
> - Confirming Oanda credentials are correct
> - Explicitly setting `DRY_RUN = False` and re-validating the engine's launch/runtime path

---

## Strategy Lab Notes

- `com.nexus.strategy-lab` is a scheduled launchd job, not a persistent daemon.
- The current pipeline is schema-complete and runs end-to-end on this Supabase project.
- Hermes review now degrades gracefully:
  - local OpenClaw can be used first
  - OpenRouter can absorb review traffic when local capacity is tight
  - deterministic fallback reviews still persist if AI responses are temporarily unusable
- Short-lived rate limits should be treated as degraded capacity, not as a broken pipeline.

## Control Plane Self-Healing

- `com.nexus.ops-control-worker` now runs every 10 minutes with automatic recovery enabled.
- Safe recovery is limited to workers in the Supabase control plane that are:
  - `control_mode = automatic`
  - `desired_state = running`
  - not in maintenance mode
  - backed by a known `runtime_label`
- Current recovery actions are intentionally narrow:
  - queue `restart_service` if an automatic launchd-managed worker disappears from `launchctl`
  - queue `restart_service` if a persistent automatic worker's heartbeat goes stale
- Duplicate restart loops are throttled with a cooldown window, so the worker will not keep re-queueing the same restart every cycle.

## Queue Self-Healing

- `nexus-research-worker` now includes conservative stale-job recovery in `stale_state_sweep`.
- Recovery is limited to jobs stuck in `claimed` or `running` that are:
  - older than 2× the stale-job threshold
  - attached to a worker with a missing/stale heartbeat, or an expired lease
- Recovered jobs are moved back to `pending` with a short delay before reprocessing.
- This keeps the queue moving without aggressively resetting jobs that may still be active.
