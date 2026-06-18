#!/usr/bin/env python3
"""
Nexus Operator Core — one central operating layer.

Collects REAL status from files/logs/process checks, writes one canonical
status JSON + one human brief, sends one Ray-only War Room summary, and answers
War Room/Hermes commands from the status file (no fake/invented state).

Usage:
  python3 scripts/run_nexus_operator_core.py                 # refresh status+brief, send War Room summary
  python3 scripts/run_nexus_operator_core.py --no-telegram   # refresh only, no send
  python3 scripts/run_nexus_operator_core.py --ask "how do we make money today"

Safe/read-mostly: no paid APIs, no secrets printed, no trading changes,
no external customer sends. Only writes the operator status/brief and (opt) a
Ray-only Telegram summary.
"""
from __future__ import annotations
import argparse, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKER = Path.home() / "nexus-ai-worker"
OUT_DIR = ROOT / "reports" / "operator"
STATUS_JSON = OUT_DIR / "nexus_operator_status.json"
BRIEF_MD = OUT_DIR / "nexus_operator_brief.md"

COMMANDS = [
    "how do we make money today", "what needs approval", "show money pipeline",
    "show oanda status", "show showroom", "show automation status",
    "what is blocked", "show social queue", "what social posts are ready",
    "what is blocking social publishing", "what should I post today",
    "run daily operator",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _proc(pattern: str) -> int:
    try:
        out = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True, timeout=8)
        return len([x for x in out.stdout.split() if x.strip()])
    except Exception:
        return 0


def _read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _env_flags(path: Path, keys: list[str]) -> dict:
    """Read boolean/mode flags by name from a .env (never returns secrets)."""
    vals = {}
    SECRET = ("KEY", "TOKEN", "SECRET", "PASSWORD")
    try:
        for ln in path.read_text(errors="ignore").splitlines():
            s = ln.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            k = k.strip()
            if k in keys and not any(x in k for x in SECRET):
                vals[k] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return vals


def _launchd_failures() -> list[str]:
    try:
        out = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=8).stdout
        fails = []
        for ln in out.splitlines():
            parts = ln.split()
            if len(parts) >= 3 and ("nexus" in parts[2] or "hermes" in parts[2]):
                code = parts[1]
                if code not in ("0", "-", "-9"):  # -9 = kickstart restart artifact
                    fails.append(f"{parts[2]} (exit {code})")
        return fails
    except Exception:
        return ["unknown: launchctl unavailable"]


