# Next Local Milestones — Mac Mini
_Last updated: 2026-04-10_

> For the simplified working plan, see `docs/CURRENT_AGENDA.md`. This is the higher-signal now/next/later version of these milestones.

## Current State

| System | Status |
|--------|--------|
| OpenClaw gateway (port 18789) | Running |
| Telegram bot | Running |
| Signal router (port 8000) | Running |
| Dashboard (port 3000) | Running |
| Control Center (port 4000) | Running |
| Research pipeline (18 strategies in Supabase) | Complete |
| Operations center / scheduler | Running |

Supabase `tv_normalized_signals` table is being populated by the Oracle VM API.
This Mac Mini reads those signals and applies AI reasoning + risk rules.

---

## Milestone 1 — Signal Review → Risk Office → Telegram Risk Alerts
**This is the immediate next build.**

### What it does
1. **Signal Poller** — polls `tv_normalized_signals` in Supabase for new signals (status = `new`)
2. **Signal Reviewer** — sends each signal to OpenClaw for AI review:
   - Does this signal match any of our 18 research strategies?
   - Confidence assessment
   - Suggested action: approve / reject / hold
3. **Risk Office** — runs approved signals through `trading-engine/risk/risk_manager.py`:
   - Max daily loss check ($100)
   - Max positions check (3)
   - R:R ratio check (min 2:1)
   - Returns: approved / rejected with reason
4. **Telegram Risk Alert** — sends structured alert for every risk decision:
   - APPROVED signals: symbol, side, entry, SL, TP, R:R, confidence, AI reasoning
   - REJECTED signals: symbol + rejection reason
   - Updates signal status in Supabase (`reviewed` / `approved` / `rejected`)

### Files to create
```
~/nexus-ai/
├── signal_review/
│   ├── __init__.py
│   ├── signal_poller.py       — polls Supabase for new tv_normalized_signals
│   ├── signal_reviewer.py     — sends to OpenClaw for AI assessment
│   └── risk_gate.py           — applies risk_manager rules, sends Telegram alert
└── scripts/
    └── start_signal_review.sh — starts the poller loop
```

### Telegram alert format (approved)
```
🟢 SIGNAL APPROVED
EUR/USD | BUY | 15m
Entry: 1.1645 | SL: 1.1620 | TP: 1.1690
R:R: 1:1.8 | Confidence: 73%
Strategy match: London Breakout
AI review: Aligns with session momentum. SL below prior support.
Risk check: PASSED (daily P&L: -$12 / limit: -$100)
```

### Telegram alert format (rejected)
```
🔴 SIGNAL REJECTED
EUR/USD | BUY | 15m
Reason: R:R below minimum (1:1.2 < 1:2.0)
```

---

## Milestone 2 — Research Brain Auto-Scheduling
- Scheduler triggers research pipeline every 12h automatically
- New strategies written to Supabase and loaded by signal reviewer
- No manual `run_research.sh` needed

## Milestone 3 — Control Center Signal Feed
- Add live signal review feed to Control Center UI (port 4000)
- Show approved/rejected signals with AI reasoning in the Bloomberg terminal
- Confidence trend chart

## Milestone 4 — Risk Office Daily Report
- 9am and 4pm daily Telegram summary:
  - Signals reviewed today: N
  - Approved: N | Rejected: N
  - P&L exposure: $X / $100 limit
  - Top strategy matches from research

---

## What Stays on Windows / Oracle VM

- `nexus-oracle-api` repo — deploy + maintain from Windows
- Oracle VM nginx, PM2, Certbot — Windows only
- TradingView webhook URL configuration — Windows/Oracle only
