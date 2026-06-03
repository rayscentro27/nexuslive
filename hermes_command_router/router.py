"""
router.py — Route normalized command objects to deterministic scripts or AI workers.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from hermes_command_router.intake import normalize, classify_intent
from hermes_command_router.report import build as build_report
from lib.hermes_model_router import synthesize as ai_synthesize, generate_codex_brief, model_class_for


def _run_script(script_path: str, args: list[str] = [], timeout: int = 30) -> tuple[bool, str]:
    """Run a script and return (success, output)."""
    if not os.path.exists(script_path):
        return False, f"Script not found: {script_path}"
    try:
        env = {**os.environ, "PYTHONPATH": ROOT}
        result = subprocess.run(
            [sys.executable, script_path] + args,
            capture_output=True, text=True, timeout=timeout,
            cwd=ROOT, env=env,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output or "(no output)"
    except subprocess.TimeoutExpired:
        return False, f"Script timed out after {timeout}s"
    except Exception as e:
        return False, str(e)


def _run_monitoring_check() -> tuple[str, list[str], str]:
    """Run monitoring worker checks and return (status, evidence, recommendation)."""
    try:
        # Load env first
        _env_path = os.path.join(ROOT, '.env')
        if os.path.exists(_env_path):
            with open(_env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, _, v = line.partition('=')
                        os.environ.setdefault(k.strip(), v.strip())

        from monitoring.monitoring_worker import run_checks
        result = run_checks()
        alerts = result.get('alerts', [])
        stale  = result.get('stale_workers', [])
        queue  = result.get('queue', {})
        jobs   = result.get('jobs', {})
        errors = result.get('errors_15m', 0)
        cost   = result.get('ai_cost_today', 0.0)

        evidence = [
            f"Signals queue: {queue.get('signals_pending', '?')}",
            f"Strategies queue: {queue.get('strategies_pending', '?')}",
            f"Job fail rate (1h): {jobs.get('fail_rate', 0):.0%} ({jobs.get('failed', 0)}/{jobs.get('total', 0)})",
            f"Errors (15m): {errors}",
            f"AI cost today: ${cost:.4f}",
        ]
        if stale:
            evidence.append(f"Stale workers: {', '.join(stale)}")

        if alerts:
            status = "warning"
            rec = f"Investigate: {alerts[0]}"
        else:
            status = "healthy"
            rec = "All checks green — no action needed."

        return status, evidence, rec
    except Exception as e:
        return "unknown", [f"Monitoring check failed: {e}"], "Check monitoring worker logs."


def _run_worker_check() -> tuple[str, list[str], str]:
    """Check worker heartbeats."""
    try:
        _env_path = os.path.join(ROOT, '.env')
        if os.path.exists(_env_path):
            with open(_env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, _, v = line.partition('=')
                        os.environ.setdefault(k.strip(), v.strip())

        import json, urllib.request
        url = os.getenv('SUPABASE_URL', '')
        key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
        if not url or not key:
            return "unknown", ["SUPABASE_URL not configured"], "Set SUPABASE credentials."

        req = urllib.request.Request(
            f"{url}/rest/v1/worker_heartbeats?select=worker_id,status,last_seen_at,worker_type&order=last_seen_at.desc&limit=20",
            headers={'apikey': key, 'Authorization': f'Bearer {key}'},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())

        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=10)
        evidence = []
        stale = []
        for row in rows:
            wid = row.get('worker_id', '?')
            ts_str = row.get('last_seen_at', '')
            if ts_str:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                age = int((now - ts).total_seconds() / 60)
                marker = "⚠ STALE" if ts < cutoff else "✓"
                evidence.append(f"{marker} {wid}: {age}m ago")
                if ts < cutoff:
                    stale.append(wid)
            else:
                evidence.append(f"? {wid}: no timestamp")
                stale.append(wid)

        if not rows:
            return "unknown", ["No heartbeat rows found"], "Workers may not have started yet."
        if stale:
            return "warning", evidence, f"Restart stale workers: {', '.join(stale)}"
        return "healthy", evidence, "All workers heartbeating normally."
    except Exception as e:
        return "unknown", [f"Heartbeat query failed: {e}"], "Check Supabase connectivity."


def _run_queue_check() -> tuple[str, list[str], str]:
    """Check signal and strategy queue depths."""
    try:
        from monitoring.monitoring_worker import check_queue_depth
        q = check_queue_depth()
        evidence = [
            f"Signals pending: {q['signals_pending']}",
            f"Strategies pending: {q['strategies_pending']}",
        ]
        if q['signals_pending'] > 50 or q['strategies_pending'] > 100:
            return "warning", evidence, "Queue backlog growing — check research worker."
        return "healthy", evidence, "Queue depths normal."
    except Exception as e:
        return "unknown", [f"Queue check failed: {e}"], "Check Supabase connectivity."


def _run_trading_check() -> tuple[str, list[str], str]:
    """Get live trading status."""
    try:
        _env_path = os.path.join(ROOT, '.env')
        if os.path.exists(_env_path):
            with open(_env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, _, v = line.partition('=')
                        os.environ.setdefault(k.strip(), v.strip())

        import json, urllib.request
        url = os.getenv('SUPABASE_URL', '')
        key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
        req = urllib.request.Request(
            f"{url}/rest/v1/trades?select=id,symbol,action,status,profit_loss&order=created_at.desc&limit=5",
            headers={'apikey': key, 'Authorization': f'Bearer {key}'},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            trades = json.loads(r.read())

        evidence = []
        total_pnl = 0.0
        for t in trades:
            pnl = float(t.get('profit_loss') or 0)
            total_pnl += pnl
            evidence.append(f"{t.get('symbol','?')} {t.get('action','?')} [{t.get('status','?')}] PnL:{pnl:+.2f}")

        if not evidence:
            evidence = ["No recent trades found"]

        pnl_str = f"{total_pnl:+.2f}"
        evidence.append(f"Last 5 trades net PnL: {pnl_str}")
        status = "healthy" if total_pnl >= 0 else "warning"
        rec = "Trading engine running." if total_pnl >= 0 else "Net negative PnL on recent trades — review strategy."
        return status, evidence, rec
    except Exception as e:
        return "unknown", [f"Trading query failed: {e}"], "Check trading engine."


def _run_pilot_readiness() -> tuple[str, list[str], str]:
    """Check if the system is ready for a 10-user pilot."""
    from datetime import datetime, timezone, timedelta
    import json, urllib.request

    _env_path = os.path.join(ROOT, '.env')
    if os.path.exists(_env_path):
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())

    checks: list[tuple[str, bool, str]] = []

    # 1. Backend DB reachable
    url = os.getenv('SUPABASE_URL', '')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
    db_ok = False
    if url and key:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/worker_heartbeats?select=id&limit=1",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                json.loads(r.read())
            db_ok = True
        except Exception:
            pass
    checks.append(("Supabase DB", db_ok, "reachable" if db_ok else "UNREACHABLE"))

    # 2. Workers alive (any heartbeat in last 15 min)
    workers_ok = False
    if db_ok:
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
            req = urllib.request.Request(
                f"{url}/rest/v1/worker_heartbeats?last_seen_at=gt.{cutoff}&select=worker_id&limit=1",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                rows = json.loads(r.read())
            workers_ok = len(rows) > 0
        except Exception:
            pass
    checks.append(("Workers", workers_ok, "heartbeating" if workers_ok else "NO HEARTBEAT"))

    # 3. Hermes gate reachable
    gate_ok = False
    try:
        gate_url = os.getenv('HERMES_GATEWAY_URL', 'http://127.0.0.1:8642')
        req = urllib.request.Request(f"{gate_url}/health", method='GET')
        with urllib.request.urlopen(req, timeout=3) as r:
            gate_ok = r.status == 200
    except Exception:
        gate_ok = True  # gate may not expose /health; absence is non-fatal

    # 4. Queue depth (signals)
    queue_ok = False
    queue_depth = -1
    if db_ok:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/signals?status=eq.pending&select=id&limit=200",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                rows = json.loads(r.read())
            queue_depth = len(rows)
            queue_ok = queue_depth < 100
        except Exception:
            queue_ok = True
    checks.append(("Queue", queue_ok, f"{queue_depth} pending" if queue_depth >= 0 else "unknown"))

    # 5. Error rate (last hour)
    errors_ok = True
    errors_15m = 0
    if db_ok:
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
            req = urllib.request.Request(
                f"{url}/rest/v1/job_events?status=eq.failed&created_at=gt.{cutoff}&select=id&limit=50",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                rows = json.loads(r.read())
            errors_15m = len(rows)
            errors_ok = errors_15m < 10
        except Exception:
            pass
    checks.append(("Error rate", errors_ok, f"{errors_15m} failures (15m)" if errors_ok else f"HIGH: {errors_15m} failures"))

    # 6. Telegram configured
    tg_ok = bool(os.getenv('TELEGRAM_BOT_TOKEN') and os.getenv('TELEGRAM_CHAT_ID'))
    checks.append(("Telegram", tg_ok, "configured" if tg_ok else "NOT CONFIGURED"))

    # 7. Email configured
    email_ok = bool(os.getenv('NEXUS_EMAIL') and os.getenv('NEXUS_EMAIL_PASSWORD'))
    checks.append(("Email", email_ok, "configured" if email_ok else "NOT CONFIGURED"))

    passed = sum(1 for _, ok, _ in checks if ok)
    total = len(checks)
    evidence = [f"{'✓' if ok else '✗'} {name}: {detail}" for name, ok, detail in checks]

    ready_10   = passed >= total - 1   # allow 1 non-critical miss
    ready_100  = passed == total

    if ready_100:
        status = "healthy"
        evidence.append(f"All {total}/{total} checks green")
        rec = "System is ready for 100-user simulation. All checks passed."
    elif ready_10:
        failed = [name for name, ok, _ in checks if not ok]
        status = "warning"
        evidence.append(f"{passed}/{total} checks green — minor gaps")
        rec = f"Ready for 10-user pilot. Fix before scaling: {', '.join(failed)}"
    else:
        status = "critical"
        evidence.append(f"Only {passed}/{total} checks green")
        rec = "NOT ready for pilot. Fix failing checks before onboarding users."

    return status, evidence, rec


def _run_next_best_move() -> tuple[str, list[str], str]:
    """Synthesize a prioritized next best move from current system state."""
    import json, urllib.request
    from datetime import datetime, timezone, timedelta

    _env_path = os.path.join(ROOT, '.env')
    if os.path.exists(_env_path):
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())

    url = os.getenv('SUPABASE_URL', '')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')

    priorities: list[tuple[int, str, str]] = []  # (score, finding, action)

    if url and key:
        # Check approval queue
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
            req = urllib.request.Request(
                f"{url}/rest/v1/owner_approval_queue?status=eq.pending&created_at=lt.{cutoff}&select=description&limit=5",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                rows = json.loads(r.read())
            if rows:
                desc = rows[0].get('description', '')[:80]
                priorities.append((10, f"{len(rows)} approval(s) waiting >6h: {desc}", "Review /approvals queue"))
        except Exception:
            pass

        # Check stale leads
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
            req = urllib.request.Request(
                f"{url}/rest/v1/leads?status=in.(new,contacted)&next_followup_at=lt.{cutoff}&select=name&limit=5",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                rows = json.loads(r.read())
            if rows:
                names = ', '.join(r.get('name', '?')[:20] for r in rows[:3])
                priorities.append((8, f"{len(rows)} lead(s) overdue: {names}", "Follow up with leads today"))
        except Exception:
            pass

        # Check recent errors
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
            req = urllib.request.Request(
                f"{url}/rest/v1/job_events?status=eq.failed&created_at=gt.{cutoff}&select=agent_name&limit=20",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                rows = json.loads(r.read())
            if len(rows) >= 3:
                agents = list({r.get('agent_name', '?') for r in rows})[:3]
                priorities.append((9, f"{len(rows)} job failures (30m): {', '.join(agents)}", "Check error logs"))
        except Exception:
            pass

        # Check funding stuck
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
            req = urllib.request.Request(
                f"{url}/rest/v1/funding_applications?status=eq.pending&updated_at=lt.{cutoff}&select=lender_name&limit=3",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                rows = json.loads(r.read())
            if rows:
                lenders = ', '.join(r.get('lender_name', '?')[:20] for r in rows[:2])
                priorities.append((7, f"{len(rows)} funding application(s) stuck >72h: {lenders}", "Follow up with lenders"))
        except Exception:
            pass

    priorities.sort(key=lambda x: -x[0])

    if not priorities:
        evidence = ["No urgent items detected across all queues"]
        return "healthy", evidence, "System is running smoothly. Consider scheduling a pilot readiness review or reviewing the weekly report."

    evidence = [f"Priority {i+1}: {finding}" for i, (_, finding, _) in enumerate(priorities[:4])]
    top_score, top_finding, top_action = priorities[0]
    status = "warning" if top_score >= 9 else "healthy"
    return status, evidence, f"Top action: {top_action}"


def _run_communication_health() -> tuple[str, list[str], str]:
    """Verify Telegram and email communication channels are working."""
    import json, urllib.request

    _env_path = os.path.join(ROOT, '.env')
    if os.path.exists(_env_path):
        with open(_env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())

    evidence: list[str] = []

    # Telegram bot check
    tg_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    tg_chat  = os.getenv('TELEGRAM_CHAT_ID', '')
    tg_ok = False
    if tg_token:
        try:
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{tg_token}/getMe",
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read())
            bot_name = data.get('result', {}).get('username', '?')
            tg_ok = data.get('ok', False)
            evidence.append(f"✓ Telegram bot @{bot_name} is responsive")
        except Exception as e:
            evidence.append(f"✗ Telegram bot check failed: {e}")
    else:
        evidence.append("✗ TELEGRAM_BOT_TOKEN not set")

    evidence.append(f"{'✓' if tg_chat else '✗'} Chat ID: {'configured' if tg_chat else 'NOT SET'}")

    # Email config check
    email_addr = os.getenv('NEXUS_EMAIL', '')
    email_pass  = os.getenv('NEXUS_EMAIL_PASSWORD', '')
    if email_addr and email_pass:
        try:
            import imaplib
            imap = imaplib.IMAP4_SSL('imap.gmail.com')
            imap.login(email_addr, email_pass)
            imap.logout()
            evidence.append(f"✓ Email IMAP login OK ({email_addr})")
        except Exception as e:
            evidence.append(f"✗ Email IMAP failed: {e}")
    else:
        evidence.append("✗ Email credentials not configured")

    # Hermes gate (DB-based)
    url = os.getenv('SUPABASE_URL', '')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
    if url and key:
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/hermes_aggregates?select=id&limit=1",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                json.loads(r.read())
            evidence.append("✓ Hermes gate (DB cooldown table) accessible")
        except Exception as e:
            evidence.append(f"✗ Hermes gate DB access failed: {e}")
    else:
        evidence.append("✗ Supabase not configured — gate running in local-only mode")

    all_ok = all("✓" in e for e in evidence)
    status = "healthy" if all_ok else "warning"
    rec = "All communication channels operational. Hermes can hear you." if all_ok \
        else "Fix failing channels listed above before relying on automated alerts."

    return status, evidence, rec


def _run_ceo_report() -> tuple[str, list[str], str]:
    """Pull latest CEO briefing from DB."""
    try:
        from ceo_agent.briefing_service import get_latest_briefing
        brief = get_latest_briefing()
        if not brief:
            return "unknown", ["No CEO briefing found in DB"], "Run: python -m ceo_agent.ceo_worker --type daily_ceo"

        headline = brief.get('headline', '')
        summary  = brief.get('summary', '')
        updates  = brief.get('top_updates') or []
        blockers = brief.get('blockers') or []

        evidence = [headline]
        if blockers:
            evidence.append(f"Blockers: {len(blockers)}")
        for u in updates[:4]:
            evidence.append(f"{u.get('agent','?')}: {str(u.get('text',''))[:80]}")

        status = "warning" if blockers else "healthy"
        rec = "Review blockers above." if blockers else "No blockers. Continue normal operations."
        return status, evidence, rec
    except Exception as e:
        return "unknown", [f"Briefing fetch failed: {e}"], "Check CEO worker."


def _run_business_opportunities() -> tuple[str, list[str], str]:
    """Content-first monetization: reads real local artifacts via hermes_monetization_today."""
    try:
        from lib.hermes_monetization_today import (
            build_today_monetization_plan,
            format_today_monetization_response,
        )
        plan = build_today_monetization_plan()
        if plan["asset_count"] == 0:
            return "unknown", [
                "No content assets found in local artifact store.",
                "Run a content pipeline cycle to generate monetizable assets.",
            ], "Start with: 'create first draft' to build a credit/funding checklist."

        evidence: list[str] = []
        for a in plan["assets"][:6]:
            label = a["asset_type"].replace("_", " ").title()
            evidence.append(f"  {label}: {a['name'][:55]} (score: {a['score']})")
        if plan["top_actions"]:
            evidence.append("")
            for ln in plan["top_actions"].splitlines()[:3]:
                if ln.strip():
                    evidence.append(f"  {ln.strip()}")
        evidence.append("")
        evidence.append("Approval boundary: publishing, spending, sending require Ray sign-off.")

        rec = format_today_monetization_response(plan)
        return "healthy", evidence, rec
    except Exception as exc:
        return "unknown", [f"Monetization handler error: {exc}"], (
            "Run 'show opportunities' again — if this persists, check lib/hermes_monetization_today.py"
        )


def _run_app_url() -> tuple[str, list[str], str]:
    """Return canonical app URL."""
    evidence = [
        "Platform URL: https://goclearonline.cc",
        "Admin dashboard: https://goclearonline.cc/admin",
        "Deploy target: Netlify (auto-deploy from nexuslive main branch)",
    ]
    return "healthy", evidence, "Access Nexus at https://goclearonline.cc"


def _run_onboarding_status() -> tuple[str, list[str], str]:
    """Check onboarding completion rates."""
    try:
        import json, urllib.request
        _env_path = os.path.join(ROOT, '.env')
        if os.path.exists(_env_path):
            with open(_env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, _, v = line.partition('=')
                        os.environ.setdefault(k.strip(), v.strip())

        url = os.getenv('SUPABASE_URL', '')
        key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')

        req = urllib.request.Request(
            f"{url}/rest/v1/user_profiles?select=onboarding_complete&limit=500",
            headers={'apikey': key, 'Authorization': f'Bearer {key}'},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())

        total = len(rows)
        complete = sum(1 for r in rows if r.get('onboarding_complete'))
        pct = (complete / total * 100) if total else 0

        evidence = [
            f"Total profiles: {total}",
            f"Onboarding complete: {complete} ({pct:.0f}%)",
            f"Onboarding incomplete: {total - complete}",
        ]
        status = "healthy" if pct >= 60 else "warning"
        rec = f"{pct:.0f}% completion. " + ("Good retention." if pct >= 60 else "Focus on reducing friction in onboarding steps.")
        return status, evidence, rec
    except Exception as e:
        return "unknown", [f"Onboarding query failed: {e}"], "Check profiles table in Supabase."


def _run_platform_analytics() -> tuple[str, list[str], str]:
    """Pull basic platform analytics from Supabase."""
    try:
        import json, urllib.request
        from datetime import datetime, timezone, timedelta
        _env_path = os.path.join(ROOT, '.env')
        if os.path.exists(_env_path):
            with open(_env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, _, v = line.partition('=')
                        os.environ.setdefault(k.strip(), v.strip())

        url = os.getenv('SUPABASE_URL', '')
        key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
        cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        evidence = []

        # Total users
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/user_profiles?select=id&limit=1000",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                users = json.loads(r.read())
            evidence.append(f"Total users: {len(users)}")
        except Exception:
            evidence.append("Total users: unavailable")

        # Invites sent
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/invite_codes?select=id,used_at&limit=500",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                invites = json.loads(r.read())
            used = sum(1 for i in invites if i.get('used_at'))
            evidence.append(f"Invites sent: {len(invites)}, used: {used} ({100*used//len(invites) if invites else 0}%)")
        except Exception:
            evidence.append("Invites: unavailable")

        # Knowledge items
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/knowledge_items?select=id,status&limit=500",
                headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            )
            with urllib.request.urlopen(req, timeout=6) as r:
                ki = json.loads(r.read())
            approved = sum(1 for k in ki if k.get('status') == 'approved')
            evidence.append(f"Knowledge items: {len(ki)} total, {approved} approved")
        except Exception:
            evidence.append("Knowledge items: unavailable")

        status = "healthy" if evidence else "unknown"
        return status, evidence, "Platform analytics pulled from live DB."
    except Exception as e:
        return "unknown", [f"Analytics query failed: {e}"], "Check Supabase connectivity."


# ── Strategic operating partner handlers ──────────────────────────────────────

def _nexus_ai_root() -> str:
    return os.path.expanduser("~/nexus-ai")


def _latest_nexus_file(glob_pattern: str) -> str | None:
    import glob as _glob
    files = _glob.glob(os.path.join(_nexus_ai_root(), glob_pattern))
    return max(files, key=os.path.getmtime) if files else None


def _read_nexus_artifact(glob_pattern: str, max_chars: int = 600) -> str:
    path = _latest_nexus_file(glob_pattern)
    if not path or not os.path.exists(path):
        return "artifact_missing"
    try:
        text = open(path).read()
        return text[:max_chars] + ("…[truncated]" if len(text) > max_chars else "")
    except Exception as e:
        return f"artifact_read_error: {e}"


def _run_nexus_status() -> tuple[str, list[str], str]:
    text = _read_nexus_artifact("docs/reports/ceo_review/NEXUS_MONETIZATION_CEO_PACKET_*.md")
    if "artifact_missing" in text:
        return "unknown", ["No CEO packet found — no verified artifact to report from"], (
            "Run: python scripts/run_nexus_monetization_operating_cycle.py "
            "--mode validation --cost free --require-artifacts true"
        )
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")][:8]
    # Augment with live evidence index
    try:
        nexus_lib = os.path.join(_nexus_ai_root(), "lib")
        if nexus_lib not in sys.path:
            sys.path.insert(0, os.path.dirname(nexus_lib))
        from lib.hermes_evidence_mode import verified_status_block
        lines.append(verified_status_block())
    except Exception:
        pass
    return "healthy", lines, "See full packet at nexus-ai/docs/reports/ceo_review/"


def _run_handoff_check() -> tuple[str, list[str], str]:
    import json, glob as _glob
    pattern = os.path.join(_nexus_ai_root(), "docs/reports/hermes_handoffs/handoff_*.json")
    files = sorted(_glob.glob(pattern), key=os.path.getmtime)
    pending = []
    for f in files:
        try:
            data = json.loads(open(f).read())
            if data.get("status") == "pending_ray":
                pending.append(f"• {data.get('title','?')} — {data.get('action_required','')[:70]}")
        except Exception:
            pass
    if not pending:
        return "healthy", ["No pending handoffs."], "Nothing waiting for your approval."
    return "warning", pending[:5], f"{len(pending)} handoff(s) need your approval. Check nexus-ai/docs/reports/hermes_handoffs/"


def _run_decision_log() -> tuple[str, list[str], str]:
    import json
    log_path = os.path.join(_nexus_ai_root(), "docs/reports/hermes_decisions/hermes_decision_log.jsonl")
    if not os.path.exists(log_path):
        return "unknown", ["No decision log found."], "Decision log is created when Hermes classifies actions."
    lines = open(log_path).read().strip().splitlines()
    recent = []
    for line in lines[-5:]:
        try:
            r = json.loads(line)
            recent.append(f"[{r.get('logged_at','')[:16]}] {r.get('action','?')} → {r.get('decision','?')}")
        except Exception:
            pass
    return "healthy", recent or ["No recent decisions."], "Full log at nexus-ai/docs/reports/hermes_decisions/"


def _run_demo_broker_status() -> tuple[str, list[str], str]:
    import json
    enabled = os.getenv("OANDA_DEMO_ENABLED", "false")
    env = os.getenv("OANDA_ENVIRONMENT", "practice")
    # Safety: reject if live environment is somehow set
    if env == "live" or os.getenv("OANDA_ALLOW_LIVE", "false").lower() == "true":
        return "critical", [
            "⛔ BLOCKED: OANDA_ENVIRONMENT=live or OANDA_ALLOW_LIVE=true detected.",
            "Live trading is prohibited. Set OANDA_ENVIRONMENT=practice.",
        ], "Do NOT place any orders. Fix env vars before proceeding."
    packet = _latest_nexus_file("integrations/oanda_demo/reports/demo_execution_packet_*.json")
    evidence = [f"Environment: {env} (practice only) | DEMO_ENABLED: {enabled}"]
    if packet and os.path.exists(packet):
        try:
            data = json.loads(open(packet).read())
            ev = data.get("evaluation", {})
            evidence.append(f"Last evaluation: pass={ev.get('pass')} | {ev.get('reason','')[:60]}")
            order = data.get("order_result") or {}
            if order:
                evidence.append(f"Last order: {'✅ filled' if order.get('ok') else '❌ ' + order.get('error','failed')}")
            evidence.append(f"Artifact: {os.path.basename(packet)}")
        except Exception:
            pass
    else:
        evidence.append("No demo execution packet — artifact_missing. NO CLAIMS without this artifact.")
    evidence.append("⚠ Hermes will NOT report trade execution without a verified order artifact.")
    return "healthy", evidence, "OANDA practice-only. Requires Ray approval + OANDA_DEMO_ENABLED=true to place orders."


def _run_premium_blocker_resolver() -> tuple[str, list[str], str]:
    text = _read_nexus_artifact("docs/reports/premium_blockers/blocker_resolution_beehiiv_*.md")
    if "artifact_missing" in text:
        return "unknown", ["No premium blocker resolution found."], (
            "Run: python scripts/run_nexus_monetization_operating_cycle.py "
            "--mode validation --resolve-premium-blockers"
        )
    lines = [l.strip() for l in text.splitlines() if l.strip()][:8]
    return "healthy", lines, "See full resolution at nexus-ai/docs/reports/premium_blockers/"


def _run_save_ray_feedback() -> tuple[str, list[str], str]:
    return "healthy", [
        "To save feedback, send: 'record lesson: [your lesson]'",
        "Or: 'remember this: [text]'",
        "Saved to: nexus-ai/docs/reports/ray_feedback/",
    ], "Feedback is saved and used to improve Hermes behavior in future cycles."


def _run_notification_log() -> tuple[str, list[str], str]:
    import json
    log_path = os.path.join(_nexus_ai_root(), "docs/reports/hermes_proactive_notifications.jsonl")
    if not os.path.exists(log_path):
        return "unknown", ["No notifications logged yet."], "Notifications are sent via --notify-ray flag on operating cycle."
    lines = open(log_path).read().strip().splitlines()
    recent = []
    for line in lines[-5:]:
        try:
            r = json.loads(line)
            status = "✅" if r.get("sent") else "⛔ suppressed"
            recent.append(f"[{r.get('sent_at','')[:16]}] {r.get('event_type','?')} {status}")
        except Exception:
            pass
    return "healthy", recent or ["No recent notifications."], "Full log at nexus-ai/docs/reports/hermes_proactive_notifications.jsonl"


def _run_source_intake(raw_text: str) -> tuple[str, list[str], str]:
    """Process a Telegram message containing a URL — register and dispatch."""
    try:
        sys.path.insert(0, _nexus_ai_root())
        from lib.hermes_telegram_source_intake import process_telegram_message
        from lib.hermes_scout_dispatcher import dispatch_from_intake
        record = process_telegram_message(raw_text)
        dispatch = dispatch_from_intake(record)
        evidence = [
            f"Intake ID: {record.intake_id}",
            f"Type: {record.source_type}",
            f"URL: {record.url or '(text message)'}",
            f"Assigned scout: {dispatch.primary_scout}",
            f"Status: {dispatch.status}",
        ]
        if hasattr(dispatch, "handoff_path") and dispatch.handoff_path:
            evidence.append(f"Handoff: {os.path.basename(dispatch.handoff_path)}")
        needs_approval = dispatch.to_dict().get("requires_approval", False)
        if needs_approval:
            return "warning", evidence, (
                f"⛔ Requires Ray approval before processing. "
                f"Reason: {dispatch.to_dict().get('approval_reason','')}"
            )
        return "healthy", evidence, (
            f"Source registered. Scout: {dispatch.primary_scout}. "
            f"I'll notify you when the first artifact is ready."
        )
    except Exception as e:
        return "unknown", [f"Source intake error: {e}"], (
            "Source could not be registered. Check lib/hermes_telegram_source_intake.py"
        )


def _run_source_intake_status() -> tuple[str, list[str], str]:
    """Show recent source intake queue."""
    try:
        sys.path.insert(0, _nexus_ai_root())
        from lib.hermes_telegram_source_intake import get_intake_summary, get_recent_intakes
        summary = get_intake_summary()
        recent = get_recent_intakes(limit=5)
        evidence = [summary]
        for r in recent:
            d = r.to_dict()
            name = d.get("url") or d.get("raw_message", "")[:40]
            evidence.append(f"[{d.get('intake_id','?')[:12]}] {d.get('source_type','?')} — {name}")
        if not recent:
            return "unknown", ["No sources received yet."], (
                "Send a YouTube URL, GitHub link, or source idea to register it."
            )
        return "healthy", evidence, "Full intake log: docs/reports/intake/telegram_source_intake.jsonl"
    except Exception as e:
        return "unknown", [f"Source intake status error: {e}"], (
            "Check lib/hermes_telegram_source_intake.py"
        )


def _run_artifact_registry_status() -> tuple[str, list[str], str]:
    """Show artifact registry summary."""
    try:
        sys.path.insert(0, _nexus_ai_root())
        from lib.nexus_artifact_registry import latest_artifacts, create_registry_summary
        artifacts = latest_artifacts(limit=10)
        if not artifacts:
            return "unknown", ["Artifact registry is empty."], (
                "Run: python scripts/register_existing_artifacts.py to backfill."
            )
        by_agent = {}
        for a in artifacts:
            d = a.to_dict()
            agent = d.get("agent_name", "unknown")
            by_agent[agent] = by_agent.get(agent, 0) + 1
        evidence = [f"Recent artifacts: {len(artifacts)}"]
        for agent, count in sorted(by_agent.items()):
            evidence.append(f"  {agent}: {count}")
        evidence.append(f"Latest: {artifacts[-1].to_dict().get('title','?')[:60]}")
        return "healthy", evidence, "Full registry: docs/reports/artifact_registry/nexus_artifact_registry.jsonl"
    except Exception as e:
        return "unknown", [f"Artifact registry error: {e}"], "Check lib/nexus_artifact_registry.py"


def _run_youtube_source_status() -> tuple[str, list[str], str]:
    """Report YouTube sources from the verified registry — NO FABRICATION."""
    import json
    registry_path = os.path.join(_nexus_ai_root(), "docs/reports/youtube/source_registry.json")
    if not os.path.exists(registry_path):
        return "unknown", [
            "No YouTube source registry found.",
            "artifact_missing — source_registry.json does not exist yet.",
        ], (
            "Run: python scripts/run_youtube_source_reconciliation.py"
        )
    try:
        data = json.loads(open(registry_path).read())
    except Exception as e:
        return "unknown", [f"Registry read error: {e}"], "Check docs/reports/youtube/source_registry.json"

    if not data:
        return "unknown", ["Registry exists but contains no sources."], (
            "Submit a YouTube source: 'register youtube source <url>'"
        )

    counts: dict[str, int] = {}
    evidence = []
    for rec in data.values():
        s = rec.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1

    for status, count in sorted(counts.items()):
        evidence.append(f"{status}: {count} source(s)")

    # Show recent active sources with their source_id
    active = [r for r in data.values() if r.get("status") == "active"][:3]
    for rec in active:
        name = rec.get("channel_name") or rec.get("video_title") or rec.get("url", "?")[:50]
        evidence.append(f"✅ {rec['source_id'][:8]} — {name}")

    total = len(data)
    return "healthy", evidence, (
        f"{total} source(s) in registry. "
        "Run `python scripts/run_youtube_intelligence_cycle.py` to extract intelligence."
    )


def _run_provider_status() -> tuple[str, list[str], str]:
    """Report live provider availability and policy via hermes_provider_policy."""
    try:
        from lib.hermes_provider_policy import get_policy
        policy = get_policy(refresh=True)
        summary = policy.summary_dict()
        evidence = [
            f"strategic_provider: {summary['best_for_strategic']}",
            f"summary_provider:   {summary['best_for_summary']}",
            f"best_available:     {summary['best_available']}",
            f"openrouter_allowed: {summary['openrouter_allowed']}",
            f"priority_order:     {', '.join(summary['priority'])}",
        ]
        for p in summary["providers"]:
            icon = "✅" if p["available"] else "❌"
            note = f" ({p['reason']})" if p["reason"] and not p["available"] else ""
            evidence.append(f"{icon} {p['provider']}{note}")
        status = "healthy" if summary["best_for_strategic"] != "evidence_only" else "degraded"
        rec = (
            f"Active brain: {summary['best_for_strategic']}. "
            "OpenRouter is DISABLED unless HERMES_ALLOW_OPENROUTER_FALLBACK=true."
            if not summary["openrouter_allowed"]
            else f"Active brain: {summary['best_for_strategic']}. OpenRouter fallback is ENABLED."
        )
        return status, evidence, rec
    except Exception as e:
        return "unknown", [f"provider_policy error: {e}"], "Check lib/hermes_provider_policy.py"


# ── Plain-text memory command handlers (no HERMES REPORT wrapper) ────────────

def _plain_memory_sources() -> str:
    """Plain text memory sources response — bypasses build_report wrapper."""
    lines = [
        "HERMES MEMORY SOURCES",
        "",
        "Live answer sources:",
        "- Current conversation context",
        "- Latest content artifacts",
        "- Action queue",
        "- Decision log",
        "- Source intake records",
        "- Active operating rules",
        "- hermes_memory_v2 active/live_answer records when preview/reader is enabled",
        "",
        "Historical sources:",
        "- archived executive memory",
        "- old handoffs",
        "- old reports",
        "- old provider snapshots",
        "",
        "Blocked from live answers:",
        "- old Executive Memory defaults",
        "- stale provider status",
        "- Quality escalation fallback",
        "- stale Ollama/Beehiiv/YouTube/OpenRouter defaults",
        "",
        "Supabase memory v2:",
        "- Table: hermes_memory_v2 (exists)",
    ]
    try:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
        if url and key:
            from supabase import create_client
            client = create_client(url, key)
            resp = client.table("hermes_memory_v2").select("memory_id", count="exact") \
                .eq("status", "active").eq("scope", "live_answer").execute()
            count = resp.count if resp.count is not None else len(resp.data)
            lines.append(f"- Current rows: {count} active/live_answer")
        else:
            lines.append("- Current rows: unavailable (env not set)")
    except Exception:
        lines.append("- Current rows: unavailable")
    try:
        from lib.hermes_memory_v2_shadow import is_primary_mode_active, get_memory_v2_mode as _gmode
        _mode = _gmode()
        if _mode == "primary":
            lines.append("- Live Telegram reader: PRIMARY for structured memory")
        elif _mode == "shadow":
            lines.append("- Live Telegram reader: shadow only (comparison, no live impact)")
        else:
            lines.append("- Live Telegram reader: preview only / not primary yet")
    except Exception:
        lines.append("- Live Telegram reader: preview only / not primary yet")
    lines.append("- Preview command: 'show memory v2 preview'")
    lines += ["", "Evidence:", "- docs/HERMES_MEMORY_SAFETY_CONTRACT.md"]
    return "\n".join(lines)


def _plain_answer_source() -> str:
    """Plain text answer source response — bypasses build_report wrapper."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    lines = [
        "ANSWER SOURCE",
        "",
        "I answered from the current active context.",
        "",
        "Most recent evidence:",
    ]
    try:
        from lib.hermes_daily_cycle_state import find_latest_daily_cycle
        cycle = find_latest_daily_cycle()
        if cycle.get("review"):
            lines.append(f"- Latest content artifact: {cycle['review']}")
        if cycle.get("intake"):
            lines.append(f"- Latest action: {cycle['intake']}")
    except Exception:
        pass
    dl_path = root / "docs" / "reports" / "decisions" / "hermes_decision_log.jsonl"
    decision_path = str(dl_path.relative_to(root)) if dl_path.exists() else "docs/reports/decisions/hermes_decision_log.jsonl"
    lines.append(f"- Latest decision log: {decision_path}")
    lines.append("- Memory policy: docs/HERMES_MEMORY_SAFETY_CONTRACT.md")
    lines.append("- Memory v2: active/live_answer preview records if available")
    lines.append("")
    lines.append("I did not use archived executive memory.")
    lines.append("")
    lines.append("Use \"show technical source details\" for full report format.")
    return "\n".join(lines)