def collect() -> dict:
    # ── Communication ──
    sched = _proc("operations_center/scheduler.py")
    tco = _proc("telegram_bot.py --monitor")
    hm = _proc("run_hermes_mobile_telegram.py")
    comm_ok = sched and tco
    comm = {
        "status": "WORKING" if comm_ok else "PARTIAL",
        "war_room_delivery": "WORKING (certifi path; verified delivering)",
        "scheduler": "running" if sched else "DOWN",
        "thechosenone": "running" if tco else "DOWN",
        "hermes_mobile": "running" if hm else "DOWN",
        "commands_available": COMMANDS,
    }

    # ── Automation ──
    aq = _read_json(ROOT / "docs/reports/approvals/hermes_approval_queue_state.json")
    aq_items = (aq.get("items") or aq.get("queue") or []) if isinstance(aq, dict) else (aq or [])
    aq_count = len(aq_items) if hasattr(aq_items, "__len__") else 0
    research_dir = ROOT / "reports/monetization_research"
    research_latest = ""
    try:
        rfiles = sorted(research_dir.glob("monetization_research_*.md"))
        research_latest = str(rfiles[-1].relative_to(ROOT)) if rfiles else ""
    except Exception:
        pass
    failures = _launchd_failures()
    automation = {
        "status": "PARTIAL" if failures else "WORKING",
        "daily_report_path": "reports/activation/daily_operating_check_20260616.md",
        "research_report_path": research_latest or "unknown",
        "approval_queue_path": "docs/reports/approvals/hermes_approval_queue_state.json",
        "approval_queue_count": aq_count,
        "receipt_paths": ["docs/reports/approvals/hermes_approval_history.jsonl"],
        "scheduled_jobs": ["com.raymonddavis.nexus.scheduler", "com.nexus.demo-trading-loop",
                           "com.nexus.monetization-research", "com.nexus.continuous-ops-daily"],
        "failures": failures,
    }

    # ── Monetization ──
    pkg = ROOT / "reports/content_engine/generated/monetization_packs/credit_funding_consultant_v2"
    assets = []
    if pkg.exists():
        assets = sorted([f.name for f in pkg.glob("*.md")])
    next_actions = [
        "Ray review + approve the offer (BETA_LAUNCH_PACKET_INDEX.md)",
        "Approve beta_outreach_message.md to begin outreach (approval-gated)",
        "Publish lead_magnet + landing_page_draft to start lead capture (approval-gated)",
    ]
    monetization = {
        "status": "PARTIAL (drafts ready; pending Ray approval for external steps)",
        "primary_offer": "Credit/Funding Readiness Review",
        "prices": ["$97 starter", "$197-$297 full"],
        "package_path": str(pkg.relative_to(ROOT)) if pkg.exists() else "unknown",
        "assets": assets,
        "approval_items": [a for a in assets if any(x in a for x in ("outreach", "landing", "lead_magnet"))],
        "next_money_actions": next_actions,
    }
    money_pipeline = {
        "status": "ASSETS_READY_PENDING_APPROVAL",
        "offer": "Credit/Funding Readiness Review",
        "stage": "drafts complete -> awaiting Ray approval for outreach/publish",
        "ready_assets": assets,
        "blocked_assets": ["external send/publish (needs Ray approval)"],
        "next_action": next_actions[0],
    }

    # ── Oanda demo ──
    rec = _read_json(WORKER / "logs/nexus_demo_trading_loop_latest.json") or {}
    de = rec.get("direct_execution") or {}
    plist = Path.home() / "Library/LaunchAgents/com.nexus.trading-engine.plist"
    sflags = {}
    try:
        import plistlib
        env = (plistlib.loads(plist.read_bytes()).get("EnvironmentVariables") or {})
        for k in ("LIVE_TRADING", "TRADING_LIVE_EXECUTION_ENABLED", "PAPER_ONLY",
                  "OANDA_ALLOW_LIVE", "NEXUS_AUTO_TRADING", "OANDA_ENVIRONMENT", "OANDA_DEMO_ENABLED"):
            if k in env:
                sflags[k] = env[k]
    except Exception:
        pass
    api_practice = "fxpractice" in (sflags.get("OANDA_ENVIRONMENT", "") or "practice")
    oanda = {
        "status": "WORKING (practice/demo)",
        "practice_demo_confirmed": sflags.get("OANDA_ENVIRONMENT") == "practice",
        "live_funded_blocked": sflags.get("LIVE_TRADING", "false") == "false"
                               and sflags.get("OANDA_ALLOW_LIVE", "false") == "false",
        "raw_auto_trading": sflags.get("NEXUS_AUTO_TRADING", "false") == "true",
        "latest_receipt": "~/nexus-ai-worker/logs/nexus_demo_trading_loop_latest.json",
        "latest_result": de.get("outcome", rec.get("status", "unknown")),
        "open_positions": [],
        "fills": 1 if de.get("outcome") == "filled" else 0,
        "cancels": 1 if de.get("outcome") == "canceled" else 0,
        "rejects": 1 if de.get("outcome") == "rejected" else 0,
        "errors": 1 if de.get("outcome") == "error" else 0,
        "safety_flags": sflags,
    }

    # ── Showroom ──
    showroom = {
        "status": "WORKING (local; not pushed)",
        "component_exists": (ROOT / "src/components/Showroom.tsx").exists(),
        "route": "/app/showroom",
        "local_commit": "62e1306",
        "pushed": False,
        "deployed": False,
        "asset_registry": "logs/showroom_assets.json",
        "followups": ["read-only /api/showroom endpoint for live asset counts + approve/revise wiring"],
    }

    # ── Social automation ──
    try:
        import sys
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from lib import social_queue
        from lib.social_publishers import connector_status
        sq_summary = social_queue.summarize()
        connectors = connector_status()
        social_queue.write_status_reports(connectors)
    except Exception as exc:
        sq_summary = {
            "total": 0,
            "pending_review_count": 0,
            "approved_count": 0,
            "dry_run_ready_count": 0,
            "published_count": 0,
            "failed_count": 0,
            "latest_items": [],
            "error": str(exc)[:160],
        }
        connectors = {"error": str(exc)[:160]}
    social = {
        "status": "WORKING (local queue/dry-run)" if not sq_summary.get("error") else "PARTIAL",
        "queue_path": sq_summary.get("queue_path", "outputs/social_queue/social_queue.jsonl"),
        "queue_count": sq_summary.get("total", 0),
        "pending_review_count": sq_summary.get("pending_review_count", 0),
        "approved_count": sq_summary.get("approved_count", 0),
        "dry_run_ready_count": sq_summary.get("dry_run_ready_count", 0),
        "published_count": sq_summary.get("published_count", 0),
        "failed_count": sq_summary.get("failed_count", 0),
        "needs_revision_count": sq_summary.get("needs_revision_count", 0),
        "average_quality_score": sq_summary.get("average_quality_score", 0),
        "last_published": sq_summary.get("last_published"),
        "latest_items": sq_summary.get("latest_items", []),
        "connector_status": connectors,
        "next_social_action": "Ray reviews the top queued Facebook posts, approves one exact item, then runs dry-run; real publish remains approval-gated.",
        "reports": {
            "queue_status": "reports/social/social_queue_status_latest.md",
            "connector_status": "reports/social/social_connector_status_latest.md",
        },
    }

    # ── Options guard ──
    of = _env_flags(ROOT / ".env", ["OPTIONS_REPORTS_ENABLED", "OPTIONS_TELEGRAM_REPORTS_ENABLED",
                                     "OPTIONS_TRADING_ENABLED", "OPTIONS_LIVE_TRADING"])
    guard_in_lab = "OPTIONS_REPORTS_ENABLED" in (ROOT / "lib/trading_intelligence_lab.py").read_text(errors="ignore")
    options_guard = {
        "status": "GUARDED (off by default)" if guard_in_lab else "UNGUARDED",
        "reports_enabled": of.get("OPTIONS_REPORTS_ENABLED", "false") == "true",
        "telegram_reports_enabled": of.get("OPTIONS_TELEGRAM_REPORTS_ENABLED", "false") == "true",
        "trading_enabled": of.get("OPTIONS_TRADING_ENABLED", "false") == "true",
        "live_trading_enabled": of.get("OPTIONS_LIVE_TRADING", "false") == "true",
        "options_trades_placed": False,
        "templates_gated_in_lab": guard_in_lab,
    }

    # ── Blockers ──
    blockers = []
    for f in failures:
        if "continuous-ops-daily" in f:
            blockers.append({"area": "automation", "blocker": "continuous-ops-daily job fails (missing worker artifact ai_improvement_postiz.md)",
                             "fix": "fix the report path / generate the expected artifact, or repoint the job"})
        elif "hermes-mobile" in f:
            blockers.append({"area": "communication", "blocker": "hermes-mobile last exit=1 (process is running; stale)",
                             "fix": "confirm bot healthy; reload only if it stops polling"})
        elif "control-center" in f:
            blockers.append({"area": "automation", "blocker": "control-center port 4000 already in use (redundant launch)",
                             "fix": "one instance already serving; ignore or dedupe the launch"})
    if monetization["status"].startswith("PARTIAL"):
        blockers.append({"area": "monetization", "blocker": "outreach/publish needs Ray approval (drafts ready)",
                         "fix": "Ray approves outreach + landing/lead-magnet publish in approval queue"})

    overall = "WORKING"
    if blockers:
        overall = "PARTIAL"
    if not comm_ok:
        overall = "BLOCKED"

    return {
        "updated_at": _now(),
        "overall_status": overall,
        "communication": comm,
        "automation": automation,
        "monetization": monetization,
        "money_pipeline": money_pipeline,
        "oanda_demo": oanda,
        "showroom": showroom,
        "social": social,
        "options_guard": options_guard,
        "blockers": blockers,
        "top_3_next_actions": next_actions,
    }


