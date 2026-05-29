# Daily Opportunity Scheduler Plan

**STATUS: NOT ENABLED — Ray must approve before activating.**

This document describes the planned schedule for the Daily Opportunity Intake cycle.
No schedule is active. All runs are manual.

---

## Suggested Schedule (pending Ray approval)

| Time | Run | Mode | Sources |
|---|---|---|---|
| 6:00 AM | Morning scan | `--mode daily --max-sources 50` | YouTube, GitHub, keywords |
| 1:00 PM | Afternoon refresh | `--mode keyword-only --max-sources 20` | Google/web, affiliate |
| 7:00 PM | Evening digest | `--mode monetization-only --max-sources 15` | Scoring + digest |

---

## How to Enable (after Ray approves)

### Option A: launchd (macOS, persistent after reboot)

Create `~/Library/LaunchAgents/com.nexus.daily-intake.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" ...>
<plist version="1.0">
<dict>
  <key>Label</key><string>com.nexus.daily-intake</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/python3</string>
    <string>/Users/raymonddavis/nexus-ai/scripts/run_daily_opportunity_intake.py</string>
    <string>--mode</string><string>daily</string>
    <string>--max-sources</string><string>50</string>
    <string>--no-dry-run</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/Users/raymonddavis/nexus-ai/logs/daily-intake.log</string>
  <key>StandardErrorPath</key><string>/Users/raymonddavis/nexus-ai/logs/daily-intake.err.log</string>
</dict>
</plist>
```

Load: `launchctl load ~/Library/LaunchAgents/com.nexus.daily-intake.plist`
Unload: `launchctl unload ~/Library/LaunchAgents/com.nexus.daily-intake.plist`

### Option B: cron

```cron
# Morning scan (6 AM)
0 6 * * * cd /Users/raymonddavis/nexus-ai && python3 scripts/run_daily_opportunity_intake.py --mode daily --max-sources 50 --no-dry-run >> logs/daily-intake.log 2>&1

# Afternoon refresh (1 PM)
0 13 * * * cd /Users/raymonddavis/nexus-ai && python3 scripts/run_daily_opportunity_intake.py --mode keyword-only --max-sources 20 --no-dry-run >> logs/daily-intake.log 2>&1

# Evening digest (7 PM)
0 19 * * * cd /Users/raymonddavis/nexus-ai && python3 scripts/run_monetization_decision_cycle.py --mode daily --top-n 10 --no-dry-run >> logs/daily-intake.log 2>&1
```

---

## How to Disable

```bash
launchctl unload ~/Library/LaunchAgents/com.nexus.daily-intake.plist
```
Or remove the crontab entry.

---

## Logs and Artifacts

- Logs: `logs/daily-intake.log`, `logs/daily-intake.err.log`
- Intake reports: `docs/reports/intake/`
- Decision reports: `docs/reports/monetization/`
- Review artifacts: `docs/reports/review/`
- Action queue: `docs/reports/actions/hermes_action_queue.jsonl`
- Decision log: `docs/reports/decisions/hermes_decision_log.jsonl`

---

## Before Enabling the Schedule

Ray should verify:
1. Validation run produces useful results: `python3 scripts/run_daily_opportunity_intake.py --mode validation`
2. Telegram digest is concise and useful (not spam)
3. Scout dispatch is routing to correct scouts
4. Approval boundaries are correct
5. Anti-spam policy is working (check `lib/hermes_notification_policy.py`)

**Tell Hermes:** "Hermes, enable daily intake schedule" — and Hermes will create an
approval action for Ray to confirm before activating.

---

## Safety Checklist

- [ ] `NEXUS_DRY_RUN=true` globally enforced
- [ ] `HERMES_TELEGRAM_NOTIFY_ON_EACH_SOURCE=false`
- [ ] `HERMES_TELEGRAM_NOTIFY_ON_REJECTED_SOURCE=false`
- [ ] `HERMES_TELEGRAM_NOTIFY_ON_SCOUT_ASSIGNMENT=false`
- [ ] `HERMES_TELEGRAM_NOTIFY_ON_ARTIFACT_CREATED=false`
- [ ] `HERMES_TELEGRAM_NOTIFY_ON_APPROVAL_REQUIRED=true`
- [ ] `HERMES_TELEGRAM_NOTIFY_ON_BLOCKER=true`
- [ ] No paid APIs used without approval
- [ ] No live trading enabled
- [ ] No public publishing enabled
