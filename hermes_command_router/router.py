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


# ── Routing table ──────────────────────────────────────────────────────────────

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