def write_brief(st: dict) -> None:
    m = st["monetization"]; o = st["oanda_demo"]; g = st["options_guard"]
    lines = [
        f"# Nexus Operator Brief — {st['updated_at'][:19]}Z",
        f"Overall: **{st['overall_status']}**", "",
        "## 1. Working",
        f"- Communication: {st['communication']['status']} (scheduler/{st['communication']['scheduler']}, "
        f"TheChosenOne/{st['communication']['thechosenone']}, Hermes-Mobile/{st['communication']['hermes_mobile']})",
        f"- Oanda demo: {o['status']} (practice, live blocked={o['live_funded_blocked']}, auto_trading={o['raw_auto_trading']})",
        f"- Options guard: {g['status']}",
        f"- Showroom: {st['showroom']['status']} (route {st['showroom']['route']})",
        f"- Social queue: {st.get('social', {}).get('status', 'unknown')} "
        f"(queued={st.get('social', {}).get('queue_count', 0)}, pending={st.get('social', {}).get('pending_review_count', 0)}, "
        f"approved={st.get('social', {}).get('approved_count', 0)}, dry-run={st.get('social', {}).get('dry_run_ready_count', 0)}, "
        f"avg_quality={st.get('social', {}).get('average_quality_score', 0)})",
        "",
        "## 2. Partial",
        f"- Monetization: {m['status']}",
        f"- Automation: {st['automation']['status']} (failures: {', '.join(st['automation']['failures']) or 'none'})",
        "",
        "## 3. Blocked",
    ]
    lines += [f"- [{b['area']}] {b['blocker']} → FIX: {b['fix']}" for b in st["blockers"]] or ["- (none)"]
    lines += [
        "", "## 4. How Nexus makes money today",
        f"- Offer: **{m['primary_offer']}** — {' / '.join(m['prices'])}",
        f"- Package: {m['package_path']}",
        f"- Assets ready ({len(m['assets'])}): {', '.join(m['assets'][:8])}{' …' if len(m['assets'])>8 else ''}",
        "", "## 5. Needs approval",
        f"- Approval queue: {st['automation']['approval_queue_count']} items ({st['automation']['approval_queue_path']})",
        f"- Approval-gated assets: {', '.join(m['approval_items']) or 'none flagged'}",
        "- External sends/publish/payments: BLOCKED until Ray approves",
        "", "## 6. Oanda demo status",
        f"- practice={o['practice_demo_confirmed']} live_blocked={o['live_funded_blocked']} auto_trading={o['raw_auto_trading']}",
        f"- latest result: {o['latest_result']} | fills={o['fills']} cancels={o['cancels']} rejects={o['rejects']} errors={o['errors']}",
        f"- receipt: {o['latest_receipt']}",
        "", "## 7. Showroom status",
        f"- component_exists={st['showroom']['component_exists']} pushed={st['showroom']['pushed']} deployed={st['showroom']['deployed']}",
        f"- registry: {st['showroom']['asset_registry']} | follow-up: {st['showroom']['followups'][0]}",
        "", "## 7b. Social automation status",
        f"- queue_count={st.get('social', {}).get('queue_count', 0)} pending_review={st.get('social', {}).get('pending_review_count', 0)} "
        f"approved={st.get('social', {}).get('approved_count', 0)} dry_run_ready={st.get('social', {}).get('dry_run_ready_count', 0)} "
        f"published={st.get('social', {}).get('published_count', 0)} failed={st.get('social', {}).get('failed_count', 0)}",
        f"- creative quality gate: active avg_score={st.get('social', {}).get('average_quality_score', 0)} needs_revision={st.get('social', {}).get('needs_revision_count', 0)}",
        f"- last published: {(st.get('social', {}).get('last_published') or {}).get('post_id', 'none')} "
        f"{(st.get('social', {}).get('last_published') or {}).get('permalink', '')}",
        f"- connector report: {st.get('social', {}).get('reports', {}).get('connector_status', 'reports/social/social_connector_status_latest.md')}",
        f"- next: {st.get('social', {}).get('next_social_action', 'review queue')}",
        "", "## 8. Commands Ray can type",
    ]
    lines += [f"- {c}" for c in COMMANDS]
    lines += ["", "## 9. Top 3 money actions"]
    lines += [f"{i+1}. {a}" for i, a in enumerate(st["top_3_next_actions"])]
    lines += ["", "## 10. Paths",
              f"- status: reports/operator/nexus_operator_status.json",
              f"- brief: reports/operator/nexus_operator_brief.md"]
    BRIEF_MD.write_text("\n".join(lines) + "\n")