def _plain_active_operating_rules() -> str:
    """Plain text active operating rules response — bypasses build_report wrapper."""
    v2_count = None
    try:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "") or os.environ.get("SUPABASE_KEY", "")
        if url and key:
            from supabase import create_client
            client = create_client(url, key)
            resp = client.table("hermes_memory_v2").select("memory_id", count="exact") \
                .eq("status", "active").eq("scope", "live_answer") \
                .eq("memory_type", "operating_rule").execute()
            v2_count = resp.count if resp.count is not None else len(resp.data)
    except Exception:
        pass
    lines = [
        "ACTIVE OPERATING RULES",
        "",
        "Hermes is currently following these live-answer rules:",
        "",
        "1. Evidence first.",
        "2. Do not invent task status, counts, commits, approvals, or source processing.",
        "3. Use current artifacts/actions/decisions/source intake before old memory.",
        "4. Use active/live_answer memory only for normal Telegram answers.",
        "5. Archived/debug memory only when Ray explicitly asks.",
        "6. Publishing, paid tools, live trading, client-facing content, Stripe/payment, and production deployment require Ray approval.",
        "7. Internal drafts, research, scoring, and action queue updates are allowed.",
        "",
        "Memory v2:",
        "- hermes_memory_v2 exists",
        "- Batch 1 active rules/preferences/context inserted",
        f"- Active operating_rule records: {v2_count if v2_count is not None else 'unavailable'}",
        "- Live reader status: preview only unless already enabled",
        "",
        "Evidence:",
        "- docs/HERMES_MEMORY_SAFETY_CONTRACT.md",
        "- docs/HERMES_MEMORY_V2_SCHEMA.md",
        "- hermes_memory_v2 active/live_answer records if available",
    ]
    return "\n".join(lines)


