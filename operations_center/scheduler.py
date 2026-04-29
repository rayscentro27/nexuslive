#!/usr/bin/env python3
"""
Nexus Operations Scheduler
Internal scheduling for all Nexus AI pipelines.
Uses threading — does NOT modify launchd.

Schedules:
  - Research ingestion (every 12h)
  - Strategy generation (after research)
  - Signal analysis (every 6h)
  - Lead intelligence check (every 30m)
  - Reputation monitoring (every 1h)
"""
import os
import sys
import json
import time
import signal
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SCHEDULER] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "scheduler.log"),
    ],
)
logger = logging.getLogger("Scheduler")

STATE_FILE = Path(__file__).parent / "scheduler_state.json"
PID_FILE = Path(__file__).parent / "scheduler.pid"
_running = True
_lock = threading.Lock()


def telegram_enabled() -> bool:
    return os.getenv("SCHEDULER_TELEGRAM_ENABLED", "true").lower() == "true"


def email_enabled() -> bool:
    return os.getenv("SCHEDULER_EMAIL_ENABLED", "false").lower() == "true"


def _acquire_pid_lock():
    """Prevent multiple scheduler instances. Exit if one is already running."""
    if PID_FILE.exists():
        try:
            existing_pid = int(PID_FILE.read_text().strip())
            # Check if that process is actually alive
            os.kill(existing_pid, 0)
            print(f"Scheduler already running (PID {existing_pid}). Exiting.")
            sys.exit(0)
        except (ProcessLookupError, ValueError):
            pass  # stale PID file — overwrite it
    PID_FILE.write_text(str(os.getpid()))


def _release_pid_lock():
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _load_state() -> Dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_state(state: Dict):
    with _lock:
        STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def _due(task_name: str, interval_hours: float) -> bool:
    state = _load_state()
    last_run = state.get(task_name)
    if not last_run:
        return True
    try:
        last = datetime.fromisoformat(last_run)
        return datetime.now() >= last + timedelta(hours=interval_hours)
    except Exception:
        return True


def _mark_done(task_name: str):
    state = _load_state()
    state[task_name] = datetime.now().isoformat()
    state.pop(f"_running_{task_name}", None)
    _save_state(state)


def _claim_due(task_name: str, interval_hours: float) -> bool:
    """
    Atomically claim a due task so slow jobs do not start twice in parallel.
    """
    with _lock:
        state = _load_state()
        running_key = f"_running_{task_name}"
        if state.get(running_key):
            return False

        last_run = state.get(task_name)
        if last_run:
            try:
                last = datetime.fromisoformat(last_run)
                if datetime.now() < last + timedelta(hours=interval_hours):
                    return False
            except Exception:
                pass

        state[running_key] = datetime.now().isoformat()
        _save_state(state)
        return True


def _release_claim(task_name: str):
    state = _load_state()
    if state.pop(f"_running_{task_name}", None) is not None:
        _save_state(state)


# ─────────────────────────────────────────────
# Task definitions
# ─────────────────────────────────────────────

def task_research_pipeline():
    """Run full research pipeline (collect→summarize→extract→store)."""
    logger.info("▶ Running research pipeline...")
    try:
        from research.ai_research_brain import run_pipeline, get_latest_strategies
        report = run_pipeline(collect=True)
        strategies = report.get("steps", {}).get("extract", {}).get("strategy_count", 0)
        logger.info(f"✅ Research pipeline done — {strategies} strategies")
        if strategies == 0:
            logger.info("No new strategies found — skipping email/Telegram notification")
            return
        _notify_dual(
            brief=(
                "🧠 <b>Research Pipeline Complete</b>\n"
                f"Strategies extracted: {strategies}"
            ),
            email_subject=f"Nexus Research Pipeline Complete — {strategies} strategies",
            email_body=(
                "Nexus Research Pipeline Complete\n\n"
                f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Strategies extracted: {strategies}\n\n"
                "This is the full operator summary for the latest research cycle.\n"
                "Telegram is intentionally receiving a shorter update to reduce noise and token churn."
            ),
        )
        # Push research digest into Hermes memory so it can answer strategy questions
        top = get_latest_strategies(n=5)
        titles = "\n".join(f"- {s['title']}" for s in top) if top else "None available"
        _notify_hermes(
            f"Research pipeline completed at {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
            f"Total strategies in library: {strategies}.\n\n"
            f"Top 5 most recently updated strategies:\n{titles}\n\n"
            "Please remember this research digest. When asked about 'latest strategies', "
            "'what did research find', 'research results', or 'trading strategies', refer to this summary."
        )
    except Exception as e:
        logger.error(f"Research pipeline failed: {e}")