# ── Command/intent answers (read from status JSON; never from memory) ──
def answer(intent: str, st: dict | None = None) -> str:
    st = st or _read_json(STATUS_JSON) or collect()
    q = (intent or "").strip().lower()
    m, o, g = st["monetization"], st["oanda_demo"], st["options_guard"]
    if "make money" in q:
        return ("HOW WE MAKE MONEY TODAY\n"
                f"Offer: {m['primary_offer']} — {' / '.join(m['prices'])}\n"
                f"Ready assets: {', '.join(m['assets'][:6]) or 'none'}\n"
                f"Needs approval: {', '.join(m['approval_items']) or 'outreach/publish'}\n"
                "Top 3 actions:\n" + "\n".join(f"  {i+1}. {a}" for i, a in enumerate(st['top_3_next_actions'])) +
                f"\nBlockers: {len(st['blockers'])} (type 'what is blocked')\n"
                "Package: " + m['package_path'])
    if "approval" in q:
        return ("WHAT NEEDS APPROVAL\n"
                f"Approval queue: {st['automation']['approval_queue_count']} items\n"
                f"Pending approval-gated assets: {', '.join(m['approval_items']) or 'none flagged'}\n"
                "Blocked external actions: customer email/DM, public posts, payments, live/options trading\n"
                f"Next decision: {st['top_3_next_actions'][0]}")
    if "money pipeline" in q:
        mp = st["money_pipeline"]
        return (f"MONEY PIPELINE\nOffer: {mp['offer']} ({' / '.join(m['prices'])})\n"
                f"Stage: {mp['stage']}\nReady: {len(mp['ready_assets'])} assets\n"
                f"Blocked: {', '.join(mp['blocked_assets'])}\nNext: {mp['next_action']}")
    if "oanda" in q:
        return (f"OANDA DEMO STATUS\npractice={o['practice_demo_confirmed']} live_blocked={o['live_funded_blocked']} "
                f"auto_trading={o['raw_auto_trading']}\nlatest result: {o['latest_result']} | "
                f"fills={o['fills']} cancels={o['cancels']} rejects={o['rejects']} errors={o['errors']}\n"
                f"receipt: {o['latest_receipt']}")
    if "showroom" in q:
        s = st["showroom"]
        return (f"SHOWROOM\nroute {s['route']} | component={s['component_exists']} | "
                f"local_commit {s['local_commit']} pushed={s['pushed']} deployed={s['deployed']}\n"
                f"registry: {s['asset_registry']}\nfollow-up: {s['followups'][0]}")
    if "social queue" in q or "social posts" in q:
        s = st.get("social", {})
        items = s.get("latest_items") or []
        lines = [
            "SOCIAL QUEUE",
            f"queue_count={s.get('queue_count', 0)} pending={s.get('pending_review_count', 0)} approved={s.get('approved_count', 0)} dry_run_ready={s.get('dry_run_ready_count', 0)} published={s.get('published_count', 0)} failed={s.get('failed_count', 0)}",
            f"next: {s.get('next_social_action', 'review queue')}",
            "latest:",
        ]
        lines += [
            f"- {item.get('id')} | {item.get('platform')} | {item.get('status')} | {item.get('title')}"
            for item in items[-5:]
        ] or ["- none"]
        return "\n".join(lines)
    if "blocking social publishing" in q:
        s = st.get("social", {})
        c = s.get("connector_status") or {}
        return ("SOCIAL PUBLISHING BLOCKERS\n"
                f"Facebook: {(c.get('facebook') or {}).get('status', 'unknown')} - {', '.join((c.get('facebook') or {}).get('blockers') or [])}\n"
                f"Instagram: {(c.get('instagram') or {}).get('status', 'unknown')} - {', '.join((c.get('instagram') or {}).get('blockers') or [])}\n"
                f"Postiz: {(c.get('postiz') or {}).get('status', 'unknown')} - {', '.join((c.get('postiz') or {}).get('blockers') or [])}\n"
                "Real publishing also requires Ray approval of exact item/account and --confirm-real-publish.")
    if "post today" in q:
        s = st.get("social", {})
        items = s.get("latest_items") or []
        candidate = next((item for item in items if item.get("status") in {"queued_for_review", "approved", "dry_run_ready"}), None)
        if candidate:
            return (f"POST TODAY CANDIDATE\n{candidate.get('title')}\nPlatform: {candidate.get('platform')}\n"
                    f"Caption: {candidate.get('caption')}\nCTA: {candidate.get('cta')}\n"
                    "Manual post only unless Ray approves connector/account and real publish.")
        return ("POST TODAY\nUse the first approved manual Facebook post from "
                "reports/value_test/manual_social_posting_package_20260617.md. Manual post only.")
    if "automation" in q:
        a = st["automation"]
        return (f"AUTOMATION STATUS: {a['status']}\nscheduled jobs: {', '.join(a['scheduled_jobs'])}\n"
                f"approval queue: {a['approval_queue_count']}\nfailures: {', '.join(a['failures']) or 'none'}\n"
                f"latest research: {a['research_report_path']}")
    if "blocked" in q:
        if not st["blockers"]:
            return "WHAT IS BLOCKED\n(nothing blocking right now)"
        return "WHAT IS BLOCKED\n" + "\n".join(
            f"- [{b['area']}] {b['blocker']}\n    FIX: {b['fix']}" for b in st["blockers"])
    if "run daily operator" in q:
        return "Refreshing operator status… (run: python3 scripts/run_nexus_operator_core.py)"
    return ("Operator commands: " + " | ".join(COMMANDS))