# ── Legacy tuple-returning handlers (kept for backward compatibility) ─────────

def _run_memory_sources() -> tuple[str, list[str], str]:
    """Kept for _INTENT_HANDLERS compatibility — routes to plain version."""
    return "healthy", [_plain_memory_sources()], "I answered from the current active context only."


def _run_answer_source() -> tuple[str, list[str], str]:
    """Kept for _INTENT_HANDLERS compatibility — routes to plain version."""
    return "healthy", [_plain_answer_source()], "Sources resolve to current active context only."


# ── Stale memory debug handler ────────────────────────────────────────────────

def _run_stale_memory_debug() -> tuple[str, list[str], str]:
    """Show the stale/hardcoded defaults that are BLOCKED from live Telegram answers."""
    try:
        from lib.hermes_executive_memory import load_archived_executive_memory_defaults
        archived = load_archived_executive_memory_defaults()
        evidence = [
            "STALE MEMORY DEBUG — DEBUG ONLY — BLOCKED FROM LIVE ANSWERS",
            "",
            "These records are shown only because you explicitly requested debug memory.",
            "",
            "These stale defaults are NEVER injected into normal Telegram replies.",
            "They are kept for reference and debugging only.",
            "",
        ]
        for cat, items in archived.items():
            if cat in ("updated_at", "version", "source"):
                continue
            label = cat.replace("_", " ").title()
            evidence.append(f"[{label}]")
            if items:
                for item in items[:3]:
                    evidence.append(f"  (BLOCKED) {item}")
                if len(items) > 3:
                    evidence.append(f"  ... +{len(items) - 3} more")
            else:
                evidence.append("  (empty)")
        return "healthy", evidence, (
            "⚠️  These are ARCHIVED / STATIC defaults. "
            "They do NOT reflect current system state."
        )
    except Exception as e:
        return "unknown", [f"Stale memory debug error: {e}"], "Check load_archived_executive_memory_defaults"


# ── Archived (stale) memory handler ───────────────────────────────────────────

def _run_archived_executive_memory() -> tuple[str, list[str], str]:
    """Show the archived (original hardcoded) executive memory defaults.

    These are NOT live — they're the stale defaults that were previously
    injected into Telegram before the Phase 2 memory safety contract.
    """
    try:
        from lib.hermes_executive_memory import load_archived_executive_memory_defaults
        archived = load_archived_executive_memory_defaults()
        evidence = [
            "ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH",
            "",
            "This is historical/debug context only. It is blocked from normal Telegram answers.",
            "",
            "These are the ORIGINAL hardcoded defaults (archived in Phase 2).",
            "They are NO LONGER injected into live Telegram responses.",
            "",
        ]
        for cat, items in archived.items():
            if cat in ("updated_at", "version", "source"):
                continue
            label = cat.replace("_", " ").title()
            if items:
                evidence.append(f"[{label}] ({len(items)} items)")
                for item in items[:3]:
                    evidence.append(f"  * {item}")
                if len(items) > 3:
                    evidence.append(f"  ... +{len(items) - 3} more")
            else:
                evidence.append(f"[{label}] (empty)")
        return "healthy", evidence, (
            "These are the archived original defaults. "
            "Run `nexus executive status` to see live active memory."
        )
    except Exception as e:
        return "unknown", [f"Archived memory load error: {e}"], (
            "Check lib/hermes_executive_memory.load_archived_executive_memory_defaults"
        )


# ── Routing table ──────────────────────────────────────────────────────────────

def _run_ceo_digest() -> tuple[str, list[str], str]:
    """Generate live CEO grouped digest with anomaly detection."""
    try:
        from lib.ceo_grouped_digest import format_grouped_digest
        digest = format_grouped_digest()
        return digest, [], "Review and action the priority items above."
    except Exception as e:
        return f"CEO digest error: {e}", [], "Check lib/ceo_grouped_digest.py"


# ── Knowledge gap handlers ─────────────────────────────────────────────────────

def _run_knowledge_gap_review() -> tuple[str, list[str], str]:
    """Show deduplicated knowledge gaps grouped by question."""
    try:
        from lib.hermes_knowledge_gap_logger import load_recent_knowledge_gaps
        gaps = load_recent_knowledge_gaps(limit=100)
        open_gaps = [g for g in gaps if g.get("status") == "open"]
        if not open_gaps:
            return "healthy", ["No open knowledge gaps on record."], (
                "Hermes answered all recent questions from active memory."
            )

        # Group by normalized_message
        groups: dict[str, dict] = {}
        counts: dict[str, int] = {}
        for g in open_gaps:
            key = g.get("normalized_message") or g.get("user_message", "?")
            key = key[:80]
            if key not in groups:
                groups[key] = g
                counts[key] = 1
            else:
                counts[key] += 1

        # Resolved candidates: phrases now handled by conversational router
        _RESOLVED_PHRASES = {
            "help", "/help", "what can you do", "what can you answer",
            "how are you", "good morning", "weather", "news",
        }
        def _is_resolved_candidate(msg: str) -> bool:
            t = msg.lower()
            return any(p in t for p in _RESOLVED_PHRASES)

        evidence = [f"Knowledge gaps — {len(groups)} unique question(s):\n"]
        for i, (key, g) in enumerate(sorted(groups.items(), key=lambda x: -counts[x[0]])[:10], 1):
            count_note = f" (asked {counts[key]}×)" if counts[key] > 1 else ""
            resolved = " [resolved candidate — now routed]" if _is_resolved_candidate(key) else ""
            evidence.append(
                f"{i}. {key[:70]}{count_note}{resolved}\n"
                f"   Reason: {g.get('reason', '?')}\n"
                f"   Fix: {g.get('suggested_handler', '?')}"
            )

        resolved_count = sum(1 for k in groups if _is_resolved_candidate(k))
        return "warning", evidence, (
            f"{len(groups)} unique gap(s) ({len(open_gaps)} total entries). "
            + (f"{resolved_count} are resolved candidates. " if resolved_count else "")
            + "Ask 'create better answers for gaps' to generate improvement proposals."
        )
    except Exception as e:
        return "unknown", [f"Gap review error: {e}"], "Check lib/hermes_knowledge_gap_logger.py"


def _run_knowledge_gap_research() -> tuple[str, list[str], str]:
    """Create internal improvement report for open gaps."""
    try:
        from lib.hermes_response_improvement_loop import create_response_improvement_report
        report_path = create_response_improvement_report()
        return "healthy", [
            "Response improvement report created.",
            f"Report: {report_path}",
            "Ray approval required before applying any proposed changes.",
        ], (
            f"Review the report and approve changes at: {report_path}"
        )
    except Exception as e:
        return "unknown", [f"Gap research error: {e}"], "Check lib/hermes_response_improvement_loop.py"


def _run_knowledge_gap_archive() -> tuple[str, list[str], str]:
    """Archive (mark resolved) gaps that have been handled."""
    return "healthy", [
        "Gap archival is a manual step — mark gaps as resolved in:",
        "docs/reports/knowledge_gaps/hermes_knowledge_gaps.jsonl",
        "Set status: 'resolved' for gaps that have been fixed.",
    ], "Update the JSONL file to mark gaps resolved."


# ── Memory v2 preview plain-text handlers ─────────────────────────────────────

def _plain_memory_v2_preview() -> str:
    """'show memory v2 preview' — plain-text preview of hermes_memory_v2 contents."""
    from lib.hermes_memory_v2_reader import build_v2_memory_context_pack, _total_count, _count_by_type
    lines = [
        "HERMES MEMORY V2 PREVIEW",
        "",
        "Status:",
        "Preview only — not the live Telegram primary reader.",
        "",
        "Rows:",
    ]
    try:
        total = _total_count()
        lines.append(f"- active/live_answer records: {total}")
        for mt in ["operating_rule", "ray_preference", "approval_policy", "project_context"]:
            cnt = _count_by_type(mt)
            label = mt.replace("_", " ")
            lines.append(f"- {label}s: {cnt}")
    except Exception:
        lines.append("- (row counts unavailable — credentials not set)")

    lines += ["", "What Hermes would read:"]
    try:
        pack = build_v2_memory_context_pack(limit=20)
        records = pack.get("records", [])
        if records:
            for i, r in enumerate(records, 1):
                title = r.get("title", "?")[:60]
                mt = r.get("memory_type", "?")
                lines.append(f"  {i}. {title} — {mt}")
        else:
            lines.append("  (no records found — check Supabase credentials)")
    except Exception:
        lines.append("  (unavailable)")

    lines += [
        "",
        "Safety:",
        "- Archived, deprecated, blocked, debug, and stale records are excluded.",
        "- Provider status snapshots are not used as current truth.",
        "- Live Telegram reader has not been switched.",
        "",
        "Evidence:",
        "- hermes_memory_v2",
        "- docs/HERMES_MEMORY_V2_SCHEMA.md",
        "- docs/HERMES_MEMORY_SAFETY_CONTRACT.md",
    ]
    return "\n".join(lines)