def task_signal_analysis():
    """Generate signal candidates from latest strategies."""
    logger.info("▶ Running signal analysis...")
    try:
        from operations_center.hedge_fund_panel import generate_signals, get_market_sentiment_summary
        sigs = generate_signals(limit=5)
        sentiment = get_market_sentiment_summary()
        logger.info(f"✅ Signal analysis done — {len(sigs)} candidates, sentiment: {sentiment.get('dominant','?')}")
        if sigs:
            top = sigs[0]
            _notify_dual(
                brief=(
                    "📊 <b>Signal Analysis</b>\n"
                    f"Market: {sentiment.get('dominant','?').upper()} "
                    f"(Bull {sentiment.get('bullish_pct',0)}% / Bear {sentiment.get('bearish_pct',0)}%)\n"
                    f"Candidates: {len(sigs)} | DRY RUN ✅"
                ),
                email_subject=f"Nexus Signal Analysis — {len(sigs)} candidates",
                email_body=(
                    "Nexus Signal Analysis Complete\n\n"
                    f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Market sentiment: {sentiment.get('dominant','?')}\n"
                    f"Bullish: {sentiment.get('bullish_pct',0)}%\n"
                    f"Bearish: {sentiment.get('bearish_pct',0)}%\n"
                    f"Candidate count: {len(sigs)}\n\n"
                    f"Top candidate:\n{json.dumps(top, indent=2, default=str)}"
                ),
            )
            top_ticker = top.get('ticker', top.get('symbol', '?'))
            top_direction = top.get('direction', top.get('signal', '?'))
            _notify_hermes(
                f"Signal analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
                f"Market sentiment: {sentiment.get('dominant','?').upper()} "
                f"(Bull {sentiment.get('bullish_pct',0)}% / Bear {sentiment.get('bearish_pct',0)}%). "
                f"Total signal candidates: {len(sigs)}. "
                f"Top candidate: {top_ticker} — {top_direction}. "
                "Remember this for questions about 'signals', 'market sentiment', or 'trade candidates'."
            )
        else:
            _notify_hermes(
                f"Signal analysis completed at {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
                f"No signal candidates found. "
                f"Market sentiment: {sentiment.get('dominant','?').upper()} "
                f"(Bull {sentiment.get('bullish_pct',0)}% / Bear {sentiment.get('bearish_pct',0)}%)."
            )
    except Exception as e:
        logger.error(f"Signal analysis failed: {e}")


def task_lead_check():
    """Daily lead summary — syncs live signups then sends one digest email."""
    logger.info("▶ Running daily lead summary...")
    try:
        # Pull real signups from nexuslive Supabase
        try:
            from lead_intelligence.supabase_lead_sync import sync_new_signups
            new = sync_new_signups(hours_back=24)
            logger.info(f"Synced {len(new)} new signups from nexuslive")
        except Exception as e:
            logger.warning(f"Supabase sync skipped: {e}")

        from lead_intelligence.lead_scoring_engine import get_lead_summary
        summary = get_lead_summary()
        high = summary.get("high_value", 0)
        total = summary.get("total", 0)
        recent = summary.get("recent_high_value", [])

        # Build lead rows for the digest
        lead_rows = ""
        for lead in recent[-10:]:  # cap at 10 leads in digest
            lead_rows += (
                f"  • {lead.get('name','?')} — Score: {lead.get('score','?')}/100"
                f" | Source: {lead.get('source','?')}"
                f" | Interest: {lead.get('interest','?')}\n"
            )

        body = (
            f"Nexus Daily Lead Summary — {datetime.now().strftime('%Y-%m-%d')}\n"
            f"{'='*50}\n\n"
            f"Total leads tracked:  {total}\n"
            f"High-value leads:     {high}\n\n"
        )
        if lead_rows:
            body += f"Top high-value leads (last 10):\n{lead_rows}"
        else:
            body += "No high-value leads detected today.\n"

        _notify_dual(
            brief=(
                f"📋 <b>Daily Lead Summary</b>\n"
                f"Total: {total} | High-value: {high}\n"
                + (f"Top: {recent[-1].get('name','?')} ({recent[-1].get('score','?')}/100)" if recent else "No high-value leads today.")
            ),
            email_subject=f"Nexus Daily Lead Summary — {high} high-value leads",
            email_body=body,
        )
        logger.info(f"✅ Daily lead summary sent — {total} total, {high} high-value")
        top_lead = recent[-1] if recent else None
        _notify_hermes(
            f"Lead check completed at {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
            f"Total leads tracked: {total}. High-value leads: {high}. "
            + (
                f"Most recent high-value lead: {top_lead.get('name','?')} "
                f"(score {top_lead.get('score','?')}/100, source: {top_lead.get('source','?')}, "
                f"interest: {top_lead.get('interest','?')})."
                if top_lead else "No high-value leads detected."
            )
            + " Remember this for questions about 'leads', 'signups', or 'new customers'."
        )
    except Exception as e:
        logger.error(f"Lead check failed: {e}")


