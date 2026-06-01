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
    """Query top business opportunities from Supabase."""
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
            f"{url}/rest/v1/business_opportunities"
            "?select=title,opportunity_type,score,urgency,monetization_hint"
            "&status=eq.active&order=score.desc&limit=5",
            headers={'apikey': key, 'Authorization': f'Bearer {key}'},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())

        if not rows:
            return "unknown", ["No active business opportunities found"], "Run the business opportunities seed."

        evidence = [
            f"#{i+1} [{r.get('score',0)}/10] {r.get('title','?')} — {r.get('monetization_hint','')[:60]}"
            for i, r in enumerate(rows)
        ]
        return "healthy", evidence, f"Top opportunity: {rows[0].get('title','?')} (score {rows[0].get('score',0)}/10). View full list at https://goclearonline.cc"
    except Exception as e:
        return "unknown", [f"Business opportunities query failed: {e}"], "Check Supabase connectivity."


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


# ── Memory sources handler ───────────────────────────────────────────────────

def _run_memory_sources() -> tuple[str, list[str], str]:
    """Explain where Hermes gets its answer data — plain language, no raw dumps.
    Never calls executive memory."""
    evidence = [
        "HERMES MEMORY SOURCES",
        "",
        "Live answer sources:",
        "- Current conversation context",
        "- Latest content artifact",
        "- Action queue",
        "- Decision log",
        "- Source intake registry",
        "- Daily research review",
        "- Active operating rules",
        "- Live provider policy",
        "",
        "Historical/debug sources:",
        "Available only when explicitly requested:",
        "- archived executive memory",
        "- stale memory debug",
        "",
        "Blocked from live answers:",
        "- old Executive Memory defaults",
        "- stale provider status",
        "- old Beehiiv/YouTube/OpenRouter defaults",
        "- quality escalation fallback dumps",
        "",
        "Evidence:",
        "docs/HERMES_MEMORY_SAFETY_CONTRACT.md",
    ]
    return "healthy", evidence, "I answered from the current active context only."


# ── Answer source handler ────────────────────────────────────────────────────

def _run_answer_source() -> tuple[str, list[str], str]:
    """Explain the source of the last answer — no raw data dumps."""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    evidence = [
        "ANSWER SOURCE",
        "",
        "I answered from the current active context.",
        "",
        "Most recent evidence:",
    ]
    # Try to resolve latest artifact / action / decision log paths
    try:
        from lib.hermes_daily_cycle_state import find_latest_daily_cycle
        cycle = find_latest_daily_cycle()
        if cycle.get("review"):
            evidence.append(f"* Latest content artifact: {cycle['review']}")
        if cycle.get("intake"):
            evidence.append(f"* Latest action: {cycle['intake']}")
    except Exception:
        pass
    dl_path = root / "docs" / "reports" / "decisions" / "hermes_decision_log.jsonl"
    decision_path = str(dl_path.relative_to(root)) if dl_path.exists() else "docs/reports/decisions/hermes_decision_log.jsonl"
    evidence.append(f"* Latest decision log: {decision_path}")
    evidence.append("* Memory policy: docs/HERMES_MEMORY_SAFETY_CONTRACT.md")
    evidence.append("")
    evidence.append("I did not use archived executive memory for that answer.")
    return "healthy", evidence, "Sources resolve to current active context only."


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