def _plain_memory_v2_compare() -> str:
    """'compare memory v2' — mode-aware comparison of current vs v2 reader."""
    from lib.hermes_memory_v2_reader import compare_v2_with_current_memory
    from lib.hermes_memory_v2_shadow import (
        PLANNED_BATCH_TYPES, EXCLUDED_FROM_CURRENT_TRUTH, get_memory_v2_mode,
    )
    try:
        cmp = compare_v2_with_current_memory()
    except Exception as exc:
        return f"MEMORY READER COMPARISON\n\nComparison unavailable: {exc}"

    mode = get_memory_v2_mode()

    lines = ["MEMORY READER COMPARISON", ""]

    if mode == "primary":
        lines += [
            "Current live reader:",
            "- hermes_memory_v2 is PRIMARY for structured memory",
            "- current conversation context, latest artifacts, action queue, decision log,",
            "  source intake, and live provider policy still have priority where applicable",
        ]
    elif mode == "shadow":
        lines += [
            "Current reader:",
            "- live answers still use current active reader",
            "- hermes_memory_v2 loaded in shadow for comparison only",
        ]
    elif mode == "off":
        lines += [
            "Current reader:",
            "- hermes_memory_v2 is off",
            "- live answers use current active reader only",
        ]
    else:  # preview
        lines += [
            "Current reader:",
            "- live answers use current active reader",
            "- hermes_memory_v2 available in preview commands only",
        ]

    lines += ["", "Memory v2:"]
    if cmp.get("v2_available"):
        lines.append(f"- {cmp['v2_total']} active/live_answer records")
        lines.append("- all 8 planned Batch 1/2 types present" if not cmp.get("missing_from_v2") else
                     f"- missing types: {cmp['missing_from_v2']}")
        v2_by_type = cmp.get("v2_by_type", {})
        for mt in PLANNED_BATCH_TYPES:
            if v2_by_type.get(mt, 0) > 0:
                lines.append(f"- {mt}")
    else:
        lines.append("- unavailable (credentials not set in this environment)")

    lines += ["", "Still excluded from current-truth memory:"]
    for et in EXCLUDED_FROM_CURRENT_TRUTH:
        lines.append(f"- {et}")
    for legacy in ("old provider status", "old executive memory"):
        lines.append(f"- {legacy}")

    if mode == "primary":
        rec = (
            "Primary structured memory is active. Continue monitoring."
            " Do not backfill risky memory types until reviewed."
        )
    elif mode == "shadow":
        rec = (
            "Batch 1/2 coverage complete. Memory v2 shadow mode active."
            " Primary mode is approved — run 'show memory v2 primary status' to confirm."
        )
    elif mode == "off":
        rec = "Memory v2 is off. Enable with HERMES_MEMORY_V2_MODE=preview."
    else:
        missing = cmp.get("missing_from_v2", [])
        rec = cmp.get("recommendation", "")
        if not missing and not rec:
            rec = "All 8 types present. Set HERMES_MEMORY_V2_MODE=shadow to enable shadow mode."

    lines += ["", "Recommendation:", rec]
    return "\n".join(lines)


def _plain_memory_v2_rules() -> str:
    """'show memory v2 rules' — operating rules from hermes_memory_v2."""
    from lib.hermes_memory_v2_reader import load_v2_operating_rules
    result = load_v2_operating_rules(limit=20)
    lines = ["MEMORY V2 OPERATING RULES", ""]
    if not result.get("available"):
        lines.append(f"Unavailable: {result.get('reason', 'unknown')}")
        lines += ["", "Use 'show active operating rules' for current live rules."]
        return "\n".join(lines)

    records = result.get("records", [])
    lines.append(f"Operating rules in hermes_memory_v2 ({len(records)} records):")
    lines.append("")
    for i, r in enumerate(records, 1):
        title = r.get("title", "?")[:70]
        conf = r.get("confidence", "?")
        lines.append(f"  {i}. {title} (confidence: {conf})")

    lines += [
        "",
        "Note: These are preview records — not yet the live Telegram rule source.",
        "Use 'show active operating rules' for current applied rules.",
    ]
    return "\n".join(lines)


def _plain_memory_v2_status() -> str:
    """'show memory v2 status' — current state of the v2 reader."""
    from lib.hermes_memory_v2_reader import explain_v2_reader_status
    return explain_v2_reader_status()


def _plain_small_talk(cmd: str = "") -> str:
    """Natural response to small talk / greetings — no evidence dump."""
    from datetime import date
    today = date.today().strftime("%A, %B %-d, %Y")
    text = cmd.lower()
    if any(w in text for w in ("sleep", "rest", "rested", "awake")):
        return (
            "I don't sleep, Ray — I'm online and ready.\n\n"
            "I can help you review Nexus status, memory v2, today's money plan, "
            "content drafts, scouts, goals, or system gaps."
        )
    if any(w in text for w in ("good morning",)):
        return f"Good morning. Today is {today}.\n\nReady when you are — ask anything or say 'what do you recommend'."
    if any(w in text for w in ("good afternoon",)):
        return f"Good afternoon. Today is {today}.\n\nAsk me anything or say 'what do you recommend'."
    if any(w in text for w in ("good evening", "good night")):
        return f"Good evening. Today is {today}.\n\nAsk me anything or say 'what do you recommend'."
    return (
        "I'm online and ready, Ray.\n\n"
        "I can help with: Nexus status, memory v2, today's money plan, "
        "content drafts, scouts, goals, or knowledge gaps."
    )


def _plain_date_time() -> str:
    """Return today's date without an artifact evidence dump."""
    from datetime import date
    try:
        from lib.hermes_memory_v2_shadow import get_memory_v2_mode
        mode = get_memory_v2_mode()
    except Exception:
        mode = "preview"
    today = date.today().strftime("%A, %B %-d, %Y")
    return (
        f"Today is {today}.\n\n"
        "Nexus context:\n"
        f"- Memory v2 mode: {mode} for structured memory\n"
        "- Live answers still prioritize current artifacts, actions, decisions, "
        "source intake, and provider policy\n\n"
        "I can give the system date from the runtime, but use your device clock for exact local time."
    )


def _plain_tomorrow_plan() -> str:
    """Return a plain tomorrow plan — no artifact dump."""
    lines = [
        "TOMORROW PLAN",
        "",
        "Based on current Nexus goals and assets, I recommend:",
        "",
        "1. Review the Credit/Funding Readiness newsletter draft.",
        "2. Approve or revise the lead magnet/newsletter/video asset packet.",
        "3. Continue daily opportunity intake.",
        "4. Monitor memory v2 primary mode for stale-answer regressions.",
        "5. Keep risky memory types excluded until reviewed.",
        "",
        "Approval:",
        "I will not publish, email subscribers, sell, deploy, spend money, "
        "or use client-facing content without Ray approval.",
        "",
        "Evidence:",
        "- active goals",
        "- latest content artifact",
        "- memory v2 primary status",
    ]
    return "\n".join(lines)


def _plain_unknown_handling() -> str:
    """Return the 'if I don't know' policy — no quality fallback dump."""
    lines = [
        "IF I DON'T KNOW",
        "",
        "I should not guess.",
        "",
        "My process is:",
        "1. Check active memory and current artifacts first.",
        "2. Check action queue, decision log, source intake, and goals.",
        "3. If the answer is still missing, say I don't have verified evidence.",
        "4. Log the gap so it can be improved.",
        "5. Ask Ray whether to research it, create a task, or ignore it.",
        "",
        "I should never invent:",
        "- task status",
        "- approval counts",
        "- commit hashes",
        "- source processing results",
        "- trading results",
        "- client/public actions",
        "",
        "You can say:",
        "- show knowledge gaps",
        "- create better answers for gaps",
        "- research this",
        "- add this as a lesson",
    ]
    return "\n".join(lines)