def task_reputation_check():
    """Check for new negative reviews and alert."""
    logger.info("▶ Checking reputation...")
    try:
        from reputation_engine.review_analyzer import get_flagged_reviews
        flagged = get_flagged_reviews()
        if flagged:
            latest = flagged[-1]
            _notify_dual(
                brief=(
                    "⚠️ <b>Negative Review Alert</b>\n"
                    f"Source: {latest.get('source','?')}\n"
                    f"By: {latest.get('reviewer_name','?')}\n"
                    f"Preview: {latest.get('text','')[:120]}..."
                ),
                email_subject=f"Nexus Negative Review Alert — {latest.get('source','?')}",
                email_body=(
                    "Nexus Reputation Alert\n\n"
                    f"Detected: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Flagged review count: {len(flagged)}\n\n"
                    "Latest flagged review:\n"
                    f"{json.dumps(latest, indent=2, default=str)}"
                ),
            )
        logger.info(f"✅ Reputation check done — {len(flagged)} flagged reviews")
        if flagged:
            _notify_hermes(
                f"Reputation check at {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
                f"WARNING: {len(flagged)} negative review(s) flagged. "
                f"Latest from {latest.get('source','?')} by {latest.get('reviewer_name','?')}: "
                f"\"{latest.get('text','')[:200]}\". "
                "Remember this for questions about 'reviews', 'reputation', or 'negative feedback'."
            )
        else:
            _notify_hermes(
                f"Reputation check at {datetime.now().strftime('%Y-%m-%d %H:%M')}. "
                "No negative reviews flagged. All clear."
            )
    except Exception as e:
        logger.error(f"Reputation check failed: {e}")


def task_token_check():
    """Sync OpenRouter spend, check budgets, send daily usage summary."""
    logger.info("▶ Running token/budget check...")
    try:
        from monitoring.ai_usage_tracker import run_token_check
        run_token_check()
        logger.info("✅ Token check done")
    except Exception as e:
        logger.error(f"Token check failed: {e}")


def task_browser_health():
    """Run browser health checks: supabase, stripe, nexuslive."""
    logger.info("▶ Running browser health checks...")
    import subprocess
    worker = Path(__file__).parent.parent / "browser_worker" / "worker.py"
    python = Path(__file__).parent.parent / "research-env" / "bin" / "python3"
    for check in ("supabase_check", "stripe_check", "nexuslive_check"):
        try:
            result = subprocess.run(
                [str(python), str(worker), "--once", check],
                capture_output=True, text=True, timeout=90,
                cwd=str(worker.parent.parent),
            )
            if result.returncode == 0:
                logger.info(f"✅ browser {check} done")
            else:
                logger.error(f"browser {check} failed: {result.stderr[:200]}")
        except Exception as e:
            logger.error(f"browser {check} error: {e}")


def task_ops_monitoring():
    """Run OpsMonitoringWorker — daily system health report to Telegram."""
    logger.info("▶ Running ops monitoring worker...")
    import subprocess
    worker_path = Path(__file__).parent.parent / "workflows" / "ai_workforce" / "ops_monitoring_worker" / "ops_monitoring_worker.js"
    try:
        result = subprocess.run(
            ["node", str(worker_path), "--summary"],
            capture_output=True, text=True, timeout=60,
            cwd=str(worker_path.parent),
        )
        if result.returncode == 0:
            logger.info("✅ Ops monitoring done")
        else:
            logger.error(f"Ops monitoring failed: {result.stderr[:200]}")
    except Exception as e:
        logger.error(f"Ops monitoring error: {e}")


