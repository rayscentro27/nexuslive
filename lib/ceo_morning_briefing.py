"""
CEO Morning Briefing System
============================
Generates a structured executive briefing covering:
  1. System health
  2. Workforce performance
  3. Business growth opportunities
  4. Content status
  5. Infrastructure status
  6. Top 5 priority actions

Outputs:
  - Supabase ceo_briefings table
  - Telegram (if TELEGRAM_AUTO_REPORTS_ENABLED=true)
  - Returns markdown string for dashboard/Hermes

Usage:
  from lib.ceo_morning_briefing import generate_morning_briefing, deliver_briefing
  briefing = generate_morning_briefing()
  deliver_briefing(briefing)

  # Or run standalone:
  python3 -m lib.ceo_morning_briefing
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return date.today().isoformat()


def _sb_url() -> str:
    return (os.getenv("SUPABASE_URL") or "").strip()


def _sb_key() -> str:
    return (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY", "")
    )


def _sb_get(path: str, timeout: int = 8) -> list:
    try:
        from scripts.prelaunch_utils import rest_select
        return rest_select(path, timeout=timeout) or []
    except Exception:
        return []


def _sb_post(table: str, payload: dict, method: str = "POST", filter_qs: str = "") -> dict:
    url = _sb_url()
    key = _sb_key()
    if not url or not key:
        return {"error": "supabase_not_configured"}
    endpoint = f"{url}/rest/v1/{table}"
    if filter_qs:
        endpoint += f"?{filter_qs}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        endpoint, data=data,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as exc:
        return {"error": str(exc)}


# ─── Section builders ─────────────────────────────────────────────────────────

def _section_system_health() -> dict:
    heartbeats = _sb_get(
        "worker_heartbeats?select=worker_id,status,last_seen_at"
        "&order=last_seen_at.desc&limit=40"
    )
    queue = _sb_get(
        "job_queue?select=id,status&order=created_at.desc&limit=80"
    )
    dispatch = _sb_get(
        "agent_dispatch_tasks?select=id,status,false_completion"
        "&order=created_at.desc&limit=100"
    )

    active_workers = sum(1 for h in heartbeats if str(h.get("status","")).lower() == "active")
    stalled_workers = sum(1 for h in heartbeats if str(h.get("status","")).lower() in ("stalled","idle"))
    q_pending = sum(1 for q in queue if str(q.get("status","")).lower() in ("queued","pending","received"))
    q_failed = sum(1 for q in queue if str(q.get("status","")).lower() == "failed")
    false_completions = sum(1 for d in dispatch if d.get("false_completion"))

    status_flag = "🟢 Healthy"
    if q_failed > 5 or false_completions > 3:
        status_flag = "🔴 Issues Detected"
    elif stalled_workers > 2 or q_failed > 0:
        status_flag = "🟡 Degraded"

    return {
        "status": status_flag,
        "active_workers": active_workers,
        "stalled_workers": stalled_workers,
        "queue_pending": q_pending,
        "queue_failed": q_failed,
        "false_completions": false_completions,
        "total_heartbeats": len(heartbeats),
    }


def _section_workforce() -> dict:
    rollups = _sb_get(
        f"worker_productivity_rollups?select=worker_id,worker_role,tasks_completed,"
        f"productivity_score,false_completion_count,last_heartbeat_at"
        f"&report_date=eq.{_today()}&order=productivity_score.desc&limit=20"
    )
    if not rollups:
        # Fall back to heartbeats
        rollups = _sb_get(
            "worker_heartbeats?select=worker_id,status,last_seen_at"
            "&order=last_seen_at.desc&limit=20"
        )

    top_workers = [r.get("worker_id","?") for r in rollups[:3]]
    inactive = [r for r in rollups if not r.get("tasks_completed") and str(r.get("status","")).lower() != "active"]
    dispatch_rows = _sb_get(
        "agent_dispatch_tasks?select=id,status,task_type,created_at"
        "&status=eq.failed&order=created_at.desc&limit=10"
    )
    stalled = _sb_get(
        "agent_dispatch_tasks?select=id,status,normalized_goal,created_at"
        "&status=in.(running,received)&order=created_at.asc&limit=5"
    )

    return {
        "top_workers": top_workers,
        "inactive_count": len(inactive),
        "failed_tasks_today": len(dispatch_rows),
        "stalled_tasks": len(stalled),
        "rollup_count": len(rollups),
    }


def _section_growth() -> dict:
    opps = _sb_get(
        "worker_recommendations?select=id,category,priority,title,status"
        "&status=eq.open&order=priority.asc,generated_at.desc&limit=10"
    )
    # Fall back to opportunity scoring knowledge
    if not opps:
        opps = _sb_get(
            "nexus_knowledge_items?select=id,category,title,summary"
            "&category=in.(monetization,affiliate,seo,content)&order=created_at.desc&limit=10"
        )
    top_opps = [
        {"priority": o.get("priority","?"), "title": o.get("title") or o.get("summary","?")}
        for o in opps[:5]
    ]
    return {
        "open_recommendations": len(opps),
        "top_opportunities": top_opps,
    }


def _section_content() -> dict:
    drafts = _sb_get(
        "content_drafts?select=id,status,title,content_type&order=created_at.desc&limit=20"
    )
    pending_publish = [d for d in drafts if str(d.get("status","")).lower() in ("draft","ready","pending")]
    published = [d for d in drafts if str(d.get("status","")).lower() == "published"]

    # Check for YouTube scripts
    yt_scripts = _sb_get(
        "agent_dispatch_tasks?select=id,status,normalized_goal"
        "&task_type=eq.content&status=in.(planned,awaiting_approval)&limit=10"
    )
    return {
        "drafts_pending": len(pending_publish),
        "published_today": len(published),
        "youtube_scripts_queued": len(yt_scripts),
        "needs_action": len(pending_publish) > 0 or len(yt_scripts) > 0,
    }


def _section_infrastructure() -> dict:
    provider_health = _sb_get(
        "provider_health?select=provider_name,status,last_checked_at"
        "&order=last_checked_at.desc&limit=10"
    )
    model_routes = _sb_get(
        "model_routing_rules?select=provider,model_name,enabled&enabled=eq.true&limit=10"
    )
    oracle_alive = False
    try:
        import socket
        s = socket.create_connection(("161.153.40.41", 22), timeout=3)
        s.close()
        oracle_alive = True
    except Exception:
        pass

    supabase_ok = bool(_sb_url())

    providers_ok = [p for p in provider_health if str(p.get("status","")).lower() == "healthy"]
    providers_down = [p for p in provider_health if str(p.get("status","")).lower() in ("down","error","unhealthy")]

    return {
        "oracle_reachable": oracle_alive,
        "supabase_configured": supabase_ok,
        "providers_healthy": len(providers_ok),
        "providers_down": len(providers_down),
        "active_models": len(model_routes),
        "provider_names_down": [p.get("provider_name","?") for p in providers_down],
    }


def _section_revenue_progress() -> dict:
    """Pull monetization KPIs and revenue progress toward $1K/week target."""
    result = {
        "weekly_target": 1000,
        "newsletter_subscribers": 0,
        "affiliate_clicks": 0,
        "funding_leads": 0,
        "content_outputs_this_week": 0,
        "top_affiliate_programs": [],
        "goals_file_exists": False,
    }
    try:
        import yaml
        goals_file = ROOT / "state" / "monetization_goals.yaml"
        if goals_file.exists():
            data = yaml.safe_load(goals_file.read_text())
            current = data.get("current_metrics", {})
            result.update({
                "newsletter_subscribers": current.get("newsletter_subscribers", 0),
                "affiliate_clicks": current.get("affiliate_clicks", 0),
                "funding_leads": current.get("funding_leads", 0),
                "goals_file_exists": True,
                "weekly_target": data.get("target_weekly_revenue", 1000),
            })
    except Exception:
        pass

    try:
        from datetime import timedelta
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        outputs = _sb_get(
            f"content_outputs?select=id,output_type,status,created_at"
            f"&created_at=gte.{week_ago}&limit=100"
        )
        result["content_outputs_this_week"] = len(outputs)
    except Exception:
        pass

    try:
        from lib.affiliate_engine import AFFILIATE_REGISTRY
        top_affiliates = sorted(
            AFFILIATE_REGISTRY.items(),
            key=lambda x: x[1].get("roi_score", 0),
            reverse=True,
        )[:3]
        result["top_affiliate_programs"] = [
            {"name": n, "roi_score": v.get("roi_score", 0), "commission": v.get("commission", "?")}
            for n, v in top_affiliates
        ]
    except Exception:
        pass

    return result


def _section_market_intelligence() -> dict:
    """Pull market intelligence scout outputs and trading research status."""
    result = {
        "strategies_in_testing": 0,
        "paper_trades_this_week": 0,
        "top_macro_signal": "",
        "research_artifacts_today": 0,
    }
    try:
        from datetime import timedelta
        today = date.today().isoformat()
        artifacts = _sb_get(
            f"research_artifacts?select=id,topic,title&created_at=gte.{today}T00:00:00Z&limit=20"
        )
        result["research_artifacts_today"] = len(artifacts)

        trading_artifacts = [a for a in artifacts if "trad" in str(a.get("topic", "")).lower()]
        result["strategies_in_testing"] = len(trading_artifacts)
    except Exception:
        pass

    return result


def _section_scout_productivity() -> dict:
    """Check which scouts have run and their finding counts."""
    result = {"scouts_active": [], "scouts_idle": [], "total_findings_today": 0}
    try:
        flag_dir = ROOT / "artifacts" / "watcher_flags"
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        if flag_dir.exists():
            for f in flag_dir.glob("*_last_run.json"):
                try:
                    data = json.loads(f.read_text())
                    ran_at = datetime.fromisoformat(data.get("ran_at", "2000-01-01").replace("Z", "+00:00"))
                    scout = f.stem.replace("_last_run", "")
                    findings = data.get("findings", 0) or data.get("ranked_count", 0)
                    if ran_at > cutoff:
                        result["scouts_active"].append(f"{scout}({findings})")
                        result["total_findings_today"] += findings
                    else:
                        result["scouts_idle"].append(scout)
                except Exception:
                    pass
    except Exception:
        pass

    return result


def _section_operational_bottlenecks() -> dict:
    """Identify the top operational bottlenecks blocking revenue."""
    bottlenecks = []
    try:
        from lib.hermes_executive_memory import load_memory
        mem = load_memory()
        unfinished = mem.get("unfinished_systems", [])
        infra_probs = mem.get("infrastructure_problems", [])
        for item in (unfinished + infra_probs)[:6]:
            bottlenecks.append(str(item))
    except Exception:
        pass
    return {"bottlenecks": bottlenecks[:5], "count": len(bottlenecks)}


def _build_top_actions(health: dict, workforce: dict, growth: dict, content: dict, infra: dict) -> list[dict]:
    actions = []
    rank = 1

    if health.get("false_completions", 0) > 0:
        actions.append({
            "rank": rank,
            "urgency": "CRITICAL",
            "action": f"Audit {health['false_completions']} false completion(s) — run `nexus hermes audit`",
        })
        rank += 1

    if infra.get("providers_down"):
        actions.append({
            "rank": rank,
            "urgency": "HIGH",
            "action": f"Restore providers: {', '.join(infra['providers_down'])}",
        })
        rank += 1

    if health.get("queue_failed", 0) > 0:
        actions.append({
            "rank": rank,
            "urgency": "HIGH",
            "action": f"Clear {health['queue_failed']} failed queue tasks — check worker logs",
        })
        rank += 1

    if workforce.get("stalled_tasks", 0) > 0:
        actions.append({
            "rank": rank,
            "urgency": "MEDIUM",
            "action": f"Unblock {workforce['stalled_tasks']} stalled task(s) — approve or reassign",
        })
        rank += 1

    if growth.get("top_opportunities"):
        top = growth["top_opportunities"][0]
        actions.append({
            "rank": rank,
            "urgency": "MEDIUM",
            "action": f"Act on top opportunity: {top['title']}",
        })
        rank += 1

    if content.get("drafts_pending", 0) > 0:
        actions.append({
            "rank": rank,
            "urgency": "LOW",
            "action": f"Review {content['drafts_pending']} content draft(s) pending publish",
        })
        rank += 1

    if not infra.get("oracle_reachable"):
        actions.append({
            "rank": rank,
            "urgency": "LOW",
            "action": "Oracle VM unreachable — verify SSH and nexus-llm-worker service",
        })
        rank += 1

    # Always cap at 5
    return actions[:5]


def _build_markdown(
    health: dict, workforce: dict, growth: dict,
    content: dict, infra: dict, actions: list,
    exec_intel: dict | None = None,
) -> str:
    d = _today()
    lines = [
        f"# 🧠 Nexus CEO Operational Briefing — {d}",
        f"**Generated:** {datetime.now().strftime('%H:%M')} | Safety: DRY_RUN=true | LIVE_TRADING=false",
        "",
        "---",
        "",
        "## 1. SYSTEM HEALTH",
        f"**Status:** {health['status']}",
        f"- Active workers: {health['active_workers']} | Stalled: {health['stalled_workers']}",
        f"- Queue pending: {health['queue_pending']} | Failed: {health['queue_failed']}",
        f"- False completions detected: {health['false_completions']}",
        "",
        "## 2. WORKFORCE PERFORMANCE",
    ]
    if workforce["top_workers"]:
        lines.append(f"- Top workers: {', '.join(workforce['top_workers'])}")
    lines += [
        f"- Inactive today: {workforce['inactive_count']}",
        f"- Failed tasks: {workforce['failed_tasks_today']}",
        f"- Stalled tasks: {workforce['stalled_tasks']}",
        "",
        "## 3. BUSINESS GROWTH",
        f"- Open recommendations: {growth['open_recommendations']}",
    ]
    for opp in growth["top_opportunities"][:3]:
        lines.append(f"  - [{opp['priority'].upper()}] {opp['title']}")
    lines += [
        "",
        "## 4. CONTENT STATUS",
        f"- Drafts pending publish: {content['drafts_pending']}",
        f"- YouTube scripts queued: {content['youtube_scripts_queued']}",
        "",
        "## 5. INFRASTRUCTURE",
        f"- Oracle VM: {'✅ Reachable' if infra['oracle_reachable'] else '❌ Unreachable'}",
        f"- Supabase: {'✅ Configured' if infra['supabase_configured'] else '❌ Not configured'}",
        f"- Providers healthy: {infra['providers_healthy']} | Down: {infra['providers_down']}",
        "",
        "## 6. TOP 5 PRIORITY ACTIONS",
    ]
    if actions:
        for a in actions:
            lines.append(f"  {a['rank']}. [{a['urgency']}] {a['action']}")
    else:
        lines.append("  ✅ No critical actions — system is running well.")

    # Executive intelligence section
    if exec_intel:
        lines += ["", "## 7. EXECUTIVE INTELLIGENCE"]
        priorities = exec_intel.get("execution_priorities", [])
        if priorities:
            lines.append("**Today's Execution Priorities:**")
            for p in priorities[:5]:
                lines.append(f"  - {p}")
        mono = exec_intel.get("monetization_priorities", [])
        if mono:
            lines.append("**Active Monetization Levers:**")
            for m in mono[:3]:
                lines.append(f"  - {m}")
        unfinished = exec_intel.get("unfinished_systems", [])
        if unfinished:
            lines.append("**Unfinished Systems:**")
            for u in unfinished[:3]:
                lines.append(f"  - 🔧 {u}")
        infra_probs = exec_intel.get("infrastructure_problems", [])
        if infra_probs:
            lines.append("**Infrastructure Problems:**")
            for p in infra_probs[:3]:
                lines.append(f"  - ⚠️  {p}")
        if exec_intel.get("overnight_changes", 0):
            lines.append(f"\n*Overnight: {exec_intel['overnight_changes']} category updates from live data*")

    lines += ["", "---", "*Nexus AI — Autonomous Intelligence + Monetization Operating System*"]
    return "\n".join(lines)


# ─── Morning Executive Intelligence Cycle ────────────────────────────────────

def _section_executive_intelligence() -> dict:
    """Pull live executive memory and overnight changes for briefing injection."""
    result: dict = {
        "execution_priorities": [],
        "unfinished_systems": [],
        "monetization_priorities": [],
        "overnight_changes": 0,
        "memory_updated_at": "",
    }
    try:
        from lib.hermes_executive_memory import load_memory, refresh_from_live_data
        changes = refresh_from_live_data()
        result["overnight_changes"] = sum(changes.values())
        mem = load_memory(force_refresh=True)
        result["execution_priorities"] = mem.get("execution_priorities", [])[:5]
        result["unfinished_systems"] = mem.get("unfinished_systems", [])[:4]
        result["monetization_priorities"] = mem.get("monetization_priorities", [])[:3]
        result["memory_updated_at"] = mem.get("updated_at", "")[:10]
        result["infrastructure_problems"] = mem.get("infrastructure_problems", [])[:3]
        result["affiliate_campaigns"] = mem.get("affiliate_campaigns", [])[:3]
    except Exception as exc:
        result["error"] = str(exc)
    return result


# ─── Public API ───────────────────────────────────────────────────────────────

def generate_morning_briefing() -> dict:
    """Build a full 12-section CEO executive briefing with revenue + intelligence focus."""
    health       = _section_system_health()
    workforce    = _section_workforce()
    growth       = _section_growth()
    content      = _section_content()
    infra        = _section_infrastructure()
    exec_intel   = _section_executive_intelligence()
    revenue      = _section_revenue_progress()
    market_intel = _section_market_intelligence()
    scout_prod   = _section_scout_productivity()
    bottlenecks  = _section_operational_bottlenecks()
    actions      = _build_top_actions(health, workforce, growth, content, infra)
    body_md      = _build_full_briefing(
        health, workforce, growth, content, infra, actions, exec_intel,
        revenue, market_intel, scout_prod, bottlenecks,
    )

    return {
        "briefing_date": _today(),
        "briefing_type": "morning",
        "status": "generated",
        "title": f"Nexus Executive Briefing — {_today()}",
        "body_markdown": body_md,
        "system_health": health,
        "workforce_kpis": workforce,
        "executive_intelligence": exec_intel,
        "revenue_progress": revenue,
        "market_intelligence": market_intel,
        "scout_productivity": scout_prod,
        "top_actions": actions,
        "delivery_log": {},
        "generated_by": "ceo_morning_briefing",
        "generated_at": _now(),
    }


def _build_full_briefing(
    health: dict, workforce: dict, growth: dict, content: dict,
    infra: dict, actions: list, exec_intel: dict,
    revenue: dict, market_intel: dict, scout_prod: dict, bottlenecks: dict,
) -> str:
    """12-section executive briefing format."""
    d = _today()
    lines = [
        f"# NEXUS EXECUTIVE BRIEFING — {d}",
        f"**{datetime.now().strftime('%H:%M')} | Mission: $1,000/week | DRY_RUN=true | NO LIVE TRADING**",
        "",
        "---",
        "",

        "## 1. REVENUE PROGRESS",
        f"**Weekly Target:** ${revenue['weekly_target']:,}/week",
        f"- Newsletter subscribers: {revenue['newsletter_subscribers']} / 250 target",
        f"- Affiliate clicks: {revenue['affiliate_clicks']} / 500 target",
        f"- Funding leads: {revenue['funding_leads']} / 15 target",
        f"- Content outputs this week: {revenue['content_outputs_this_week']} / 15 target",
    ]
    if revenue.get("top_affiliate_programs"):
        lines.append("- Top affiliates ready:")
        for a in revenue["top_affiliate_programs"]:
            lines.append(f"  • {a['name']}: roi_score={a['roi_score']} | {a['commission']}")
    lines += [
        "",
        "## 2. SYSTEM HEALTH",
        f"**Status:** {health['status']}",
        f"- Active workers: {health['active_workers']} | Stalled: {health['stalled_workers']}",
        f"- Queue pending: {health['queue_pending']} | Failed: {health['queue_failed']}",
        f"- False completions detected: {health['false_completions']}",
        "",
        "## 3. WORKFORCE PRODUCTIVITY",
    ]
    if workforce.get("top_workers"):
        lines.append(f"- Top workers: {', '.join(workforce['top_workers'])}")
    lines += [
        f"- Inactive today: {workforce['inactive_count']}",
        f"- Failed tasks: {workforce['failed_tasks_today']}",
        f"- Stalled tasks: {workforce['stalled_tasks']}",
        "",
        "## 4. MONETIZATION OPPORTUNITIES",
    ]
    for opp in growth.get("top_opportunities", [])[:4]:
        lines.append(f"  - [{opp['priority'].upper() if isinstance(opp.get('priority'), str) else '?'}] {opp['title']}")
    if not growth.get("top_opportunities"):
        try:
            from lib.nexus_consensus_engine import get_top_opportunities, format_opportunities_for_briefing
            top = get_top_opportunities(limit=4)
            lines.append(format_opportunities_for_briefing(top))
        except Exception:
            lines.append("  Run `nexus watchers run --once` to generate ranked opportunities.")
    lines += [
        "",
        "## 5. CONTENT STATUS",
        f"- Drafts pending: {content['drafts_pending']}",
        f"- YouTube scripts queued: {content['youtube_scripts_queued']}",
        "",
        "## 6. MARKET INTELLIGENCE",
        f"- Research artifacts today: {market_intel['research_artifacts_today']}",
        f"- Strategies in paper testing: {market_intel['strategies_in_testing']}",
        "",
        "## 7. SCOUT PRODUCTIVITY",
    ]
    if scout_prod.get("scouts_active"):
        lines.append(f"- Active (24h): {', '.join(scout_prod['scouts_active'])}")
    if scout_prod.get("scouts_idle"):
        lines.append(f"- Idle: {', '.join(scout_prod['scouts_idle'][:4])}")
    lines.append(f"- Total findings today: {scout_prod.get('total_findings_today', 0)}")
    lines += [
        "",
        "## 8. INFRASTRUCTURE",
        f"- Oracle VM (161.153.40.41): {'✅ Reachable' if infra['oracle_reachable'] else '❌ Unreachable'}",
        f"- Supabase: {'✅ OK' if infra['supabase_configured'] else '❌ Not configured'}",
        f"- Providers healthy: {infra['providers_healthy']} | Down: {infra['providers_down']}",
        "",
        "## 9. OPERATIONAL BOTTLENECKS",
    ]
    for b in bottlenecks.get("bottlenecks", [])[:5]:
        lines.append(f"  - 🔴 {b}")
    if not bottlenecks.get("bottlenecks"):
        lines.append("  ✅ No critical bottlenecks in executive memory")

    lines += ["", "## 10. TOP 5 PRIORITY ACTIONS"]
    if actions:
        for a in actions[:5]:
            lines.append(f"  {a['rank']}. [{a['urgency']}] {a['action']}")
    else:
        lines.append("  ✅ All systems operational — continue execution plan")

    # Section 11: Executive Intelligence
    lines += ["", "## 11. EXECUTIVE INTELLIGENCE"]
    if exec_intel:
        priorities = exec_intel.get("execution_priorities", [])
        if priorities:
            lines.append("**Execution Priorities:**")
            for p in priorities[:4]:
                lines.append(f"  - {p}")
        mono = exec_intel.get("monetization_priorities", [])
        if mono:
            lines.append("**Monetization Levers:**")
            for m in mono[:3]:
                lines.append(f"  - {m}")

    # Section 12: Recommended next-day plan
    lines += [
        "",
        "## 12. RECOMMENDED NEXT-DAY EXECUTION PLAN",
        "  1. Fix content LLM → route to OpenRouter deepseek (content_engine gets real AI output)",
        "  2. Add Lendio/Nav.com affiliate CTAs to all SEO articles and newsletters",
        "  3. Complete Beehiiv setup → launch Newsletter #1 with affiliate CTAs",
        "  4. Complete YouTube Studio profile links (15 min task)",
        "  5. Run `nexus watchers run --once` → re-score all opportunities via consensus engine",
        "  6. Run `nexus hermes audit` → remediate 7 false completions",
        "",
        "---",
        "*Nexus AI — Autonomous Intelligence + Monetization Operating System*",
        "*Safety: NEXUS_DRY_RUN=true | LIVE_TRADING=false | Evidence-first execution*",
    ]
    return "\n".join(lines)


def save_briefing(briefing: dict) -> str | None:
    """Save briefing to Supabase ceo_briefings. Returns row ID or None."""
    result = _sb_post("ceo_briefings", briefing)
    if isinstance(result, list) and result:
        return result[0].get("id")
    if isinstance(result, dict) and result.get("id"):
        return result["id"]
    return None


def deliver_briefing(briefing: dict, send_telegram: bool | None = None) -> dict:
    """Save briefing and optionally send to Telegram. Returns delivery log."""
    log = {}

    row_id = save_briefing(briefing)
    log["supabase_row_id"] = row_id
    log["saved"] = bool(row_id)

    # Telegram delivery
    tg_enabled = send_telegram
    if tg_enabled is None:
        tg_enabled = os.getenv("TELEGRAM_AUTO_REPORTS_ENABLED", "false").lower() == "true"

    if tg_enabled:
        try:
            token = os.getenv("HERMES_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("HERMES_CHAT_ID", "")
            if token and chat_id:
                msg = briefing["body_markdown"][:4000]
                tg_url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode()
                req = urllib.request.Request(tg_url, data=payload,
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=10) as r:
                    tg_resp = json.loads(r.read())
                log["telegram"] = True
                log["telegram_message_id"] = tg_resp.get("result", {}).get("message_id")
            else:
                log["telegram"] = False
                log["telegram_reason"] = "HERMES_BOT_TOKEN or TELEGRAM_CHAT_ID not set"
        except Exception as exc:
            log["telegram"] = False
            log["telegram_error"] = str(exc)
    else:
        log["telegram"] = False
        log["telegram_reason"] = "TELEGRAM_AUTO_REPORTS_ENABLED=false"

    return log


if __name__ == "__main__":
    print("Generating CEO Morning Briefing...")
    briefing = generate_morning_briefing()
    print(briefing["body_markdown"])
    print("\n--- Saving to Supabase ---")
    log = deliver_briefing(briefing)
    print(f"Delivery log: {json.dumps(log, indent=2)}")