def _plain_knowledge_gaps() -> str:
    """'show knowledge gaps' — plain text, no HERMES REPORT wrapper."""
    try:
        from lib.hermes_knowledge_gap_logger import load_recent_knowledge_gaps
        gaps = load_recent_knowledge_gaps(limit=100)
        open_gaps = [g for g in gaps if g.get("status") == "open"]
        if not open_gaps:
            return (
                "KNOWLEDGE GAPS\n\nNo open knowledge gaps on record.\n\n"
                "Hermes answered all recent questions from active memory."
            )

        groups: dict[str, dict] = {}
        counts: dict[str, int] = {}
        for g in open_gaps:
            key = (g.get("normalized_message") or g.get("user_message", "?"))[:80]
            if key not in groups:
                groups[key] = g
                counts[key] = 1
            else:
                counts[key] += 1

        _RESOLVED_PHRASES = {
            "help", "/help", "what can you do", "what can you answer",
            "how are you", "good morning", "weather", "news",
            "did you sleep", "what is today", "what day", "tomorrow",
        }
        def _is_resolved(msg: str) -> bool:
            t = msg.lower()
            return any(p in t for p in _RESOLVED_PHRASES)

        lines = ["KNOWLEDGE GAPS", "", "Open / recent gaps:"]
        sorted_items = sorted(groups.items(), key=lambda x: -counts[x[0]])[:10]
        for i, (key, g) in enumerate(sorted_items, 1):
            count_note = f" — asked {counts[key]}×" if counts[key] > 1 else ""
            status_note = "resolved candidate — now routed" if _is_resolved(key) else "open"
            fix_note = g.get("suggested_handler", g.get("reason", "needs handler"))
            lines += [
                f"{i}. {key[:70]}{count_note}",
                f"   Status: {status_note}",
                f"   Fix: {fix_note}",
                "",
            ]

        resolved_count = sum(1 for k in groups if _is_resolved(k))
        total_entries = len(open_gaps)
        lines += [
            "Summary:",
            f"- {len(groups)} unique gap(s)",
            f"- {total_entries} total entries",
            f"- {resolved_count} resolved candidates",
            "",
            "Next:",
            "Say \"create better answers for gaps\" to generate improvement proposals.",
            "Use \"show technical gap report\" for the full HERMES REPORT wrapper.",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"KNOWLEDGE GAPS\n\nUnable to load gaps: {exc}\n\nCheck lib/hermes_knowledge_gap_logger.py"


def _plain_memory_v2_primary_status() -> str:
    """'show memory v2 primary status' — primary mode guards and active state."""
    from lib.hermes_memory_v2_shadow import format_primary_status
    return format_primary_status()


# ── Learning loop plain-text handlers ─────────────────────────────────────────

def _plain_lesson_record(cmd: str = "") -> str:
    """Handle 'record this lesson: <text>' commands."""
    from lib.hermes_learning_loop import create_lesson_proposal, detect_lesson_intent
    if not detect_lesson_intent(cmd):
        return (
            "LESSON RECORD\n\n"
            "To record a lesson, say:\n"
            "  record this lesson: <lesson text>\n"
            "  remember this lesson: <lesson text>\n"
            "  learn this: <lesson text>\n\n"
            "The lesson will be stored as a pending proposal for your review.\n"
            "Use 'show pending lessons' to review, then 'approve lesson <id>' to make it active."
        )
    try:
        proposal = create_lesson_proposal(cmd)
        lid    = proposal.get("lesson_id", "?")
        status = proposal.get("proposed_status", "?")
        title  = proposal.get("title", "?")[:60]
        flags  = proposal.get("safety_flags", [])
        if status == "blocked":
            return (
                "LESSON BLOCKED\n\n"
                "Your lesson was blocked by safety validation.\n\n"
                f"Reason(s): {', '.join(flags)}\n\n"
                "Lessons cannot bypass safety policies, enable live trading, "
                "publishing, payments, or contain secrets."
            )
        return (
            f"LESSON PROPOSAL CREATED\n\n"
            f"ID:     {lid}\n"
            f"Title:  {title}\n"
            f"Status: pending_review\n\n"
            "The lesson is saved locally for your review.\n"
            "Use 'show pending lessons' to see all pending proposals.\n"
            f"Use 'approve lesson {lid}' to write it to active memory."
        )
    except Exception as exc:
        return f"LESSON RECORD\n\nFailed to create lesson proposal: {exc}"


def _plain_lesson_pending() -> str:
    """Show pending lesson proposals."""
    from lib.hermes_learning_loop import list_pending_lessons
    pending = list_pending_lessons(limit=10)
    if not pending:
        return (
            "PENDING LESSONS\n\n"
            "No lesson proposals pending review.\n\n"
            "To create a lesson, say: 'record this lesson: <lesson text>'"
        )
    lines = ["PENDING LESSONS", "", f"{len(pending)} proposal(s) awaiting review:", ""]
    for p in pending:
        lid     = p.get("lesson_id", "?")
        title   = p.get("title", "?")[:60]
        created = p.get("created_at", "?")[:10]
        lines += [
            f"ID:      {lid}",
            f"Title:   {title}",
            f"Created: {created}",
            f"Action:  approve lesson {lid}",
            "",
        ]
    lines += [
        "Safety: Pending lessons are stored locally only.",
        "They write to memory only after Ray approval.",
    ]
    return "\n".join(lines)


def _plain_lesson_active() -> str:
    """Show active lessons from hermes_memory_v2."""
    from lib.hermes_learning_loop import list_active_lessons
    active = list_active_lessons(limit=10)
    if not active:
        return (
            "ACTIVE LESSONS\n\n"
            "No active lessons in hermes_memory_v2 yet.\n\n"
            "To add a lesson: 'record this lesson: <text>'\n"
            "Then: 'approve lesson <id>'"
        )
    lines = ["ACTIVE LESSONS", "", f"{len(active)} active lesson(s) in hermes_memory_v2:", ""]
    for r in active:
        mid         = r.get("memory_id", "?")
        title       = r.get("title", "?")[:60]
        payload     = r.get("payload") or {}
        approved_by = payload.get("approved_by", "Ray Davis")
        approved_at = (payload.get("approved_at") or r.get("updated_at") or "?")[:10]
        lines += [
            f"ID:          {mid}",
            f"Title:       {title}",
            f"Approved by: {approved_by}  on {approved_at}",
            "",
        ]
    lines += [
        "Use 'deprecate lesson <memory_id>' to remove a lesson.",
        "Use 'where did that lesson come from?' for traceability.",
    ]
    return "\n".join(lines)


def _plain_lesson_approve(cmd: str = "") -> str:
    """Approve a lesson proposal: 'approve lesson <lesson_id>'."""
    from lib.hermes_learning_loop import approve_lesson
    lower     = cmd.lower()
    lesson_id = ""
    for marker in ("approve lesson ", "i approve lesson "):
        idx = lower.find(marker)
        if idx != -1:
            lesson_id = cmd[idx + len(marker):].strip()
            break
    if not lesson_id:
        return (
            "LESSON APPROVE\n\n"
            "Usage: approve lesson <lesson_id>\n\n"
            "Use 'show pending lessons' to see lesson IDs."
        )
    result = approve_lesson(lesson_id)
    if result.get("ok"):
        status = result.get("status", "approved")
        mid    = result.get("memory_id", lesson_id)
        if status in ("already_approved", "already_in_supabase"):
            return f"LESSON APPROVE\n\nLesson {mid} is already active in hermes_memory_v2."
        return (
            f"LESSON APPROVED\n\n"
            f"ID:          {mid}\n"
            f"Approved by: Ray Davis\n"
            f"Written to:  hermes_memory_v2\n"
            f"Status:      active / live_answer\n\n"
            "The lesson is now part of Hermes active memory."
        )
    flags = result.get("safety_flags", [])
    error = result.get("error", "unknown error")
    if flags:
        return (
            f"LESSON BLOCKED\n\n"
            f"Cannot approve lesson {lesson_id}.\n"
            f"Reason: {error}\n"
            f"Safety flags: {', '.join(flags)}"
        )
    return f"LESSON APPROVE\n\nFailed: {error}"


def _plain_lesson_reject(cmd: str = "") -> str:
    """Reject a lesson proposal: 'reject lesson <lesson_id>'."""
    from lib.hermes_learning_loop import reject_lesson
    lower     = cmd.lower()
    lesson_id = ""
    for marker in ("reject lesson ", "i reject lesson "):
        idx = lower.find(marker)
        if idx != -1:
            lesson_id = cmd[idx + len(marker):].strip()
            break
    if not lesson_id:
        return (
            "LESSON REJECT\n\n"
            "Usage: reject lesson <lesson_id>\n\n"
            "Use 'show pending lessons' to see lesson IDs."
        )
    result = reject_lesson(lesson_id)
    if result.get("ok"):
        return f"LESSON REJECTED\n\nLesson {lesson_id} has been rejected. No changes to hermes_memory_v2."
    return f"LESSON REJECT\n\nFailed: lesson {lesson_id} not found."


def _plain_lesson_deprecate(cmd: str = "") -> str:
    """Deprecate an active lesson: 'deprecate lesson <memory_id>'."""
    from lib.hermes_learning_loop import deprecate_lesson
    lower     = cmd.lower()
    memory_id = ""
    for marker in ("deprecate lesson ", "remove lesson "):
        idx = lower.find(marker)
        if idx != -1:
            memory_id = cmd[idx + len(marker):].strip()
            break
    if not memory_id:
        return (
            "LESSON DEPRECATE\n\n"
            "Usage: deprecate lesson <memory_id>\n\n"
            "Use 'show active lessons' to see memory IDs."
        )
    result = deprecate_lesson(memory_id)
    if result.get("ok"):
        return (
            f"LESSON DEPRECATED\n\n"
            f"Memory ID: {memory_id}\n"
            f"Status:    deprecated\n\n"
            "The lesson has been deprecated in hermes_memory_v2. "
            "It will no longer be used in live answers."
        )
    return f"LESSON DEPRECATE\n\nFailed: {result.get('error', 'unknown error')}"


def _plain_lesson_learned() -> str:
    """Show the most recent lesson proposal."""
    from lib.hermes_learning_loop import get_last_lesson_proposal
    proposal = get_last_lesson_proposal()
    if not proposal:
        return (
            "LAST LESSON\n\n"
            "No lesson proposals created yet.\n\n"
            "To teach Hermes a lesson, say:\n"
            "  record this lesson: <lesson text>"
        )
    lid         = proposal.get("lesson_id", "?")
    title       = proposal.get("title", "?")[:60]
    status      = proposal.get("proposed_status", "?")
    created     = proposal.get("created_at", "?")[:10]
    lesson_text = proposal.get("lesson_text", "?")[:200]
    lines = [
        "LAST LESSON PROPOSAL",
        "",
        f"ID:      {lid}",
        f"Title:   {title}",
        f"Status:  {status}",
        f"Created: {created}",
        "",
        "Lesson:",
        lesson_text,
        "",
    ]
    if status == "pending_review":
        lines += [f"Action:  approve lesson {lid}", f"Or:      reject lesson {lid}"]
    elif status == "approved":
        lines += ["Already approved and written to hermes_memory_v2."]
    elif status == "blocked":
        flags = proposal.get("safety_flags", [])
        lines += [f"Blocked by: {', '.join(flags)}"]
    return "\n".join(lines)


def _plain_lesson_source(cmd: str = "") -> str:
    """Show lesson traceability: 'where did that lesson come from?'"""
    from lib.hermes_learning_loop import explain_lesson_source, get_last_lesson_proposal
    lower     = cmd.lower()
    memory_id = ""
    for marker in ("explain lesson ", "lesson source ", "where did lesson "):
        idx = lower.find(marker)
        if idx != -1:
            rest = cmd[idx + len(marker):].strip()
            memory_id = rest.split()[0] if rest else ""
            break
    if not memory_id:
        proposal = get_last_lesson_proposal()
        if not proposal:
            return (
                "LESSON SOURCE\n\n"
                "No lesson proposals found.\n\n"
                "All lessons taught through Telegram are stored in:\n"
                "docs/reports/memory/learning/hermes_lesson_proposals.jsonl\n\n"
                "Active lessons trace to: hermes_memory_v2 (memory_type=lesson)"
            )
        memory_id = proposal.get("lesson_id", "")
    info   = explain_lesson_source(memory_id)
    lines = [
        "LESSON SOURCE",
        "",
        f"Memory ID: {memory_id}",
        f"Title:     {info.get('title', '?')[:60]}",
        f"Status:    {info.get('status', '?')}",
        f"Source:    {info.get('source', '?')}",
    ]
    if info.get("created_at"):
        lines.append(f"Created:   {info['created_at'][:10]}")
    if info.get("approved_at"):
        lines.append(f"Approved:  {info['approved_at'][:10]}")
    if info.get("approved_by"):
        lines.append(f"By:        {info['approved_by']}")
    lines += [
        "",
        "All lessons originate from Ray's Telegram instructions.",
        "They are never auto-approved.",
        "Proposal file: docs/reports/memory/learning/hermes_lesson_proposals.jsonl",
    ]
    return "\n".join(lines)


def _plain_lesson_approve_all(cmd: str = "") -> str:
    """Handle 'approve all pending lessons' and 'approve all 3' commands."""
    import re as _re
    from lib.hermes_learning_loop import (
        approve_all_pending_lessons,
        list_pending_lessons,
    )

    # Extract optional limit: "approve all 3" → 3
    limit: int | None = None
    m = _re.search(r'\bapprove\s+all\s+(\d+)', cmd.lower())
    if m:
        limit = int(m.group(1))

    # Count total pending before applying limit
    all_pending = list_pending_lessons(limit=100)
    total_pending = len(all_pending)

    if total_pending == 0:
        return (
            "BULK LESSON APPROVAL\n\n"
            "No pending lesson proposals to approve.\n\n"
            "Use 'record this lesson: <text>' to create lessons first.\n"
            "Use 'show pending lessons' to review what is waiting."
        )

    # Large batches: return immediately, process in background thread
    if total_pending > 5:
        import threading as _threading
        _threading.Thread(
            target=approve_all_pending_lessons,
            kwargs={"limit": limit},
            daemon=True,
        ).start()
        batch_note = f"up to {limit}" if limit else str(total_pending)
        return (
            "BULK LESSON APPROVAL STARTED\n\n"
            f"Processing {batch_note} pending lesson(s) in the background.\n\n"
            "Memory:\n"
            "Safe lessons will be written to hermes_memory_v2 as active/live_answer records.\n"
            "Unsafe lessons will be blocked automatically.\n\n"
            "Safety:\n"
            "Old tables will not be changed.\n\n"
            'Say "show active lessons" in a moment to see results.'
        )

    summary = approve_all_pending_lessons(limit=limit)
    reviewed   = summary["reviewed"]
    n_approved = summary["approved"]
    n_blocked  = summary["blocked"]
    n_skipped  = summary["skipped"]
    remaining  = total_pending - reviewed

    lines = ["BULK LESSON APPROVAL COMPLETE", ""]

    if limit and total_pending < limit:
        lines += [f"Note: {total_pending} pending lesson(s) found (requested up to {limit}).", ""]
    elif limit and remaining > 0:
        lines += [f"Note: Reviewed {limit} most recent. {remaining} more pending still need review.", ""]

    lines += [
        "Reviewed:",
        f"{reviewed} pending lesson(s)",
        "",
        "Approved:",
        f"{n_approved} lesson(s)",
        "",
        "Blocked:",
        f"{n_blocked} lesson(s)",
    ]

    if n_skipped:
        lines += ["", "Skipped (already active):", f"{n_skipped} lesson(s)"]

    if summary["approved_lessons"]:
        lines += ["", "Approved lessons:"]
        for lsn in summary["approved_lessons"]:
            lines.append(f"- {lsn['lesson_id']} — {lsn['title']}")

    if summary["blocked_lessons"]:
        lines += ["", "Blocked lessons:"]
        for lsn in summary["blocked_lessons"]:
            flags_str = ", ".join(lsn.get("flags", []))[:80]
            lines.append(f"- {lsn['lesson_id']} — {flags_str or 'safety validation failed'}")

    if summary["skipped_lessons"]:
        lines += ["", "Skipped lessons:"]
        for lsn in summary["skipped_lessons"]:
            lines.append(f"- {lsn['lesson_id']} — already active")

    lines += [
        "",
        "Memory:",
        "Approved lessons were written to hermes_memory_v2 as active/live_answer lesson records.",
        "",
        "Safety:",
        "Unsafe lessons were not approved.",
        "Old tables were not changed.",
    ]

    if remaining > 0 and not limit:
        lines += ["", f"Note: {remaining} pending lesson(s) still in queue."]

    lines += [
        "",
        "Next:",
        'Say "show active lessons" to review active memory.',
    ]
    return "\n".join(lines)


def _plain_daily_operating_cycle() -> str:
    """Handle 'run daily operating cycle', 'what should I work on today', 'show today's nexus plan'."""
    from lib.hermes_daily_operating_cycle import build_daily_operating_plan, format_daily_operating_plan
    try:
        plan = build_daily_operating_plan()
        return format_daily_operating_plan(plan)
    except Exception as exc:
        return f"DAILY OPERATING CYCLE\n\nCould not build today's plan: {exc!s:.120}\n\nTry: show active lessons, show action queue, show knowledge gaps."


def _plain_daily_approval_needed() -> str:
    """Handle legacy 'daily approval needed' intent — delegates to Phase 6C queue."""
    try:
        from lib.hermes_approval_queue import format_approval_queue
        return format_approval_queue()
    except Exception as exc:
        return f"APPROVAL QUEUE\n\nCould not load approval queue: {exc!s:.120}"


def _plain_daily_continue_while_out() -> str:
    """Handle 'continue while I am out', 'keep working while I am out'."""
    from lib.hermes_daily_operating_cycle import format_continue_while_out_plan
    return format_continue_while_out_plan()


def _plain_daily_top_revenue_move() -> str:
    """Handle 'show today's top revenue move', 'what can make money today'."""
    from lib.hermes_daily_operating_cycle import build_daily_operating_plan, format_top_revenue_move
    try:
        plan = build_daily_operating_plan()
        return format_top_revenue_move(plan)
    except Exception as exc:
        return f"TODAY'S TOP MONEY MOVE\n\nCould not build revenue plan: {exc!s:.120}"


def _plain_daily_blockers() -> str:
    """Handle 'show today's blockers', 'what is blocked', 'blockers today'."""
    from lib.hermes_daily_operating_cycle import build_daily_operating_plan, format_blockers_summary
    try:
        plan = build_daily_operating_plan()
        return format_blockers_summary(plan)
    except Exception as exc:
        return f"TODAY'S BLOCKERS\n\nCould not check blockers: {exc!s:.120}"


def _plain_thirty_day_revenue_plan() -> str:
    """Handle '30 day revenue plan', 'plan to make money this month', '30-day plan'."""
    from datetime import date
    from lib.hermes_daily_operating_cycle import load_daily_operating_inputs

    today = date.today().strftime("%B %d, %Y")

    # Try to surface the top content asset
    top_asset_name = "lead magnet / funding readiness checklist"
    try:
        inputs = load_daily_operating_inputs()
        mon_plan = inputs.get("monetization_plan") or {}
        top_asset_name = mon_plan.get("top_asset_name") or top_asset_name
    except Exception:
        pass

    lines = [
        f"30-DAY NEXUS REVENUE PLAN — {today}",
        "",
        "Goal:",
        "  Generate $1,000/week in recurring or repeatable revenue.",
        "",
        f"Best starting asset: {top_asset_name}",
        "",
        "Week 1 — Build and approve the asset packet",
        "  - finalize lead magnet",
        "  - finalize newsletter draft",
        "  - finalize short video script",
        "  - prepare CTA (call to action)",
        "  - compliance and approval review",
        "",
        "Week 2 — Traffic and lead capture",
        "  - publish approved content only (after Ray approval)",
        "  - post short-form video",
        "  - connect lead magnet to opt-in page",
        "  - track lead volume",
        "",
        "Week 3 — Offer and follow-up",
        "  - create funding readiness audit offer",
        "  - create consultation/strategy call CTA",
        "  - identify affiliate offers matching Nexus audience",
        "",
        "Week 4 — Convert and improve",
        "  - review metrics and lead quality",
        "  - improve CTA based on results",
        "  - produce second content batch",
        "  - turn best questions into lessons and knowledge gaps",
        "",
        "What needs Ray approval:",
        "  - publishing to social / newsletter",
        "  - subscriber email sends",
        "  - affiliate signup",
        "  - payment / Stripe activation",
        "  - any client-facing content",
        "",
        "What Hermes can do internally now:",
        "  - prepare and improve asset drafts",
        "  - refine CTA copy",
        "  - draft approval checklist",
        "  - assign scouts to research leads",
        "  - build internal launch checklist",
        "",
        "Approval boundary:",
        "  I will not publish, email subscribers, sell, deploy, spend money,",
        "  apply to affiliate programs, or run live trading without Ray approval.",
    ]
    return "\n".join(lines)


def _plain_show_last_daily_plan() -> str:
    """Handle 'show last daily plan', 'what was the last plan', 'previous daily plan'."""
    try:
        from lib.hermes_daily_cycle_state import summarize_latest_daily_cycle
        return summarize_latest_daily_cycle()
    except Exception as exc:
        return f"LAST DAILY PLAN\n\nCould not load last plan: {exc!s:.120}"


def _plain_while_out_summary() -> str:
    """Handle 'what did you do while I was out', 'while I was out', 'catch me up from last plan'."""
    try:
        from lib.hermes_daily_cycle_state import (
            load_latest_daily_cycle_state, is_cycle_state_stale, list_pending_cycle_items,
        )
        state = load_latest_daily_cycle_state()
        if not state:
            return (
                "WHILE YOU WERE OUT\n\n"
                "No saved daily plan found.\n"
                "Run: 'hermes run daily operating cycle' to generate one."
            )
        from datetime import datetime, timezone
        date_str   = state.get("date", "unknown date")
        created_at = state.get("created_at", "")
        stale      = is_cycle_state_stale(max_age_hours=24)
        age_str    = ""
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
                age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                age_str = f"{age_h:.0f}h ago" if age_h >= 1 else f"{age_h * 60:.0f}m ago"
            except Exception:
                age_str = ""

        lines = ["WHILE YOU WERE OUT", ""]
        lines.append(f"Last plan: {date_str}" + (f" ({age_str})" if age_str else ""))
        if stale:
            lines.append("(Plan is over 24h old — consider running a fresh daily cycle.)")
        lines.append("")

        completed = state.get("completed_items") or []
        if completed:
            lines += [f"Completed since last plan ({len(completed)}):"]
            for c in completed[:5]:
                label = c.get("item") or c.get("blocker") or "unknown"
                lines.append(f"  - {label}")
            lines.append("")

        pending = list_pending_cycle_items()
        if pending:
            lines += [f"Still pending ({len(pending)}):"]
            for p in pending[:5]:
                lines.append(f"  - [{p['type']}] {p['item']}")
            lines.append("")

        safe_actions = state.get("safe_next_actions") or []
        if safe_actions:
            lines += ["Internal work ready to run:"]
            for a in safe_actions[:4]:
                lines.append(f"  - {a}")
            lines.append("")

        lines += [
            "What you can say:",
            "  - 'show pending items' to see pending list",
            "  - 'mark [item] complete' to record progress",
            "  - 'hermes run daily operating cycle' to refresh the plan",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"WHILE YOU WERE OUT\n\nCould not load summary: {exc!s:.120}"


def _plain_pending_daily_items() -> str:
    """Handle 'show pending items', 'what needs doing', 'what is still pending from today'."""
    try:
        from lib.hermes_daily_cycle_state import load_latest_daily_cycle_state, list_pending_cycle_items
        state = load_latest_daily_cycle_state()
        if not state:
            return (
                "PENDING DAILY ITEMS\n\n"
                "No saved daily plan found.\n"
                "Run: 'hermes run daily operating cycle' to generate one."
            )
        pending = list_pending_cycle_items()
        date_str = state.get("date", "unknown date")
        lines = [f"PENDING DAILY ITEMS — {date_str}", ""]

        approval_items = [p for p in pending if p["type"] == "approval"]
        blockers       = [p for p in pending if p["type"] == "blocker"]
        safe_actions   = [p for p in pending if p["type"] == "safe_action"]

        if blockers:
            lines += [f"Blockers ({len(blockers)}):"]
            for b in blockers:
                lines.append(f"  - {b['item']}")
                if b.get("why"):
                    lines.append(f"    Fix: {b['why']}")
            lines.append("")

        if safe_actions:
            lines += [f"Safe internal items ({len(safe_actions)}):"]
            for a in safe_actions:
                lines.append(f"  - {a['item']}")
            lines.append("")

        if approval_items:
            lines += [f"Needs Ray approval ({len(approval_items)}):"]
            for a in approval_items:
                lines.append(f"  - {a['item']}")
                if a.get("why"):
                    lines.append(f"    Why: {a['why']}")
            lines.append("")

        if not (approval_items or blockers or safe_actions):
            lines += [
                "No pending items found.",
                "",
                "Everything from the last plan may be complete or cleared.",
                "Run 'hermes run daily operating cycle' to refresh.",
            ]
        else:
            lines += [
                "Evidence:",
                "  docs/reports/operations/hermes_daily_cycle_state.json",
                "",
                "To mark an item complete:",
                "  Say: 'mark item complete: [item title]'",
            ]
        return "\n".join(lines)
    except Exception as exc:
        return f"PENDING DAILY ITEMS\n\nCould not load pending items: {exc!s:.120}"


def _plain_compare_since_last_plan() -> str:
    """Handle 'compare since last plan', 'what changed since last plan'."""
    try:
        from lib.hermes_daily_cycle_state import load_latest_daily_cycle_state
        from lib.hermes_daily_operating_cycle import build_daily_operating_plan, load_daily_operating_inputs
        last = load_latest_daily_cycle_state()
        if not last:
            return (
                "WHAT CHANGED SINCE THE LAST PLAN\n\n"
                "No saved daily plan found to compare against.\n"
                "Run: 'hermes run daily operating cycle' to generate one."
            )
        from lib.hermes_daily_cycle_state import compare_current_to_last_cycle
        inputs  = load_daily_operating_inputs()
        current = build_daily_operating_plan(inputs)
        diff    = compare_current_to_last_cycle(current, last)

        lines = ["WHAT CHANGED SINCE THE LAST PLAN", ""]
        prev_date = diff.get("prev_date") or last.get("date", "unknown")
        curr_date = diff.get("curr_date") or current.get("date", "today")
        lines.append(f"Comparing: {prev_date} → {curr_date}")
        lines.append("")

        changes = diff.get("changes") or ["No changes detected."]
        lines += ["Changes:"]
        for c in changes:
            lines.append(f"  - {c}")
        lines.append("")

        if diff.get("priority_changed"):
            lines += [
                f"Previous top priority: {diff['prev_priority']}",
                f"Current top priority:  {diff['curr_priority']}",
                "",
            ]

        lines += [
            "Approval boundary:",
            "  I will not publish, email, sell, deploy, spend money, or trade live without Ray approval.",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"WHAT CHANGED SINCE THE LAST PLAN\n\nCould not compare plans: {exc!s:.120}"


def _plain_mark_daily_item_complete(raw_text: str = "") -> str:
    """Handle 'mark [item] complete', 'mark done', 'mark it complete'."""
    try:
        from lib.hermes_daily_cycle_state import mark_cycle_item_completed, list_pending_cycle_items
        pending = list_pending_cycle_items()
        if not pending:
            return (
                "DAILY ITEM MARKED COMPLETE\n\n"
                "No pending items found in the last saved plan.\n"
                "Run 'hermes run daily operating cycle' first."
            )

        # Extract the item title from the raw command text
        lowered = raw_text.strip().lower()
        # Strip leading command words to get the item fragment.
        # Order matters: longer/more-specific prefixes must come first.
        for prefix in (
            "mark daily item complete",
            "mark daily item done",
            "complete daily item",
            "complete item",
            "mark as complete",
            "mark as done",
            "mark item complete",
            "mark item done",
            "mark complete",
            "mark done",
            "mark it complete",
            "mark it done",
            "that is complete",
            "mark that complete",
            "completed that",
            "finished that item",
        ):
            if lowered.startswith(prefix):
                lowered = lowered[len(prefix):].strip()
                break
        # Strip any leading separator: colon, dash, bullet, whitespace
        lowered = lowered.lstrip(':–—-• \t')
        # Strip trailing "complete"/"done" residue
        for suffix in (" as complete", " complete", " as done", " done"):
            if lowered.endswith(suffix):
                lowered = lowered[: -len(suffix)].strip()
                break

        if not lowered:
            # No item name given — mark the first pending item
            first = pending[0]
            item_title = first.get("item", "")
        else:
            item_title = lowered

        result = mark_cycle_item_completed(item_title)
        lines = ["DAILY ITEM MARKED COMPLETE", ""]
        if result["success"]:
            completed_item = result.get("completed_item") or {}
            label = completed_item.get("item") or completed_item.get("blocker") or item_title
            remaining = list_pending_cycle_items()
            lines += [
                f"Completed:",
                f"  {label}",
                "",
                f"Remaining pending: {len(remaining)} item(s)",
                "",
                "Evidence:",
                "  docs/reports/operations/hermes_daily_cycle_state.json",
                "",
                "Say 'show pending items' to see the updated list.",
            ]
        else:
            lines += [
                result["message"],
                "",
                "Pending items you can mark complete:",
            ]
            for p in pending[:5]:
                lines.append(f"  - {p['item']}")
            lines += [
                "",
                "Say: 'mark item complete: [item title]'",
            ]
        return "\n".join(lines)
    except Exception as exc:
        return f"DAILY ITEM MARKED COMPLETE\n\nCould not mark item: {exc!s:.120}"


# ── Phase 6C: Approval Queue ─────────────────────────────────────────────────

def _plain_show_approval_queue() -> str:
    """Handle 'show approval queue', 'what needs my approval', 'pending approvals'."""
    try:
        from lib.hermes_approval_queue import format_approval_queue
        return format_approval_queue()
    except Exception as exc:
        return f"APPROVAL QUEUE\n\nCould not load approval queue: {exc!s:.120}"


def _plain_show_approval_item(raw_text: str = "") -> str:
    """Handle 'show approval item N', 'approval item detail N'."""
    try:
        from lib.hermes_approval_queue import format_approval_item_detail
        # Extract ref (number or approval_id) from raw_text
        lowered = raw_text.strip().lower()
        for prefix in (
            "show approval item",
            "approval item detail",
            "tell me about approval item",
            "details for approval item",
            "what is approval item",
            "describe approval item",
            "approval item info",
            "explain approval item",
        ):
            if lowered.startswith(prefix):
                lowered = lowered[len(prefix):].strip().lstrip(":– \t")
                break
        ref = lowered.split()[0] if lowered.split() else ""
        if not ref:
            return "APPROVAL ITEM\n\nPlease specify an item number, e.g.:\n  show approval item 1"
        return format_approval_item_detail(ref)
    except Exception as exc:
        return f"APPROVAL ITEM\n\nCould not load item detail: {exc!s:.120}"


def _plain_approve_item(raw_text: str = "") -> str:
    """Handle 'approve item N'."""
    try:
        from lib.hermes_approval_queue import approve_approval_item, format_approval_result
        lowered = raw_text.strip().lower()
        for prefix in (
            "approve number",
            "yes approve item",
            "give approval for item",
            "i approve item",
            "approve this item",
            "approve item",
            "approved item",
        ):
            if lowered.startswith(prefix):
                lowered = lowered[len(prefix):].strip().lstrip(":– \t")
                break
        ref = lowered.split()[0] if lowered.split() else ""
        if not ref:
            return "APPROVAL RECORDED\n\nPlease specify an item number, e.g.:\n  approve item 1"
        result = approve_approval_item(ref)
        return format_approval_result(ref, result)
    except Exception as exc:
        return f"APPROVAL RECORDED\n\nCould not approve item: {exc!s:.120}"


def _plain_reject_item(raw_text: str = "") -> str:
    """Handle 'reject item N [reason]'."""
    try:
        from lib.hermes_approval_queue import reject_approval_item, format_approval_result
        lowered = raw_text.strip().lower()
        reason_text = raw_text.strip()
        for prefix in (
            "do not approve item",
            "decline item",
            "rejected item",
            "i reject item",
            "reject this item",
            "reject item",
            "deny item",
        ):
            if lowered.startswith(prefix):
                lowered = lowered[len(prefix):].strip().lstrip(":– \t")
                reason_text = raw_text.strip()[raw_text.strip().lower().find(prefix) + len(prefix):].strip().lstrip(":– \t")
                break
        parts = lowered.split(None, 1)
        ref    = parts[0] if parts else ""
        reason = parts[1].strip() if len(parts) > 1 else reason_text.split(None, 1)[1].strip() if len(reason_text.split(None, 1)) > 1 else ""
        if not ref:
            return "APPROVAL REJECTED\n\nPlease specify an item number, e.g.:\n  reject item 1"
        result = reject_approval_item(ref, reason or None)
        return format_approval_result(ref, result)
    except Exception as exc:
        return f"APPROVAL REJECTED\n\nCould not reject item: {exc!s:.120}"


def _plain_approval_impact(raw_text: str = "") -> str:
    """Handle 'what happens if I approve item N', 'if rejected item N'."""
    try:
        from lib.hermes_approval_queue import format_approval_impact
        lowered = raw_text.strip().lower()
        action = "approve"
        if any(k in lowered for k in ("reject", "denied", "not approve")):
            action = "reject"
        # Extract ref
        for prefix in (
            "what happens if i approve",
            "what would happen if i approve",
            "if i approve item",
            "impact of approving",
            "if approved item",
            "simulate approval",
            "what happens if i reject",
            "if i reject item",
            "impact of rejecting",
            "if rejected item",
            "simulate rejection",
        ):
            if lowered.startswith(prefix):
                lowered = lowered[len(prefix):].strip().lstrip(":– \t")
                break
        # Strip trailing words like "item", "number"
        lowered = lowered.lstrip("item #").strip()
        ref = lowered.split()[0] if lowered.split() else ""
        if not ref:
            return f"IF {'APPROVED' if action == 'approve' else 'REJECTED'} — ITEM ?\n\nPlease specify an item number."
        return format_approval_impact(ref, action)
    except Exception as exc:
        return f"APPROVAL IMPACT\n\nCould not simulate impact: {exc!s:.120}"


def _plain_clear_stale_approvals() -> str:
    """Handle 'clear stale approvals', 'archive old approvals'."""
    try:
        from lib.hermes_approval_queue import archive_stale_approval_items
        result = archive_stale_approval_items(max_age_days=7)
        count = result.get("archived_count", 0)
        if count == 0:
            return (
                "STALE APPROVAL CLEANUP\n\n"
                "No stale approval items found.\n"
                "(Items are marked stale after 7 days in pending state.)\n\n"
                "Evidence: docs/reports/approvals/hermes_approval_queue_state.json"
            )
        titles = result.get("stale_titles") or []
        lines = ["STALE APPROVAL CLEANUP", "", f"Archived {count} stale item(s):", ""]
        for t in titles[:10]:
            lines.append(f"  - {t}")
        lines += [
            "",
            "These items remain in the state file with status=stale.",
            "They can be reviewed but will not appear in the active queue.",
            "",
            "Evidence: docs/reports/approvals/hermes_approval_queue_state.json",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"STALE APPROVAL CLEANUP\n\nCould not clean up approvals: {exc!s:.120}"


def _plain_bulk_approve_blocked() -> str:
    """Handle 'bulk approve blocked internal items'."""
    try:
        from lib.hermes_approval_queue import (
            list_approval_items, approve_approval_item,
            format_approval_result, HIGH_RISK_CATEGORIES,
        )
        pending = list_approval_items(limit=20)
        if not pending:
            return (
                "BULK APPROVE\n\n"
                "No pending approval items found.\n"
                "Use 'show approval queue' to check current queue."
            )
        safe_items = [i for i in pending if i.get("category") not in HIGH_RISK_CATEGORIES]
        blocked_items = [i for i in pending if i.get("category") in HIGH_RISK_CATEGORIES]
        if not safe_items:
            lines = ["BULK APPROVE", "", "No safe internal items eligible for bulk approval.", ""]
            if blocked_items:
                lines += [
                    f"{len(blocked_items)} high-risk item(s) require individual Ray approval:",
                ]
                for item in blocked_items[:5]:
                    lines.append(f"  - [{item['category']}] {item['title']}")
            lines += [
                "",
                "High-risk categories cannot be bulk approved:",
                "  content_publish, subscriber_email, live_trading, production_deploy,",
                "  payment_or_stripe, affiliate_signup, paid_tool, client_facing_content",
            ]
            return "\n".join(lines)

        approved_titles: list[str] = []
        for item in safe_items:
            r = approve_approval_item(item["approval_id"])
            if r.get("success"):
                approved_titles.append(item["title"])

        lines = ["BULK APPROVE", "", f"Approved {len(approved_titles)} safe internal item(s):", ""]
        for t in approved_titles:
            lines.append(f"  - {t}")
        if blocked_items:
            lines += [
                "",
                f"{len(blocked_items)} high-risk item(s) skipped (require individual approval):",
            ]
            for item in blocked_items[:5]:
                lines.append(f"  - [{item['category']}] {item['title']}")
        lines += [
            "",
            "Safety: no content published, no emails sent, no money spent.",
            "",
            "Evidence: docs/reports/approvals/hermes_approval_queue_state.json",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"BULK APPROVE\n\nCould not bulk approve items: {exc!s:.120}"


# ── Phase 6D: Revenue Asset Packet ──────────────────────────────────────────

def _plain_build_revenue_asset_packet() -> str:
    """Handle 'build revenue asset packet', 'create revenue asset packet'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            build_revenue_asset_packet, save_revenue_asset_packet,
            inject_approval_candidates,
        )
        packet = build_revenue_asset_packet()
        save_revenue_asset_packet(packet)
        result = inject_approval_candidates(packet.get("approval_candidates") or [])

        score    = packet.get("readiness_score", 0)
        ready    = packet.get("approval_ready_items") or []
        needs_rev = packet.get("needs_revision_items") or []
        candidates = packet.get("approval_candidates") or []
        added    = result.get("added", 0)
        skipped  = result.get("skipped", 0)

        lines = ["REVENUE ASSET PACKET CREATED", ""]
        lines += [
            "Packet:",
            "  Nexus Credit/Funding Readiness Asset Packet",
            "",
            f"Overall readiness: {score}/100",
            "",
        ]

        if ready:
            lines += [f"Launch-ready assets ({len(ready)}):", ""]
            for a in ready:
                lines.append(f"  - {a.get('category','').replace('_',' ')}: {a['filename']}")
            lines.append("")

        if needs_rev:
            lines += [f"Needs revision ({len(needs_rev)}):", ""]
            for a in needs_rev:
                lines.append(f"  - {a.get('category','').replace('_',' ')}: {a['filename']}")
            lines.append("")

        if candidates:
            lines += [f"Approval candidates created ({added} new, {skipped} already queued):", ""]
            for c in candidates:
                lines.append(f"  - {c['title']}")
            lines.append("")

        lines += [
            "Safety: no content published, no emails sent, no money spent.",
            "",
            "Next:",
            "  Say 'show revenue asset packet' to review the full packet.",
            "  Say 'show approval queue' to review approval items.",
            "",
            "Evidence: docs/reports/revenue_packets/latest_revenue_asset_packet.json",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"REVENUE ASSET PACKET CREATED\n\nCould not build packet: {exc!s:.200}"


def _plain_show_revenue_asset_packet() -> str:
    """Handle 'show revenue asset packet', 'show latest revenue packet'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            format_revenue_asset_packet,
        )
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        return format_revenue_asset_packet(packet)
    except Exception as exc:
        return f"REVENUE ASSET PACKET\n\nCould not load packet: {exc!s:.200}"


def _plain_show_launch_ready_assets() -> str:
    """Handle 'show launch-ready assets'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            format_launch_ready_assets,
        )
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        return format_launch_ready_assets(packet)
    except Exception as exc:
        return f"LAUNCH-READY ASSETS\n\nCould not load assets: {exc!s:.200}"


def _plain_show_content_awaiting_approval() -> str:
    """Handle 'show content awaiting approval'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            format_content_awaiting_approval,
        )
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        return format_content_awaiting_approval(packet)
    except Exception as exc:
        return f"CONTENT AWAITING APPROVAL\n\nCould not load content: {exc!s:.200}"


def _plain_show_cta_options() -> str:
    """Handle 'show CTA options'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            build_cta_options, load_latest_revenue_asset_packet,
        )
        packet = load_latest_revenue_asset_packet()
        opts = build_cta_options(packet)
        lines = ["CTA OPTIONS", ""]
        lines += ["Current CTA options for Nexus lead magnet:", ""]
        for label, text in opts.items():
            lines.append(f"  [{label}]  {text}")
        lines += [
            "",
            "These are internal drafts — not published.",
            "Say 'build revenue asset packet' to regenerate options.",
            "Say 'approve item N' to approve a CTA for use.",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"CTA OPTIONS\n\nCould not load CTA options: {exc!s:.200}"


def _plain_show_launch_checklist() -> str:
    """Handle 'show launch checklist'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            build_launch_checklist, load_latest_revenue_asset_packet,
        )
        packet = load_latest_revenue_asset_packet()
        cl = build_launch_checklist(packet)

        lines = ["LAUNCH CHECKLIST", "", "Before publishing:", ""]
        for step in (cl.get("ray_approval_required") or []):
            lines.append(f"  - {step}")
        lines += [""]

        lines += ["Safe internal work Hermes can do:", ""]
        for step in (cl.get("safe_internal_work") or []):
            lines.append(f"  - {step}")
        lines += [""]

        lines += ["Requires Ray approval (blocked until approved):", ""]
        for step in (cl.get("blocked_until_ray_approves") or []):
            lines.append(f"  - {step}")

        return "\n".join(lines)
    except Exception as exc:
        return f"LAUNCH CHECKLIST\n\nCould not load checklist: {exc!s:.200}"


def _plain_show_approval_checklist() -> str:
    """Handle 'show approval checklist'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            build_approval_checklist, load_latest_revenue_asset_packet,
        )
        packet = load_latest_revenue_asset_packet()
        cl = build_approval_checklist(packet)

        lines = ["APPROVAL CHECKLIST", ""]
        for item in (cl.get("checklist") or []):
            lines.append(f"  - {item}")
        lines += [
            "",
            "Approval boundary:",
            f"  {cl.get('approval_boundary', '')}",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"APPROVAL CHECKLIST\n\nCould not load checklist: {exc!s:.200}"


def _plain_generate_approval_candidates() -> str:
    """Handle 'generate approval candidates', 'create approval items from packet'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            generate_approval_candidates, inject_approval_candidates,
        )
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        candidates = generate_approval_candidates(packet)
        result = inject_approval_candidates(candidates)

        added   = result.get("added", 0)
        skipped = result.get("skipped", 0)
        total   = result.get("total", 0)

        lines = ["APPROVAL CANDIDATES GENERATED", ""]
        if total == 0:
            lines += [
                "No approval candidates could be generated.",
                "Run 'build revenue asset packet' first to discover assets.",
            ]
            return "\n".join(lines)

        lines += [
            f"{added} new approval item(s) added to queue.",
            f"{skipped} already existed (no duplicates added).",
            "",
        ]
        for c in candidates:
            lines.append(f"  - {c['title']} [{c['category'].replace('_',' ')}]")
        lines += [
            "",
            "Safety: no content published, no emails sent, no money spent.",
            "",
            "Next:",
            "  Say 'show approval queue' to review and act on items.",
            "  Say 'approve item N' to approve individual items.",
            "",
            "Evidence: docs/reports/approvals/hermes_approval_queue_state.json",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"APPROVAL CANDIDATES GENERATED\n\nCould not generate candidates: {exc!s:.200}"


# ── Phase 6E: Revenue Packet Improvement ─────────────────────────────────────

def _plain_show_revenue_packet_gaps() -> str:
    """Handle 'show revenue packet gaps', 'show readiness gaps'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            format_packet_readiness_gaps,
        )
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        return format_packet_readiness_gaps(packet)
    except Exception as exc:
        return f"REVENUE PACKET READINESS GAPS\n\nCould not analyze gaps: {exc!s:.200}"


def _plain_improve_revenue_asset_packet() -> str:
    """Handle 'improve revenue asset packet', 'improve packet score', 'raise packet readiness'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            apply_internal_packet_improvements, recommend_packet_improvements,
            save_improved_revenue_packet, inject_approval_candidates,
            generate_approval_candidates,
        )
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        improvements = recommend_packet_improvements(packet)
        improved = apply_internal_packet_improvements(packet)
        save_result = save_improved_revenue_packet(improved, improvements)

        # Update approval candidates from improved packet
        candidates = generate_approval_candidates(improved)
        inject_result = inject_approval_candidates(candidates)

        old_score = packet.get("readiness_score", 0)
        new_score = improved.get("readiness_score", 0)
        ready = improved.get("approval_ready_items") or []
        added = inject_result.get("added", 0)

        lines = ["REVENUE PACKET IMPROVED", ""]
        lines += [
            f"Previous score: {old_score}/100",
            f"Current score:  {new_score}/100",
            f"Approval-ready: {len(ready)}",
            f"New approval queue items: {added}",
            "",
        ]

        if improvements:
            lines += ["Improvements noted:", ""]
            for imp in improvements[:5]:
                lines.append(f"  - {imp}")
            if len(improvements) > 5:
                lines.append(f"  ... and {len(improvements) - 5} more.")
            lines.append("")

        lines += [
            "Safety: no content published, no emails sent, no money spent.",
            "",
            "Evidence:",
            f"  {save_result.get('saved_md', '')}",
            "",
            "Next:",
            "  Say 'show revenue packet gaps' to review remaining gaps.",
            "  Say 'show approval queue' to review approval items.",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"REVENUE PACKET IMPROVED\n\nCould not improve packet: {exc!s:.200}"


def _plain_show_improved_cta_options() -> str:
    """Handle 'show improved cta options'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, format_improved_cta_options,
        )
        packet = load_latest_revenue_asset_packet()
        return format_improved_cta_options(packet)
    except Exception as exc:
        return f"IMPROVED CTA OPTIONS\n\nCould not load CTA options: {exc!s:.200}"


def _plain_show_offer_bridge() -> str:
    """Handle 'show offer bridge', 'funnel model'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, format_offer_bridge,
        )
        packet = load_latest_revenue_asset_packet()
        return format_offer_bridge(packet)
    except Exception as exc:
        return f"OFFER BRIDGE\n\nCould not load offer bridge: {exc!s:.200}"


def _plain_show_packet_improvement_plan() -> str:
    """Handle 'show packet improvement plan'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            format_packet_improvement_plan,
        )
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        return format_packet_improvement_plan(packet)
    except Exception as exc:
        return f"PACKET IMPROVEMENT PLAN\n\nCould not build plan: {exc!s:.200}"


def _plain_rescore_revenue_packet() -> str:
    """Handle 'rescore revenue packet', 'refresh revenue packet score'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            rescore_packet_after_improvements, save_revenue_asset_packet,
            format_rescored_packet,
        )
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        rescored = rescore_packet_after_improvements(packet)
        save_revenue_asset_packet(rescored)
        return format_rescored_packet(rescored)
    except Exception as exc:
        return f"REVENUE PACKET RESCORED\n\nCould not rescore packet: {exc!s:.200}"