def task_funding_brief():
    """Produce a daily Hermes funding brief for a configured user."""
    logger.info("▶ Running funding brief...")
    user_id = (os.getenv("FUNDING_BRIEF_USER_ID") or "").strip()
    tenant_id = (os.getenv("FUNDING_BRIEF_TENANT_ID") or "").strip() or None
    if not user_id:
        logger.info("Funding brief skipped — FUNDING_BRIEF_USER_ID not configured")
        return
    try:
        from funding_engine.service import build_hermes_funding_brief

        brief = build_hermes_funding_brief(user_id=user_id, tenant_id=tenant_id)
        brief_text = brief.get("brief_text", "").strip()
        if not brief_text:
            logger.info("Funding brief skipped — no brief text generated")
            return
        _notify(
            "💼 <b>Daily Funding Brief</b>\n"
            + brief_text.replace("\n\n", "\n")
        )
        _notify_hermes(
            f"Daily funding brief for user {user_id} at {datetime.now().strftime('%Y-%m-%d %H:%M')}:\n\n"
            f"{brief_text}"
        )
        logger.info("✅ Funding brief generated")
    except Exception as e:
        logger.error(f"Funding brief failed: {e}")


def task_funding_recommendation_refresh():
    """Daily refresh for users who have usable funding profile data."""
    logger.info("▶ Running funding recommendation refresh...")
    try:
        from funding_engine.service import (
            create_or_refresh_user_recommendations,
            get_users_needing_recommendations,
            get_users_with_stale_recommendations,
            process_pending_recommendation_jobs,
        )

        processed_jobs = process_pending_recommendation_jobs(limit=50)
        # Skip users already handled by the job queue in this same run.
        already_processed: set = processed_jobs.get("processed_pairs") or set()

        candidate_map: dict[tuple[str | None, str], dict[str, Any]] = {}
        for row in get_users_needing_recommendations():
            key = (row.get("tenant_id"), row.get("user_id"))
            candidate_map[key] = row
        for row in get_users_with_stale_recommendations():
            key = (row.get("tenant_id"), row.get("user_id"))
            candidate_map[key] = {
                "tenant_id": row.get("tenant_id"),
                "user_id": row.get("user_id"),
                "reason": "stale_recommendations_refresh",
            }

        refreshed = 0
        skipped = 0
        for row in list(candidate_map.values())[:100]:
            pair = (row.get("tenant_id"), row.get("user_id"))
            if pair in already_processed:
                skipped += 1
                continue
            result = create_or_refresh_user_recommendations(
                user_id=row["user_id"],
                tenant_id=row.get("tenant_id"),
                reason=row.get("reason") or "scheduled_daily_refresh",
                force=False,
            )
            if result.get("refresh", {}).get("skipped"):
                skipped += 1
            else:
                refreshed += 1

        logger.info(
            "✅ Funding recommendation refresh done — refreshed=%s skipped=%s queued_processed=%s queued_failed=%s",
            refreshed,
            skipped,
            processed_jobs.get("processed", 0),
            processed_jobs.get("failed", 0),
        )
    except Exception as e:
        logger.error(f"Funding recommendation refresh failed: {e}")


def _notify(message: str):
    """Send a Telegram alert without crashing if bot is unavailable."""
    if not telegram_enabled():
        return
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from telegram_bot import NexusTelegramBot
        bot = NexusTelegramBot()
        if bot.connected:
            bot.send_message(message)
    except Exception as e:
        logger.warning(f"Telegram notify failed: {e}")


_EMAIL_COOLDOWN_HOURS = 2.0  # minimum gap between emails with the same subject prefix

def _email_notify(subject: str, body: str):
    """Send a fuller operator summary by email without crashing the scheduler."""
    if not email_enabled():
        return
    try:
        state = _load_state()
        cooldown_key = f"_email_sent_{subject[:40]}"
        last_sent = state.get(cooldown_key)
        if last_sent:
            try:
                elapsed = (datetime.now() - datetime.fromisoformat(last_sent)).total_seconds() / 3600
                if elapsed < _EMAIL_COOLDOWN_HOURS:
                    logger.info(f"📧 Email cooldown active ({elapsed:.1f}h < {_EMAIL_COOLDOWN_HOURS}h) — skipping: {subject}")
                    return
            except Exception:
                pass

        from notifications.operator_notifications import send_operator_email
        sent, detail = send_operator_email(subject, body)
        if sent:
            logger.info(f"📧 Email summary sent: {subject}")
            state[cooldown_key] = datetime.now().isoformat()
            _save_state(state)
        else:
            logger.warning(f"Email notify skipped/failed: {detail}")
    except Exception as e:
        logger.warning(f"Email notify failed: {e}")


