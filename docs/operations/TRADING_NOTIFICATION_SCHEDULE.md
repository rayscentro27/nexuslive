# Trading / Demo Notification Schedule

How Nexus reports demo trading without spamming TheChoseone Telegram.

## The spam incident (2026-06-18)
TheChoseone received ~5 demo-trade messages around **3:17 AM** and **9:16 PM**.

**Root cause:** the launchd job `com.nexus.demo-trading-loop` runs
`scripts/run_nexus_demo_trading_loop.py … --local-paper-max-reps 5` from the **diverged
`~/nexus-ai-worker` checkout**. That worker copy sends **one Telegram per paper trade**, so
5 reps = 5 messages. It fires when signals cluster (session opens ≈ 3:17 / 21:16). The
**main** repo's `nexus_trading_engine.py` notifier is already digest-first and does NOT do
this — only the worker path spammed.

## Fix
- The worker job `com.nexus.demo-trading-loop` was **unloaded + disabled**
  (`launchctl bootout` / `unload -w`). That stopped the bursts.
- `lib/telegram_send_guard.py` gained a `demo_trading_report` purpose:
  dedup 12h, **auto cap 1 per 6h**, burst max 1. A 5-trade run now yields **one** message.
- `nexus_trading_engine.py::TelegramNotifier._send` routes critical sends through that
  guard; `demo_summary()` sends ONE guarded summary instead of per-trade messages.
- `lib/run_lock.py` provides a scheduler lock so duplicate schedulers can't double-run.

## Intended scheduler (keep ONE)
- **Active job:** `com.nexus.demo-trading-loop` — currently **DISABLED** pending re-point.
- **Should run:** a guarded summary path (main repo), not the worker's per-trade sender.
- **Times:** at most twice daily is fine; never one-message-per-trade.
- **Guard:** `demo_trading_report` purpose (1 per 6h) + `run_lock` ("demo_trading_report").
- **Loss cap:** Oanda demo stops at $500 cumulative loss; SL/TP required; demo/practice only.

## How to disable / re-enable
```
launchctl bootout gui/$(id -u)/com.nexus.demo-trading-loop
launchctl unload -w ~/Library/LaunchAgents/com.nexus.demo-trading-loop.plist   # disable
launchctl load   -w ~/Library/LaunchAgents/com.nexus.demo-trading-loop.plist   # re-enable
```
Before re-enabling: point the job at a guarded summary script (or restore the executor
into main) so it uses `TelegramNotifier.demo_summary()` / the `demo_trading_report` guard.

## How to test safely
```
python3 scripts/run_nexus_operator_core.py --no-telegram     # status only, no send
# guard/lock unit behavior is covered by lib/telegram_send_guard.py + lib/run_lock.py
```

## Note
The worker launchd plists embed broker/Supabase secrets in EnvironmentVariables. Those are
on-machine only (not in the git repo) and must never be committed.