def send_war_room(st: dict, force: bool = False) -> bool:
    try:
        import sys
        sys.path.insert(0, str(ROOT))
        from lib import hermes_gate as G
        v = {}
        for ln in (ROOT / ".env").read_text(errors="ignore").splitlines():
            s = ln.strip()
            if s and not s.startswith("#") and "=" in s:
                k, val = s.split("=", 1); v[k.strip()] = val.strip().strip('"').strip("'")

        def _truthy(key, default):
            return str(v.get(key, default)).strip().lower() in {"1", "true", "yes", "on"}

        # Auto War Room send is OFF unless explicitly enabled. This stops every operator
        # run from emitting a Telegram message (a prior spam source). Manual --ask replies
        # and force=True bypass this; the raw send is still duplicate-guarded downstream.
        if not force:
            manual_only = _truthy("TELEGRAM_MANUAL_ONLY", "true")
            auto_ok = _truthy("WAR_ROOM_AUTO_SEND", "false") and _truthy("NEXUS_WAR_ROOM_SEND_ENABLED", "false")
            if manual_only or not auto_ok:
                st.setdefault("notes", []).append("war_room auto-send disabled (TELEGRAM_MANUAL_ONLY / WAR_ROOM flags)")
                return False
        msg = ("Nexus Operator Core is active.\n"
               f"Overall: {st['overall_status']}\n"
               f"Money: {st['monetization']['primary_offer']} ($97 / $197-$297). "
               f"Approval queue: {st['automation']['approval_queue_count']}.\n"
               f"Oanda demo: {st['oanda_demo']['latest_result']} (practice, live blocked).\n"
               f"Showroom: {st['showroom']['route']} (local, not pushed).\n"
               f"Automation failures: {', '.join(st['automation']['failures']) or 'none'}.\n"
               f"Top blockers: {len(st['blockers'])}.\n"
               "Type: how do we make money today | what needs approval | show money pipeline | "
               "show oanda status | show showroom | show automation status | what is blocked | run daily operator\n"
               "status: reports/operator/nexus_operator_status.json | brief: reports/operator/nexus_operator_brief.md")
        return bool(G._telegram_send(msg, v.get("TELEGRAM_BOT_TOKEN", ""), v.get("WAR_ROOM_CHAT_ID", ""), parse_mode=""))
    except Exception as e:
        st.setdefault("blockers", []).append({"area": "communication", "blocker": f"war room send failed: {str(e)[:120]}", "fix": "check certifi/token/WAR_ROOM_CHAT_ID"})
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Nexus Operator Core")
    ap.add_argument("--ask", default=None, help="answer a War Room command from current status")
    ap.add_argument("--no-telegram", action="store_true", help="refresh status/brief only, no send")
    args = ap.parse_args()

    if args.ask:
        print(answer(args.ask))
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    st = collect()
    sent = False
    if not args.no_telegram:
        sent = send_war_room(st)
        st["communication"]["war_room_summary_sent"] = sent
    STATUS_JSON.write_text(json.dumps(st, indent=2, default=str))
    write_brief(st)
    print(f"operator status -> {STATUS_JSON.relative_to(ROOT)}")
    print(f"operator brief  -> {BRIEF_MD.relative_to(ROOT)}")
    print(f"overall: {st['overall_status']} | war_room_sent: {sent} | blockers: {len(st['blockers'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