def _notify_dual(brief: str, email_subject: str, email_body: str):
    """Short bot update + full email summary."""
    _notify(brief)
    _email_notify(email_subject, email_body)


def _notify_hermes(content: str):
    """Write a memory entry directly into Hermes's MEMORY.md (instant, no inference round-trip)."""
    memory_file = Path.home() / ".hermes" / "memories" / "MEMORY.md"
    if not memory_file.exists():
        logger.debug("Hermes MEMORY.md not found — skipping memory update")
        return
    try:
        existing = memory_file.read_text(encoding="utf-8")
        entry = content.strip()
        # Append new entry with § separator (Hermes memory format)
        updated = existing.rstrip() + f"\n§\n{entry}\n"
        memory_file.write_text(updated, encoding="utf-8")
        logger.info(f"🧠 Hermes memory updated ({len(entry)} chars)")
    except Exception as e:
        logger.warning(f"Hermes memory write failed: {e}")


# ─────────────────────────────────────────────
# Schedule table: (task_fn, interval_hours, name)
# ─────────────────────────────────────────────

SCHEDULE = [
    (task_research_pipeline, 12.0,  "research_pipeline"),
    (task_signal_analysis,    6.0,  "signal_analysis"),
    (task_lead_check,        24.0,  "lead_check"),
    (task_reputation_check,   1.0,  "reputation_check"),
    (task_funding_brief,     24.0,  "funding_brief"),
    (task_funding_recommendation_refresh, 24.0, "funding_recommendation_refresh"),
    (task_ops_monitoring,    24.0,  "ops_monitoring"),
    (task_token_check,       24.0,  "token_check"),
    (task_browser_health,    12.0,  "browser_health"),
]

TICK_INTERVAL = 60  # check every minute


def get_schedule_status() -> Dict:
    state = _load_state()
    result = {}
    for fn, hours, name in SCHEDULE:
        last = state.get(name)
        running = bool(state.get(f"_running_{name}"))
        if last:
            try:
                next_run = (datetime.fromisoformat(last) + timedelta(hours=hours)).isoformat()
            except Exception:
                next_run = "unknown"
        else:
            next_run = "now (never run)"
        result[name] = {
            "last_run": last,
            "interval_hours": hours,
            "next_run": next_run,
            "running": running,
        }
    return result


def run_scheduler():
    global _running

    _acquire_pid_lock()

    def _shutdown(sig, frame):
        global _running
        logger.info("Scheduler shutdown signal received.")
        _running = False
        _release_pid_lock()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("🚀 Nexus Scheduler started (PID %s)", os.getpid())
    logger.info("Schedule:")
    for fn, hours, name in SCHEDULE:
        logger.info(f"  {name}: every {hours}h")

    while _running:
        for fn, interval_hours, name in SCHEDULE:
            if not _running:
                break
            if _claim_due(name, interval_hours):
                t = threading.Thread(target=_run_task, args=(fn, name), daemon=True)
                t.start()

        for _ in range(TICK_INTERVAL):
            if not _running:
                break
            time.sleep(1)

    logger.info("Scheduler stopped.")
    _release_pid_lock()


def _run_task(fn: Callable, name: str):
    try:
        fn()
        _mark_done(name)
    except Exception as e:
        _release_claim(name)
        logger.error(f"Task {name} raised: {e}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--status", action="store_true")
    p.add_argument("--run-now", metavar="TASK",
                   choices=["research", "signals", "leads", "reputation", "funding_brief", "funding_recommendation_refresh"],
                   help="Run a specific task immediately")
    args = p.parse_args()

    if args.status:
        print(json.dumps(get_schedule_status(), indent=2, default=str))
    elif args.run_now:
        task_map = {
            "research": task_research_pipeline,
            "signals": task_signal_analysis,
            "leads": task_lead_check,
            "reputation": task_reputation_check,
            "funding_brief": task_funding_brief,
            "funding_recommendation_refresh": task_funding_recommendation_refresh,
        }
        task_map[args.run_now]()
    else:
        run_scheduler()
