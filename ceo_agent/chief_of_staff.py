"""
Chief of Staff digest builder for Hermes.

Builds grouped digests and CEO-style recommendations from existing Supabase data.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta


SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")

TRADING_MIN_WIN_RATE = float(os.getenv("HERMES_TRADING_MIN_WIN_RATE", "45"))
TRADING_MIN_PROFIT_FACTOR = float(os.getenv("HERMES_TRADING_MIN_PROFIT_FACTOR", "1.1"))
TRADING_MAX_DRAWDOWN = float(os.getenv("HERMES_TRADING_MAX_DRAWDOWN", "-2.0"))
TRADING_MIN_CONSISTENCY = float(os.getenv("HERMES_TRADING_MIN_CONSISTENCY", "0.35"))

BUSINESS_WEIGHT_CONFIDENCE = float(os.getenv("HERMES_BIZ_W_CONF", "0.2"))
BUSINESS_WEIGHT_URGENCY = float(os.getenv("HERMES_BIZ_W_URGENCY", "1.0"))
BUSINESS_WEIGHT_STARTUP = float(os.getenv("HERMES_BIZ_W_STARTUP", "1.0"))
BUSINESS_WEIGHT_SPEED = float(os.getenv("HERMES_BIZ_W_SPEED", "1.0"))
BUSINESS_WEIGHT_AUTOMATION = float(os.getenv("HERMES_BIZ_W_AUTOMATION", "1.0"))
BUSINESS_WEIGHT_FIT = float(os.getenv("HERMES_BIZ_W_FIT", "1.0"))

PERSIST_BRIEFS = os.getenv("HERMES_COS_PERSIST_BRIEFS", "true").lower() == "true"
MIN_TRADES_FOR_RANKING = int(os.getenv("HERMES_TRADING_MIN_TRADES_FOR_RANKING", "20"))
MIN_WEEKS_FOR_RANKING = int(os.getenv("HERMES_TRADING_MIN_WEEKS_FOR_RANKING", "2"))


def _sb_get(path: str) -> list:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _fmt_ts(ts: str) -> str:
    return (ts or "")[:16].replace("T", " ")


def _strategy_data_guidance() -> str:
    return (
        f"Insufficient strategy history this week. Collect {MIN_TRADES_FOR_RANKING}+ completed trades "
        f"across {MIN_WEEKS_FOR_RANKING}+ weeks to unlock ranking analysis."
    )


def _business_readout(opportunity: dict) -> str:
    title = opportunity.get("title", "Untitled")
    model = opportunity.get("niche") or opportunity.get("opportunity_type") or "General"
    desc = str(opportunity.get("description") or "")
    complexity = "Lean" if any(k in desc.lower() for k in ("no-code", "lean", "lightweight")) else "Moderate"
    automation = "High" if any(k in desc.lower() for k in ("automation", "ai", "workflow")) else "Medium"
    monetization = "Lead-gen + service conversion" if any(k in desc.lower() for k in ("lead", "service", "client")) else "Subscription or project-based"
    return (
        f"{title} | model: {model} | launch complexity: {complexity} | "
        f"automation potential: {automation} | monetization: {monetization}"
    )


def build_trading_digest(hours: int = 24) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows = _sb_get(
        "trade_logs?select=id,created_at,symbol,strategy_id,pnl,status,entry_price,exit_price"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=created_at.desc&limit=200"
    )
    if not rows:
        return {
            "text": "No trading activity found for the selected period.",
            "recommendations": ["Run more paper/backtests before strategy changes."],
        }

    by_strategy: dict[str, list[dict]] = defaultdict(list)
    total_pnl = 0.0
    wins = 0
    losses = 0
    for r in rows:
        sid = str(r.get("strategy_id") or "unattributed")
        by_strategy[sid].append(r)
        pnl = float(r.get("pnl") or 0.0)
        total_pnl += pnl
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1

    strat_metrics = []
    for sid, items in by_strategy.items():
        pnls = [float(x.get("pnl") or 0.0) for x in items]
        wins_s = sum(1 for p in pnls if p > 0)
        losses_s = sum(1 for p in pnls if p < 0)
        gross_win = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (gross_win if gross_win > 0 else 0.0)
        win_rate = (wins_s / len(items) * 100.0) if items else 0.0
        drawdown = min(pnls) if pnls else 0.0
        rr_hint = round((gross_win / max(wins_s, 1)) / max((gross_loss / max(losses_s, 1)), 1e-9), 2) if losses_s else 2.5
        consistency = round(abs(sum(pnls)) / max(sum(abs(p) for p in pnls), 1e-9), 2)
        strat_metrics.append({
            "strategy": sid,
            "count": len(items),
            "win_rate": round(win_rate, 1),
            "drawdown": round(drawdown, 2),
            "profit_factor": round(profit_factor, 2),
            "risk_reward": rr_hint,
            "consistency": consistency,
            "pnl": round(sum(pnls), 2),
        })

    strat_metrics.sort(key=lambda x: x["pnl"], reverse=True)
    best = strat_metrics[0]
    worst = strat_metrics[-1]
    recs: list[str] = []
    for s in strat_metrics:
        if s["win_rate"] < TRADING_MIN_WIN_RATE or s["profit_factor"] < TRADING_MIN_PROFIT_FACTOR:
            recs.append(
                f"{s['strategy']}: tighten entry rules and add market/timeframe filter; backtest before scaling."
            )
        if s["drawdown"] < TRADING_MAX_DRAWDOWN:
            recs.append(f"{s['strategy']}: reduce risk size and enforce stricter stop-loss placement.")
        if s["consistency"] < TRADING_MIN_CONSISTENCY:
            recs.append(f"{s['strategy']}: run more samples for consistency validation.")
    if not recs:
        recs.append("Top strategies look stable; next experiment: test one tighter exit rule on best performer.")

    lines = [
        "<b>Trading Digest</b>",
        f"Trades: {len(rows)} | PnL: ${round(total_pnl,2)} | Wins/Losses: {wins}/{losses}",
        f"Best strategy: {best['strategy']} (PnL ${best['pnl']}, win {best['win_rate']}%, PF {best['profit_factor']})",
        f"Worst strategy: {worst['strategy']} (PnL ${worst['pnl']}, win {worst['win_rate']}%, PF {worst['profit_factor']})",
        "Strategy improvements:",
    ]
    lines.extend([f"- {r}" for r in recs[:5]])
    lines.append("Next experiment: Run one 7-day A/B test on entry filter + reduced risk size for weakest strategy.")
    return {"text": "\n".join(lines), "recommendations": recs[:5], "metrics": strat_metrics[:8]}


def build_business_digest(hours: int = 72) -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows = _sb_get(
        "business_opportunities?select=id,title,description,opportunity_type,niche,score,confidence,urgency,created_at"
        f"&created_at=gt.{urllib.parse.quote(cutoff)}&order=score.desc,created_at.desc&limit=50"
    )
    if not rows:
        return {"text": "No business opportunities found in the selected period.", "top": None}

    scored = []
    for r in rows:
        base = float(r.get("score") or 0)
        conf = float(r.get("confidence") or 0)
        urgency = str(r.get("urgency") or "").lower()
        urgency_boost = 8 if urgency in {"high", "urgent"} else 3 if urgency in {"medium"} else 0
        desc = (r.get("description") or "").lower()
        startup_cost = 10 if any(k in desc for k in ("low cost", "no-code", "lean")) else 5
        speed = 10 if any(k in desc for k in ("quick", "fast", "7 day", "immediate")) else 5
        automation = 10 if any(k in desc for k in ("automation", "ai", "workflow")) else 5
        fit = 10 if any(k in desc for k in ("smb", "funding", "credit", "nexus", "client")) else 5
        total = (
            base
            + conf * BUSINESS_WEIGHT_CONFIDENCE
            + urgency_boost * BUSINESS_WEIGHT_URGENCY
            + startup_cost * BUSINESS_WEIGHT_STARTUP
            + speed * BUSINESS_WEIGHT_SPEED
            + automation * BUSINESS_WEIGHT_AUTOMATION
            + fit * BUSINESS_WEIGHT_FIT
        )
        scored.append({**r, "composite": round(total, 2)})

    scored.sort(key=lambda x: x["composite"], reverse=True)
    top = scored[0]
    lines = [
        "<b>Business Opportunity Digest</b>",
        f"Opportunities reviewed: {len(scored)}",
        f"Top recommendation: {top.get('title','Untitled')} ({top.get('niche') or top.get('opportunity_type') or 'general'})",
        "Best online opportunities:",
    ]
    for row in scored[:5]:
        lines.append(f"- {row.get('title','Untitled')} | score {row['composite']} | launch: fast-track")
    lines.append("Website build priority: top 1-2 opportunities with highest composite and Nexus/client fit.")
    return {"text": "\n".join(lines), "top": top, "ranked": scored[:10]}


def build_grants_digest(days: int = 14) -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    cutoff = (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()
    rows = _sb_get(
        "grants_catalog?select=id,title,deadline,funding_amount,is_active"
        f"&is_active=eq.true&deadline=gte.{today}&deadline=lte.{cutoff}&order=deadline.asc&limit=20"
    )
    if not rows:
        return {"text": "No near-term grants found.", "items": []}
    lines = ["<b>Grants Digest</b>"]
    for g in rows[:6]:
        lines.append(f"- {g.get('title','Grant')} | deadline {g.get('deadline','?')} | {g.get('funding_amount') or 'amount n/a'}")
    return {"text": "\n".join(lines), "items": rows}


def build_website_brief(opportunity: dict) -> str:
    title = opportunity.get("title") or "New Venture"
    niche = opportunity.get("niche") or opportunity.get("opportunity_type") or "online service"
    desc = opportunity.get("description") or "Market-validated online offer"
    stem = "".join(ch for ch in title.lower() if ch.isalnum())[:10] or "nexus"
    return "\n".join([
        "<b>Website Build Brief (Approval-Ready)</b>",
        f"Business idea: {title}",
        f"Target customer: SMB operators in {niche}",
        f"Domain/name ideas: {stem}hub.com, get{stem}.com, {stem}pilot.com",
        "Homepage structure: Hero → Problem → Offer → Proof → CTA → FAQ",
        f"Offer: {desc[:160]}",
        "Lead magnet: 1-page readiness checklist + ROI calculator",
        "Checkout/booking flow: CTA → qualification form → calendar/payment",
        "Required pages: Home, Offer, Pricing, Case Studies, FAQ, Contact, Privacy/Terms",
        "AI employee support role: lead qualifier + onboarding concierge",
        "First 7-day launch plan: Day1 messaging, Day2 LP draft, Day3 assets, Day4 CRM flow, Day5 QA, Day6 traffic, Day7 review",
    ])


def build_daily_executive_summary() -> str:
    try:
        from ceo_agent.recommendation_queue import seed_default_recommendations
        seed_default_recommendations()
    except Exception:
        pass

    trading = build_trading_digest()
    business = build_business_digest()
    grants = build_grants_digest()
    credit_line = "Credit intelligence pending telemetry refresh."
    funding_line = "Funding intelligence pending telemetry refresh."
    client_line = "Client success intelligence pending telemetry refresh."
    review_line = "Review console diagnostics pending."
    try:
        from ceo_agent.credit_funding_intelligence import credit_actions_work_best, funding_blockers
        from ceo_agent.client_success_intelligence import prioritize_this_week
        from ceo_agent.executive_review_console import sparse_data_diagnostics

        credit_line = credit_actions_work_best()
        funding_line = funding_blockers()
        client_line = prioritize_this_week()
        review_line = sparse_data_diagnostics()
    except Exception:
        pass

    pending = _sb_get("owner_approval_queue?status=eq.pending&select=id&limit=50")
    failed = _sb_get("job_events?status=eq.failed&select=id,agent_name,created_at&order=created_at.desc&limit=20")
    workers = _sb_get("worker_heartbeats?select=worker_id,status,last_seen_at&order=last_seen_at.desc&limit=8")

    digest_items = _sb_get(
        "hermes_aggregates?event_source=eq.digest_collector&classification=eq.digest_item"
        "&select=event_type,aggregated_summary,created_at&order=created_at.desc&limit=200"
    )
    grouped: dict[str, list[str]] = defaultdict(list)
    for item in digest_items:
        grouped[str(item.get("event_type") or "operations_digest")].append(str(item.get("aggregated_summary") or ""))

    telemetry_rollups = _sb_get(
        "hermes_aggregates?event_source=eq.executive_telemetry"
        "&event_type=in.(daily_trading_rollup,daily_business_rollup,daily_recommendation_rollup,daily_system_rollup)"
        "&select=event_type,aggregated_summary,created_at&order=created_at.desc&limit=20"
    )
    latest_rollup: dict[str, str] = {}
    for row in telemetry_rollups:
        et = str(row.get("event_type") or "")
        if et and et not in latest_rollup:
            latest_rollup[et] = str(row.get("aggregated_summary") or "")[:220]

    lines = [
        "<b>CEO Daily Executive Summary</b>",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        trading.get("text", "Trading digest unavailable."),
        "",
        business.get("text", "Business digest unavailable."),
        "",
        grants.get("text", "Grants digest unavailable."),
        "",
        "<b>Grouped Digests (suppressed routine events)</b>",
        f"Trading digest items: {len(grouped.get('trading_digest', []))}",
        f"Business digest items: {len(grouped.get('business_digest', []))}",
        f"Grants digest items: {len(grouped.get('grants_digest', []))}",
        f"Operations digest items: {len(grouped.get('operations_digest', []))}",
        "",
        "<b>Telemetry Readiness (Daily Rollups)</b>",
        latest_rollup.get("daily_trading_rollup", "Trading rollup pending; collect completed trade outcomes with metadata."),
        latest_rollup.get("daily_business_rollup", "Business rollup pending; capture launch + ROI outcomes."),
        latest_rollup.get("daily_recommendation_rollup", "Recommendation rollup pending; capture approval/execution outcomes."),
        latest_rollup.get("daily_system_rollup", "System rollup pending; capture repeated bottlenecks and job failures."),
        latest_rollup.get("daily_credit_rollup", "Credit rollup pending; capture score velocity + dispute outcomes."),
        latest_rollup.get("daily_funding_rollup", "Funding rollup pending; capture approvals/denials + profile readiness."),
        latest_rollup.get("daily_client_success_rollup", "Client success rollup pending; capture onboarding/engagement/progression telemetry."),
        "",
        "<b>Credit & Funding Intelligence</b>",
        credit_line,
        funding_line,
        "<b>Client Success Intelligence</b>",
        client_line,
        "<b>Review Diagnostics</b>",
        review_line,
        "",
        "<b>Operations Digest</b>",
        f"Failed jobs (recent): {len(failed)}",
        f"Pending approvals: {len(pending)}",
        f"Worker health samples: {len(workers)}",
        "Recommended next actions:",
        "1) Address highest-risk strategy and run the next experiment.",
        "2) Approve top business opportunity website brief for build queue.",
        "3) Clear pending approvals and failed automation root causes.",
    ]
    final = "\n".join(lines)[:3900]
    if PERSIST_BRIEFS and SUPABASE_URL and SUPABASE_KEY:
        try:
            body = json.dumps({
                "briefing_type": "daily_ceo_digest",
                "content": final,
                "urgency": "medium",
                "generated_by": "chief_of_staff",
            }).encode()
            req = urllib.request.Request(
                f"{SUPABASE_URL}/rest/v1/executive_briefings",
                data=body,
                method="POST",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass
    return final


def build_weekly_focus() -> str:
    trading = build_trading_digest(hours=24 * 7)
    business = build_business_digest(hours=24 * 7)
    grants = build_grants_digest(days=21)
    failed = _sb_get("job_events?status=eq.failed&select=id&limit=200")
    pending = _sb_get("owner_approval_queue?status=eq.pending&select=id&limit=100")

    ranked_text = ""
    top_rank = "n/a"
    try:
        from ceo_agent.recommendation_queue import ranked_recommendations

        ranked = ranked_recommendations(limit=5)
        if ranked:
            payload = ranked[0].get("payload") or {}
            top_rank = f"{payload.get('recommendation_type','unknown')} — {payload.get('title','untitled')}"
    except Exception:
        pass

    strategy_line = _strategy_data_guidance()
    metrics = trading.get("metrics") or []
    if metrics:
        strategy_line = f"{metrics[0]['strategy']} (consistency {metrics[0]['consistency']}, PF {metrics[0]['profit_factor']})"

    business_top = "No business opportunity data"
    business_readout = "No practical launch candidate in the current window."
    btop = business.get("top")
    if btop:
        business_top = f"{btop.get('title','Untitled')} ({btop.get('composite','?')})"
        business_readout = _business_readout(btop)

    credit_focus = "Credit outcomes sparse; prioritize telemetry capture on disputes/utilization deltas this week."
    funding_focus = "Funding outcomes sparse; prioritize clean application + readiness outcome capture this week."
    client_focus = "Client success telemetry sparse; prioritize outreach + onboarding completion tracking this week."
    try:
        from ceo_agent.credit_funding_intelligence import credit_strategies_improve_scores_fastest, profile_patterns_succeed
        from ceo_agent.client_success_intelligence import highest_momentum_clients

        credit_focus = credit_strategies_improve_scores_fastest()
        funding_focus = profile_patterns_succeed()
        client_focus = highest_momentum_clients()
    except Exception:
        pass

    lines = [
        "<b>Weekly CEO Focus</b>",
        "Top 3 this week:",
        "1) Clear approval bottlenecks on launch-ready opportunities (unblocks execution speed this week).",
        "2) Stabilize repeated automation failures (protects delivery reliability and trust).",
        "3) Run one controlled strategy experiment on weakest setup (improves trading signal quality).",
        "",
        "Urgent now:",
        f"- Operational load: {len(failed)} failed jobs and {len(pending)} pending approvals require immediate triage.",
        "",
        "Strategic next:",
        f"- Highest ROI opportunity: {business_top}",
        f"- Launchability profile: {business_readout}",
        f"- Trading intelligence: {strategy_line}",
        f"- Credit intelligence: {credit_focus}",
        f"- Funding intelligence: {funding_focus}",
        f"- Client success intelligence: {client_focus}",
        "Delegate to AI employees: approval packet drafting, root-cause logs, scoring refresh, and launch QA prep.",
        f"Current top-ranked recommendation: {top_rank}",
    ]
    return "\n".join(lines)


def best_performing_strategy() -> str:
    metrics = build_trading_digest(hours=24 * 14).get("metrics") or []
    if not metrics:
        return (
            "<b>Strategy Performance Intelligence</b>\n"
            f"{_strategy_data_guidance()}\n"
            "Next action: run one standardized 7-day paper-trading cycle and log outcomes by strategy_id."
        )
    best = metrics[0]
    worst = metrics[-1]
    return (
        "<b>Strategy Performance Intelligence</b>\n"
        f"Best: {best['strategy']} | win {best['win_rate']}% | PF {best['profit_factor']} | consistency {best['consistency']}\n"
        f"Should scale/backtest more: {best['strategy']}\n"
        f"Should consider retirement: {worst['strategy']} (PF {worst['profit_factor']}, drawdown {worst['drawdown']})"
    )


def stop_doing_recommendation() -> str:
    metrics = build_trading_digest(hours=24 * 14).get("metrics") or []
    if not metrics:
        return (
            "No recurring underperformance pattern detected yet. "
            f"Collect {MIN_TRADES_FOR_RANKING}+ completed trades before making retirement calls."
        )
    weak = [m for m in metrics if m.get("profit_factor", 0) < TRADING_MIN_PROFIT_FACTOR or m.get("consistency", 1) < TRADING_MIN_CONSISTENCY]
    if not weak:
        return "No recurring underperformance pattern detected yet. Continue controlled experiments with fixed risk limits."
    top = weak[0]
    return f"Stop doing: over-allocating to {top['strategy']} until backtest + risk adjustments pass."


def automate_next_recommendation() -> str:
    b = build_business_digest(hours=24 * 7)
    ranked = b.get("ranked") or []
    if not ranked:
        return "No clear automation wedge detected this week. Continue collecting workflow-friction events for 7 more days."
    top = ranked[0]
    top_title = top.get('title', 'top business opportunity')
    confidence = top.get('confidence', 'baseline')
    return (
        "Automate next: lead qualification + onboarding workflow for "
        f"{top_title} using AI handoff + CRM updates. "
        "Why now: this removes repetitive operator load and speeds response times. "
        "Expected impact: faster conversion and cleaner pipeline handoffs. "
        f"Confidence: {confidence}."
    )