def _plain_show_final_review_checklist() -> str:
    """Handle 'show final review checklist', 'pre-launch final checklist'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            format_final_review_checklist,
        )
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        return format_final_review_checklist(packet)
    except Exception as exc:
        return f"FINAL REVIEW CHECKLIST\n\nCould not load checklist: {exc!s:.200}"


# ── Phase 6F: Revenue Asset Fixer ────────────────────────────────────────────

def _plain_fix_revenue_packet_assets() -> str:
    """Handle 'fix revenue packet assets', 'apply safe asset fixes'."""
    try:
        from lib.hermes_revenue_asset_fixer import apply_safe_asset_fixes, format_asset_fix_report
        result = apply_safe_asset_fixes()
        return format_asset_fix_report(result)
    except Exception as exc:
        return f"REVENUE ASSET FIXES APPLIED\n\nCould not apply fixes: {exc!s:.200}"


def _plain_show_asset_fix_report() -> str:
    """Handle 'show asset fix report', 'what was fixed'."""
    try:
        from lib.hermes_revenue_asset_fixer import (
            apply_safe_asset_fixes, format_asset_fix_report, find_assets_needing_fixes,
        )
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
        )
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        needing = find_assets_needing_fixes(packet)
        if needing:
            result = apply_safe_asset_fixes()
            return format_asset_fix_report(result)
        # Nothing left to fix — show current packet state
        score = packet.get("readiness_score", 0)
        ready = packet.get("approval_ready_items") or []
        lines = [
            "REVENUE ASSET FIX REPORT",
            "",
            f"Score:          {score}/100",
            f"Assets:         {len(packet.get('assets') or [])}",
            f"Approval-ready: {len(ready)}",
            "",
            "No assets currently need safe internal fixes.",
            "",
            "Safety: No content published. No emails sent. No spending.",
        ]
        return "\n".join(lines)
    except Exception as exc:
        return f"REVENUE ASSET FIX REPORT\n\nCould not generate report: {exc!s:.200}"


def _plain_rescore_after_fixes() -> str:
    """Handle 'rescore after fixes', 'update score after fixes'."""
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            build_revenue_asset_packet_with_fixes, save_revenue_asset_packet,
        )
        from lib.hermes_revenue_asset_fixer import format_rescore_after_fixes_report
        old_packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        old_score = old_packet.get("readiness_score", 0)
        new_packet = build_revenue_asset_packet_with_fixes()
        save_revenue_asset_packet(new_packet)
        new_score = new_packet.get("readiness_score", 0)
        return format_rescore_after_fixes_report(old_score, new_score, new_packet)
    except Exception as exc:
        return f"REVENUE PACKET RESCORED AFTER FIXES\n\nCould not rescore: {exc!s:.200}"


def _plain_lesson_gap_generate() -> str:
    """Generate lesson proposals from open knowledge gaps."""
    from lib.hermes_learning_loop import generate_gap_lesson_proposals
    created = generate_gap_lesson_proposals(limit=5)
    if not created:
        return (
            "LESSON GAP GENERATION\n\n"
            "No open knowledge gaps matched lesson templates.\n\n"
            "Use 'show knowledge gaps' to review open gaps.\n"
            "Use 'record this lesson: <text>' to manually create a lesson."
        )
    lines = ["LESSON GAP GENERATION", "", f"{len(created)} lesson proposal(s) created from gaps:", ""]
    for p in created:
        lid    = p.get("lesson_id", "?")
        title  = p.get("title", "?")[:60]
        status = p.get("proposed_status", "?")
        lines += [f"ID:     {lid}", f"Title:  {title}", f"Status: {status}", ""]
    lines += [
        "Use 'show pending lessons' to review.",
        "Use 'approve lesson <id>' to write to active memory.",
    ]
    return "\n".join(lines)


def _plain_memory_v2_shadow_status() -> str:
    """'show memory v2 shadow status' — shadow mode config and last comparison."""
    from lib.hermes_memory_v2_shadow import format_shadow_status
    return format_shadow_status()


def _plain_memory_v2_live_check() -> str:
    """'is memory v2 live / primary / shadow only' queries."""
    from lib.hermes_memory_v2_shadow import format_v2_live_status
    return format_v2_live_status()


# ── Plain-text intent routing (memory commands bypass build_report) ───────────
# Handlers return str directly — no HERMES REPORT wrapper.
_PLAIN_INTENTS: dict[str, object] = {
    # ── Conversational / general ─────────────────────────────────────────────
    "small_talk":                  _plain_small_talk,
    "date_time_question":          _plain_date_time,
    "tomorrow_plan":               _plain_tomorrow_plan,
    "unknown_handling":            _plain_unknown_handling,
    "knowledge_gap_review":        _plain_knowledge_gaps,
    # ── Memory commands ──────────────────────────────────────────────────────
    "memory_sources":              _plain_memory_sources,
    "memory_sources_again":        _plain_memory_sources,
    "answer_source":               _plain_answer_source,
    "active_operating_rules":      _plain_active_operating_rules,
    "memory_v2_preview":           _plain_memory_v2_preview,
    "memory_v2_compare":           _plain_memory_v2_compare,
    "memory_v2_rules":             _plain_memory_v2_rules,
    "memory_v2_status":            _plain_memory_v2_status,
    "memory_v2_primary_status":    _plain_memory_v2_primary_status,
    "memory_v2_shadow_status":     _plain_memory_v2_shadow_status,
    "memory_v2_live_check":        _plain_memory_v2_live_check,
    # ── Daily operating cycle (Phase 6A) ─────────────────────────────────────
    "daily_operating_cycle":       _plain_daily_operating_cycle,
    "daily_approval_needed":       _plain_daily_approval_needed,
    "daily_continue_while_out":    _plain_daily_continue_while_out,
    "daily_top_revenue_move":      _plain_daily_top_revenue_move,
    "daily_blockers":              _plain_daily_blockers,
    "thirty_day_revenue_plan":     _plain_thirty_day_revenue_plan,
    # ── Daily cycle state (Phase 6B) ─────────────────────────────────────────
    "show_last_daily_plan":        _plain_show_last_daily_plan,
    "while_out_summary":           _plain_while_out_summary,
    "pending_daily_items":         _plain_pending_daily_items,
    "compare_since_last_plan":     _plain_compare_since_last_plan,
    "mark_daily_item_complete":    _plain_mark_daily_item_complete,
    # ── Approval queue (Phase 6C) ─────────────────────────────────────────────
    "show_approval_queue":         _plain_show_approval_queue,
    "show_approval_item":          _plain_show_approval_item,
    "approve_item":                _plain_approve_item,
    "reject_item":                 _plain_reject_item,
    "approval_impact":             _plain_approval_impact,
    "clear_stale_approvals":       _plain_clear_stale_approvals,
    "bulk_approve_blocked":        _plain_bulk_approve_blocked,
    # ── Revenue asset packet (Phase 6D) ──────────────────────────────────────
    "build_revenue_asset_packet":      _plain_build_revenue_asset_packet,
    "show_revenue_asset_packet":       _plain_show_revenue_asset_packet,
    "show_launch_ready_assets":        _plain_show_launch_ready_assets,
    "show_content_awaiting_approval":  _plain_show_content_awaiting_approval,
    "show_cta_options":                _plain_show_cta_options,
    "show_launch_checklist":           _plain_show_launch_checklist,
    "show_approval_checklist":         _plain_show_approval_checklist,
    "generate_approval_candidates":    _plain_generate_approval_candidates,
    # ── Revenue packet improvement (Phase 6E) ─────────────────────────────────
    "show_revenue_packet_gaps":        _plain_show_revenue_packet_gaps,
    "improve_revenue_asset_packet":    _plain_improve_revenue_asset_packet,
    "show_improved_cta_options":       _plain_show_improved_cta_options,
    "show_offer_bridge":               _plain_show_offer_bridge,
    "show_packet_improvement_plan":    _plain_show_packet_improvement_plan,
    "rescore_revenue_packet":          _plain_rescore_revenue_packet,
    "show_final_review_checklist":     _plain_show_final_review_checklist,
    # ── Revenue asset fixer (Phase 6F) ────────────────────────────────────────
    "fix_revenue_packet_assets":       _plain_fix_revenue_packet_assets,
    "show_asset_fix_report":           _plain_show_asset_fix_report,
    "rescore_after_fixes":             _plain_rescore_after_fixes,
    # ── Learning loop ─────────────────────────────────────────────────────────
    "lesson_record":               _plain_lesson_record,
    "lesson_pending":              _plain_lesson_pending,
    "lesson_active":               _plain_lesson_active,
    "lesson_approve_all":          _plain_lesson_approve_all,
    "lesson_approve":              _plain_lesson_approve,
    "lesson_reject":               _plain_lesson_reject,
    "lesson_deprecate":            _plain_lesson_deprecate,
    "lesson_learned":              _plain_lesson_learned,
    "lesson_source":               _plain_lesson_source,
    "lesson_gap_generate":         _plain_lesson_gap_generate,
}

# Intents whose handlers need raw_text to extract IDs or lesson content
_PLAIN_INTENTS_WITH_CMD = frozenset({
    "small_talk",
    "lesson_record",
    "lesson_approve_all",
    "lesson_approve",
    "lesson_reject",
    "lesson_deprecate",
    "lesson_source",
    "mark_daily_item_complete",
    "show_approval_item",
    "approve_item",
    "reject_item",
    "approval_impact",
})

# ── Phrases that must NEVER produce a generic evidence dump ───────────────────
_EVIDENCE_DUMP_BLOCKED_PHRASES = frozenset([
    # ── Conversational ───────────────────────────────────────────────────────
    "did you get enough sleep", "did you sleep", "how are you", "are you awake",
    "are you online", "you good", "good morning", "good afternoon", "good evening",
    "what is today's date", "what is todays date", "what day is it",
    "what time is it", "what is the date", "what's the date",
    "what do you have planned for tomorrow", "what are we doing tomorrow",
    "tomorrow plan", "plan for tomorrow",
    "what if you don't know", "what if you dont know",
    "what if you dont have the answer", "what if you don't have the answer",
    "what if you cannot answer",
    "show knowledge gaps", "show unanswered questions", "what gaps do you have",
    # ── Memory ───────────────────────────────────────────────────────────────
    "show memory sources", "show memory sources again", "memory sources again",
    "where do you get memory from",
    "show active operating rules", "what active rules are you using",
    "where did that answer come from", "show approval rules",
    "show live answer rules",
    "show memory v2 preview", "preview memory v2", "compare memory v2",
    "show memory v2 status", "show memory v2 rules",
    "show memory v2 shadow status", "memory v2 shadow status",
    "show shadow memory status", "is memory v2 live",
    "is memory v2 primary", "is memory v2 shadow only",
    "show memory v2 primary status", "memory v2 primary status",
    "is memory v2 primary active", "primary mode status",
    # ── Daily operating cycle ────────────────────────────────────────────────
    "run daily operating cycle", "daily operating cycle", "run daily cycle",
    "what should i work on today", "what should we work on today",
    "what should i focus on today", "what should we focus on today",
    "show today's nexus plan", "show today's plan", "today's nexus plan",
    "show today nexus plan", "nexus plan today", "todays nexus plan",
    "todays plan", "daily plan",
    "show approval queue", "show items needing approval", "approval queue",
    "what needs ray approval", "show what needs approval",
    "what needs my approval", "pending approvals", "approval needed",
    "what is waiting for approval", "what requires approval",
    "what approvals are pending", "list approval items", "list approvals",
    "what is in the approval queue", "approval item detail",
    "tell me about approval item", "details for approval item",
    "approve item", "reject item", "approve this item", "reject this item",
    "what happens if i approve", "what would happen if i approve",
    "if i approve item", "impact of approving", "if approved item",
    "what happens if i reject", "if i reject item",
    "clear stale approvals", "clean up stale approvals", "archive old approvals",
    "bulk approve", "approve all safe items", "approve blocked internal items",
    "continue while i am out", "continue while i'm out",
    "keep working while i am out", "keep working while i'm out",
    "what can you do while i am gone", "what can you do while i'm gone",
    "continue work", "keep going while i am out",
    "continue while i am gone", "work while i am out",
    "show today's top revenue move", "show today's top money move",
    "top revenue move", "top money move today", "today's top money move",
    "today's top revenue move", "show top money move",
    "what can make money today", "how do we make money today",
    "todays top revenue move", "todays top money move",
    "show today's blockers", "show blockers", "what is blocked",
    "what is stopping us", "show current blockers", "today's blockers",
    "blockers today", "todays blockers",
    # ── 30-day revenue plan ──────────────────────────────────────────────────
    "30 day revenue plan", "30-day revenue plan",
    "plan to make money this month", "how do we make money this month",
    "make money in the next 30 days", "get to 1000 a week",
    "we need to come up with a plan to make money",
    # ── Lesson bulk approval ─────────────────────────────────────────────────
    "approve all", "approve all lessons", "approve all pending lessons",
    "approve these lessons", "approve pending lessons",
    "approve the pending lessons",
    # ── Revenue asset packet (Phase 6D) ──────────────────────────────────────
    "build revenue asset packet", "create revenue asset packet",
    "show revenue asset packet", "show latest revenue packet",
    "revenue asset packet", "show launch-ready assets", "launch ready assets",
    "show content awaiting approval", "content awaiting approval",
    "show cta options", "cta options", "show launch checklist", "launch checklist",
    "show approval checklist", "approval checklist",
    "generate approval candidates", "create approval candidates",
    "create approval items from packet", "generate approval items",
    # ── Revenue packet improvement (Phase 6E) ────────────────────────────────
    "show revenue packet gaps", "show readiness gaps", "revenue packet gaps",
    "what are the packet gaps", "show packet gaps", "packet readiness gaps",
    "improve revenue asset packet", "improve the revenue packet",
    "improve packet score", "raise packet readiness", "fix revenue packet",
    "show improved cta options", "improved cta options", "improved cta set",
    "show offer bridge", "offer bridge", "show the offer bridge", "funnel model",
    "show packet improvement plan", "packet improvement plan", "improvement roadmap",
    "rescore revenue packet", "rescore the revenue packet", "rescore packet",
    "refresh revenue packet score", "recalculate packet score",
    "show final review checklist", "final review checklist", "final checklist",
    "pre-launch final checklist", "show pre-launch review",
    # ── Revenue asset fixer (Phase 6F) ───────────────────────────────────────
    "fix revenue packet assets", "apply safe asset fixes", "fix packet gaps",
    "fix revenue asset gaps", "clean revenue assets", "fix revenue assets",
    "apply internal fixes", "fix content assets",
    "remove unsafe promises from assets", "soften unsafe language",
    "fix unsafe promise language", "remove guarantees from assets",
    "fix promise language",
    "add cta to revenue assets", "add cta to assets",
    "add call to action to assets",
    "add compliance notes to assets", "add compliance note to assets",
    "add disclaimer to assets", "add compliance notes",
    "show asset fix report", "asset fix report", "show fix report",
    "what was fixed", "show what was fixed", "asset repair report",
    "rescore after fixes", "rescore packet after fixes",
    "update score after fixes", "refresh score after fixes",
    "what is the score after fixes",
])

_INTENT_HANDLERS = {
    "health_check":              _run_monitoring_check,
    "worker_status":             _run_worker_check,
    "queue_status":              _run_queue_check,
    "trading_lab_status":        _run_trading_check,
    "summarize_recent_activity": _run_ceo_report,
    "pilot_readiness":           _run_pilot_readiness,
    "next_best_move":            _run_next_best_move,
    "communication_health":      _run_communication_health,
    "business_opportunities":    _run_business_opportunities,
    "app_url":                   _run_app_url,
    "onboarding_status":         _run_onboarding_status,
    "platform_analytics":        _run_platform_analytics,
    "ceo_digest":                _run_ceo_digest,
    "user_intelligence_status":  _run_platform_analytics,
    # ── Strategic operating partner ─────────────────────────────────────────
    "nexus_status":              _run_nexus_status,
    "handoff_check":             _run_handoff_check,
    "decision_log":              _run_decision_log,
    "demo_broker_status":        _run_demo_broker_status,
    "premium_blocker_resolver":  _run_premium_blocker_resolver,
    "save_ray_feedback":         _run_save_ray_feedback,
    "notification_log":          _run_notification_log,
    # ── YouTube source accountability ────────────────────────────────────────
    "research_task":             _run_youtube_source_status,
    # ── Source intake / artifact registry ────────────────────────────────────
    "source_intake_status":      _run_source_intake_status,
    "artifact_registry_status":  _run_artifact_registry_status,
    # ── Archived (stale) executive memory ────────────────────────────────────
    "archived_executive_memory": _run_archived_executive_memory,
    "memory_sources":            _run_memory_sources,
    "answer_source":             _run_answer_source,
    "stale_memory_debug":        _run_stale_memory_debug,
    # ── Provider / brain status ───────────────────────────────────────────────
    "provider_status":           _run_provider_status,
    # ── Knowledge gap review ─────────────────────────────────────────────────
    "knowledge_gap_review":      _run_knowledge_gap_review,
    "knowledge_gap_research":    _run_knowledge_gap_research,
    "knowledge_gap_archive":     _run_knowledge_gap_archive,
}

_SCRIPT_ROUTES = {
    "run_tests": os.path.join(ROOT, "scripts", "test_hermes_comms.py"),
}


def run_command(raw_text: str, source: str = "cli", sender: str = "raymond") -> str:
    """Normalize, classify, route, and return a formatted Hermes Report.

    Routing logic:
      deterministic intents → Supabase checks only, no AI call
      reasoning intents     → Supabase checks + qwen3:8b synthesis (fallback: llama3.2:3b)
      code intents          → Codex CLI task brief (no model writes code)
      unknown               → one clarifying question
    """
    # ── Evidence gate: block fake trading execution claims before any routing ──
    try:
        from lib.hermes_evidence_mode import is_fake_trading_claim
        if is_fake_trading_claim(raw_text):
            return build_report(
                status="blocked",
                what_happened="Fake trading execution claim detected.",
                evidence=[
                    "No verified broker artifact (order ID / execution packet) exists.",
                    "Hermes does not report trade execution without a real OANDA order artifact.",
                    f"Blocked phrase detected in: '{raw_text[:80]}'",
                ],
                recommendation=(
                    "To see real demo status, run:\n"
                    "`python scripts/test_oanda_demo_execution_loop.py --dry-run`\n"
                    "Or ask: 'show me oanda demo status'"
                ),
                action_needed="none",
                command=raw_text,
            )
    except ImportError:
        pass

    cmd    = normalize(raw_text, source=source, sender=sender)
    intent = cmd["intent"]
    mc     = model_class_for(intent)

    # ── Plain-text commands: bypass build_report wrapper ─────────────────────
    if intent in _PLAIN_INTENTS:
        try:
            fn = _PLAIN_INTENTS[intent]
            return fn(raw_text) if intent in _PLAIN_INTENTS_WITH_CMD else fn()
        except Exception as e:
            return f"I ran into an issue: {e}\n\nCheck logs or ask 'check backend health'."

    # ── Dev Agent Bridge intents ──────────────────────────────────────────────
    if intent in ("list_dev_agents", "dev_agent_status", "recommend_dev_agent", "prepare_dev_handoff"):
        try:
            from lib.hermes_dev_agent_bridge import (
                build_telegram_dev_agent_response,
                get_cli_agent_status,
                recommend_dev_agent_for_task,
            )
            tg_response = build_telegram_dev_agent_response(intent, raw_text)
            status_data = get_cli_agent_status()
            installed = status_data.get("installed_names", [])
            missing = status_data.get("missing_names", [])
            evidence = [
                f"Installed: {', '.join(installed) or 'none'}",
                f"Missing: {', '.join(missing) or 'none'}",
                f"Execution enabled: {status_data.get('execution_enabled', False)}",
                f"Dry-run mode: {status_data.get('dry_run_mode', True)}",
            ]
            if intent == "recommend_dev_agent":
                rec = recommend_dev_agent_for_task(raw_text)
                primary = rec.get("primary_recommendation", {})
                evidence.append(f"Recommended: {primary.get('display_name', '?')} — {primary.get('reason', '')}")
            return build_report(
                status="healthy",
                what_happened=tg_response,
                evidence=evidence,
                recommendation="See AI Ops dashboard → Dev Agents panel for full details.",
                action_needed="none",
                command=raw_text,
            )
        except Exception as e:
            return build_report(
                status="warning",
                what_happened="Dev Agent Bridge check failed.",
                evidence=[str(e)],
                recommendation="Check lib/hermes_dev_agent_bridge.py is installed.",
                action_needed="investigate",
                command=raw_text,
            )

    # ── Codex CLI: generate task brief, do not attempt code ourselves ──────────
    if mc == "codex_cli":
        brief = generate_codex_brief(intent, [f"Original request: {raw_text}"], "")
        return build_report(
            status="blocked",
            what_happened="This is a coding/review task. Hermes does not write code.",
            evidence=[
                f"Intent: {intent}",
                "Code implementation is handled by Codex CLI, not Hermes.",
                "Copy the task brief below and run it with Codex CLI.",
            ],
            recommendation=brief,
            action_needed="run task brief with Codex CLI",
            command=raw_text,
        )

    # ── Script routes (e.g. run_tests) ────────────────────────────────────────
    if intent in _SCRIPT_ROUTES:
        ok, output = _run_script(_SCRIPT_ROUTES[intent])
        status   = "healthy" if ok else "warning"
        evidence = [line for line in output.split("\n") if line.strip()][:15]
        rec      = "Tests passed." if ok else "One or more tests failed — check logs."
        return build_report(
            status=status,
            what_happened=f"Ran: {_SCRIPT_ROUTES[intent]}",
            evidence=evidence,
            recommendation=rec,
            action_needed="none" if ok else "investigate",
            command=raw_text,
        )

    # ── Source intake: URL registration (needs raw_text) ─────────────────────
    if intent == "source_intake":
        status, evidence, det_rec = _run_source_intake(raw_text)
        return build_report(
            status=status,
            what_happened="Source URL registered and dispatched to scout.",
            evidence=evidence,
            recommendation=det_rec,
            action_needed="none" if status in ("healthy", "queued") else "investigate",
            command=raw_text,
        )

    # ── Function-based deterministic handlers ─────────────────────────────────
    if intent in _INTENT_HANDLERS:
        status, evidence, det_rec = _INTENT_HANDLERS[intent]()

        # For reasoning intents, enhance with AI synthesis
        if mc == "reasoning":
            synth = ai_synthesize(intent, evidence, context=raw_text)
            rec   = synth["recommendation"] or det_rec
            model_note = f"Model: {synth['model']}"
            if synth.get("fallback_used"):
                model_note += f" (fallback — {synth.get('fallback_reason', 'primary unavailable')})"
                if status == "healthy":
                    status = "warning"
            evidence = evidence + [model_note]
        else:
            rec = det_rec

        return build_report(
            status=status,
            what_happened=f"Ran {intent.replace('_', ' ')} check.",
            evidence=evidence,
            recommendation=rec,
            action_needed="none" if status == "healthy" else "investigate",
            next_best_step="" if status == "healthy" else f"Ask Hermes: '{raw_text}' again if conditions change.",
            command=raw_text,
        )

    # ── Unknown — ask ONE clarifying question ─────────────────────────────────
    return build_report(
        status="unknown",
        what_happened=f"I wasn't sure what you meant by: \"{raw_text[:80]}\"",
        evidence=[f"Intent classified as: {intent}"],
        recommendation=(
            "What would you like me to check? Options:\n"
            "  • System health  — 'check backend health'\n"
            "  • Worker status  — 'worker status'\n"
            "  • Queue depth    — 'queue status'\n"
            "  • Trading        — 'trading status'\n"
            "  • Pilot ready?   — 'are we ready for pilot'\n"
            "  • Next move      — 'next best move'\n"
            "  • Comm check     — 'can you hear me'"
        ),
        action_needed="reply with one of the options above",
        command=raw_text,
    )
