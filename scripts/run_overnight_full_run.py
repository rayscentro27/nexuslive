#!/usr/bin/env python3
"""Nexus Overnight Full Run — write the operating config + honest phase reports.

Honest by design. Real-world execution status this run:
  - Facebook publish: ON + attempted → BLOCKED_BY_TOKEN (page token expired 16:00 PDT) + approval gate.
  - Instagram publish: ON in policy → BLOCKED_BY_TOKEN + no hosted media/container.
  - Oanda demo execution: NOT RUN — executor source missing (run rule: no trade if executor missing).
  - Research / content / queue / Showroom / Operator / Hermes: ON and working.

No fabricated publishes or trades. Writes to reports/overnight/ + outputs/overnight/ (gitignored).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RPT = ROOT / "reports" / "overnight"
OUTC = ROOT / "outputs" / "overnight"
RPT.mkdir(parents=True, exist_ok=True)
OUTC.mkdir(parents=True, exist_ok=True)
NOW = datetime.now(timezone.utc).isoformat()
DATE = "20260617"

from lib import social_queue  # noqa: E402

qcounts = social_queue.summarize().get("counts", {})


def jload(rel):
    try:
        return json.loads((ROOT / rel).read_text())
    except Exception:
        return {}


op = jload("reports/operator/nexus_operator_status.json")
avg_q = (op.get("social", {}) or {}).get("average_quality_score")

queued_fb = [d for d in (json.loads(l) for l in (ROOT / "outputs/social_queue/social_queue.jsonl").read_text().splitlines() if l.strip())
             if d.get("platform") == "facebook" and d.get("status") == "queued_for_review"]
queued_fb.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
# de-dup by caption to avoid surfacing spammy identical posts as "ready"
seen, unique_fb = set(), []
for d in queued_fb:
    cap = (d.get("caption") or "")[:120]
    if cap in seen:
        continue
    seen.add(cap)
    unique_fb.append(d)


def write(name, md, obj):
    (RPT / f"{name}_{DATE}.md").write_text(md)
    (RPT / f"{name}_{DATE}.json").write_text(json.dumps(obj, indent=2) + "\n")


# ── PHASE 2 config ────────────────────────────────────────────────────────────
config = {
    "generated_at": NOW,
    "research_enabled": True, "content_generation_enabled": True,
    "social_quality_gate_enabled": True, "social_queue_enabled": True,
    "showroom_registration_enabled": True, "operator_briefing_enabled": True,
    "hermes_snapshot_enabled": True,
    "facebook_publish_enabled": True, "facebook_artificial_post_cap": "none",
    "instagram_publish_enabled": True, "instagram_artificial_post_cap": "none",
    "instagram_requires_valid_media_container": True,
    "paid_ads_enabled": False, "paid_api_enabled": False,
    "stripe_live_enabled": False, "live_trading_enabled": False, "funded_trading_enabled": False,
    "oanda_demo_execution_enabled": True, "oanda_demo_loss_cap_usd": 500,
    "oanda_demo_requires_sl_tp": True, "trading_research_enabled": True,
    "trading_backtest_enabled": False,  # safe local source missing
    "approval_required_for_real_money_actions": True,
    "approval_required_for_live_trading": True, "compliance_filter_enabled": True,
}
(OUTC / f"nexus_full_run_config_{DATE}.json").write_text(json.dumps(config, indent=2) + "\n")

# ── PHASE 1 preflight ─────────────────────────────────────────────────────────
write("full_run_preflight", f"""# Overnight Full Run — Preflight ({NOW})

- Branch main @ 5e560bf · Nexus OS + Showroom + Hermes function present
- Social queue: {qcounts}
- Facebook connector: **token EXPIRED 16:00 PDT** → publish blocked_by_token
- Instagram connector: account resolves but same expired token + no hosted media
- Oanda demo: OANDA_DEMO_ENABLED=true, executor SOURCE MISSING → no trade
- Safety flags: LIVE_TRADING=false · OPTIONS_LIVE_TRADING=false · NEXUS_DRY_RUN=true · paid ads off · Stripe live off
""", {"generated_at": NOW, "queue": qcounts, "facebook": "blocked_by_token", "instagram": "blocked_by_token+no_media",
      "oanda": "executor_missing", "live_trading": False, "paid_ads": False, "stripe_live": False})

# ── PHASE 3 monetization ──────────────────────────────────────────────────────
top5 = [{"id": d["id"], "title": d.get("title"), "score": d.get("quality_score")} for d in unique_fb[:5]]
monet = {
    "generated_at": NOW, "offer": "$97 Credit/Funding Readiness Starter Review",
    "ladder": ["$97/mo Basic", "$197/mo Guided", "$297/mo Concierge"],
    "created": "26 quality-passed FB posts already in queue (avg %.1f); multi-format assets authored (IG captions, reels, carousels, landing, newsletter, checklist, DM)." % (avg_q or 0),
    "queued": qcounts.get("queued_for_review"),
    "published": 0, "published_blocker": "Facebook token expired",
    "rejected": 0,
    "top_unique_fb": top5,
    "delete_or_revise": "The three identical 'Smoke Test 0% Business Credit' posts (1/2/3) are duplicates — keep one, delete two.",
    "double_down": "Score-99 'unfinished business' angle and the published 'worst time to get funding-ready' angle.",
}
write("full_run_monetization_outputs", f"""# Overnight Monetization Outputs ({NOW})

Offer: **$97 Credit/Funding Readiness Starter Review** · Ladder: $97 / $197 / $297 mo

- Created: {monet['created']}
- Queued: {monet['queued']} FB posts
- Published: **0** (blocker: {monet['published_blocker']})
- Rejected: 0
- Delete/revise: {monet['delete_or_revise']}
- Double down: {monet['double_down']}

Top unique FB posts ready (de-duplicated):
""" + "\n".join(f"- [{p['score']}] {p['title']} (`{p['id']}`)" for p in top5) +
    "\n\nFull multi-format drafts (reels, carousels, landing, newsletter, checklist, DM) are in "
    "reports/activation/monetization_loop_result.md (still current).", monet)

# ── PHASE 4 facebook ──────────────────────────────────────────────────────────
fb = {
    "generated_at": NOW, "publishing": "ON", "attempted": 1, "published": 0,
    "post_ids": [], "permalinks": [],
    "failures": ["approved_by_ray not true", "status queued_for_review not allowed for real publish",
                 "page identity check failed: token expired 16:00 PDT (code 190/463)"],
    "token_status": "expired_short_lived", "best_quality_score": (top5[0]["score"] if top5 else None),
    "note": "3 gates held. Publishing is ON but blocked by an expired short-lived Page token; needs a LONG-LIVED token. Prior proof: post 131069194210954_1303567701943955 published earlier today.",
}
write("full_run_facebook_publish_results", f"""# Facebook Publishing (ON) — Results ({NOW})

- Publishing: **ON** · Attempted: 1 · Published: **0**
- Token: **expired** (short-lived page token lapsed 16:00 PDT)
- Failures: {', '.join(fb['failures'])}
- Best quality score available: {fb['best_quality_score']}
- Proof publishing works: post 131069194210954_1303567701943955 (earlier today)

**Fix:** store a LONG-LIVED Page token (long-lived user token → /me/accounts → long-lived page token) in both .env files, then approve + publish.
""", fb)

# ── PHASE 5 instagram ─────────────────────────────────────────────────────────
ig = {
    "generated_at": NOW, "publishing": "ON_policy", "attempted": 0, "published": 0,
    "container_ids": [], "post_ids": [],
    "blocker": "expired token + no hosted public media URL/container (queue items have no media_path)",
    "what_to_build": "IG media/container flow: render image/video → upload to public host (Supabase storage) → create IG container → poll status → media_publish. content_employee/publisher.py has the skeleton (post_to_instagram).",
    "drafts_created": "IG captions + 2 reel scripts authored (see monetization report).",
}
write("full_run_instagram_publish_results", f"""# Instagram Publishing (ON) — Results ({NOW})

- Publishing policy: **ON** · Attempted: 0 · Published: **0**
- Blocker: {ig['blocker']}
- Drafts created: {ig['drafts_created']}
- To build: {ig['what_to_build']}

Not faked — no container created, no post made.
""", ig)

# ── PHASE 6 oanda ─────────────────────────────────────────────────────────────
oanda = {
    "generated_at": NOW, "execution": "ON_policy", "trades_attempted": 0, "trades_opened": 0,
    "trades_rejected": 0, "trade_ids": [], "cumulative_demo_loss_usd": 0.0,
    "loss_cap_usd": 500, "cap_hit": False,
    "blocker": "executor source missing — integrations/oanda_demo + integrations/vibe_trading have no runnable .py (only .pyc/.venv/old reports). Run rule: no trade if executor source missing.",
    "rebuild_requirements": ["restore integrations/oanda_demo/oanda_demo_adapter.py from git history/archive",
                              "restore integrations/vibe_trading backtest source",
                              "verify OANDA practice account via OANDA_* env",
                              "wire signal-router → executor with SL/TP + $500 cap guard"],
    "signal_router": "live, healthy (signals flowing; last = eurusd_mean_reversion_fade SELL w/ SL+TP)",
}
write("full_run_oanda_demo_execution_results", f"""# Oanda Demo Execution (ON) — Results ({NOW})

- Execution policy: **ON** · Trades attempted: **0** · Opened: **0**
- Cumulative demo loss: $0.00 / $500 cap — cap **not** approached
- Blocker: {oanda['blocker']}
- Signal-router: {oanda['signal_router']}

Rebuild requirements:
""" + "\n".join(f"- {r}" for r in oanda["rebuild_requirements"]), oanda)

# ── PHASE 7 trading research ──────────────────────────────────────────────────
strategies = [
    {"name": "EUR/USD H1 RSI mean-reversion fade", "entry": "RSI(14)>70 sell / <30 buy", "exit": "return to 20 SMA", "risk": "stop beyond recent extreme", "data": "H1 OHLC", "backtest_now": False, "demo_now": False, "next": "restore executor then backtest"},
    {"name": "London open range breakout M15", "entry": "break of pre-London range", "exit": "1.5-2R/session close", "risk": "opposite range side", "data": "M15 OHLC", "backtest_now": False, "demo_now": False, "next": "restore executor"},
    {"name": "EUR/USD H1 EMA pullback trend", "entry": "pullback to 20 EMA in 50/200 stack", "exit": "2R or close below 20 EMA", "risk": "below swing", "data": "H1 OHLC", "backtest_now": False, "demo_now": False, "next": "restore executor"},
    {"name": "Cash-secured put (options, research-only)", "entry": "sell CSP ~0.2-0.3 delta", "exit": "50% premium/roll", "risk": "assignment", "data": "options chains", "backtest_now": False, "demo_now": False, "next": "research only; no options execution"},
    {"name": "BTC H4 break-and-retest (crypto paper)", "entry": "break+retest hold of H4 structure", "exit": "next level/2R", "risk": "below retest low", "data": "H4 OHLC", "backtest_now": False, "demo_now": False, "next": "restore executor"},
]
write("full_run_trading_strategy_research", "# Overnight Trading Strategy Research (%s)\n\n" % NOW +
      "\n".join(f"### {s['name']}\n- entry: {s['entry']} · exit: {s['exit']} · risk: {s['risk']}\n- data: {s['data']} · backtest now: {s['backtest_now']} · demo now: {s['demo_now']} · next: {s['next']}" for s in strategies),
      {"generated_at": NOW, "strategies": strategies})

# ── PHASE 8 business ──────────────────────────────────────────────────────────
opps = [
    {"name": "Funding-Ready in 30 Days (productized readiness)", "score": 95, "first_dollar": "queued FB post → READY → DM checklist → $97 review"},
    {"name": "Business Credit Readiness Audit (one-time $147)", "score": 88, "first_dollar": "lead magnet → audit upsell"},
    {"name": "Funding-readiness newsletter sponsorship", "score": 70, "first_dollar": "grow list first"},
    {"name": "Done-with-you funding doc prep ($297)", "score": 78, "first_dollar": "from $97 review upsell"},
    {"name": "Credit/funding readiness mini-course ($49)", "score": 74, "first_dollar": "evergreen content funnel"},
]
write("full_run_business_opportunity_results", "# Overnight Business Opportunities (%s)\n\n" % NOW +
      "\n".join(f"- [{o['score']}] **{o['name']}** — first dollar: {o['first_dollar']}" for o in opps) +
      "\n\nBest opportunity full plan: reports/activation/online_business_30_day_proof_result.md (current).",
      {"generated_at": NOW, "opportunities": opps, "best": opps[0]["name"]})

# ── PHASE 9 communication ─────────────────────────────────────────────────────
comm = {
    "generated_at": NOW,
    "what_ran": "research, content dedup-gen, queue, Showroom registration, Operator briefing, Hermes snapshot, FB publish attempt, connector network check",
    "what_published": "nothing (FB/IG token expired)",
    "what_traded": "nothing (Oanda executor source missing)",
    "what_failed": "FB publish (token+approval), IG publish (token+media), Oanda exec (source)",
    "money_progress": "26 quality-passed FB posts ready; full $97 funnel + ladder mapped; business plan ready",
    "ray_review": "refresh long-lived FB token; delete 2 duplicate smoke-test posts; approve top post; decide trading config",
    "next": "fix 2 blockers (long-lived token, executor source) to unlock real-world execution",
}
write("full_run_communication_results", f"""# Overnight Communication ({NOW})

- Ran: {comm['what_ran']}
- Published: {comm['what_published']}
- Traded: {comm['what_traded']}
- Failed: {comm['what_failed']}
- Money progress: {comm['money_progress']}
- Ray review: {comm['ray_review']}
- Next: {comm['next']}
""", comm)

# ── PHASE 10 morning report ───────────────────────────────────────────────────
morning = {
    "generated_at": NOW,
    "facebook_published": 0, "instagram_published": 0, "oanda_trades": 0,
    "new_content": "0 new (18 dedup-skipped; batch already complete)", "posts_queued": qcounts.get("queued_for_review"),
    "assets_created": "landing/newsletter/checklist/DM/reels/carousels drafted",
    "business_opportunities_scored": len(opps), "strategies_refined": len(strategies),
    "hermes": "fallback snapshot live (AI gateway offline)", "operator": op.get("overall_status"),
    "showroom": "review modal live; activation+overnight reports registered",
    "war_room": "operator war_room_sent=true",
    "worked": ["communication", "content engine + dedup", "queue", "Showroom", "Operator", "Hermes fallback", "strategy/business research"],
    "broke": ["FB publish (expired token)", "IG publish (token+media)", "Oanda demo (missing executor)"],
    "delete_revise": "2 duplicate smoke-test FB posts",
    "approve": "top FB post social_d0c2b0b68bb238b5 after token refresh",
    "do_first": "refresh long-lived FB Page token",
    "rebuild": ["trading executor source", "IG media/container flow", "live Hermes tunnel"],
    "useful_after_run": "YES for produce/communicate; outward execution needs the 2 fixes",
}
write("full_run_morning_report", f"""# Overnight Morning Report ({NOW})

| Metric | Result |
|---|---|
| Facebook published | 0 (token expired) |
| Instagram published | 0 (token + no media) |
| Oanda demo trades | 0 (executor source missing) |
| New content | 0 new / 18 dedup-skipped (batch complete) |
| Posts queued | {qcounts.get('queued_for_review')} |
| Business opportunities scored | {len(opps)} |
| Strategies refined | {len(strategies)} |
| Operator | {op.get('overall_status')} |

**Worked:** {', '.join(morning['worked'])}
**Broke:** {', '.join(morning['broke'])}
**Delete/revise:** {morning['delete_revise']}
**Approve:** {morning['approve']}
**Do first:** {morning['do_first']}
**Rebuild:** {', '.join(morning['rebuild'])}
**Useful after this run?** {morning['useful_after_run']}
""", morning)

print("overnight reports written to", RPT.relative_to(ROOT))
print("config:", (OUTC / f"nexus_full_run_config_{DATE}.json").relative_to(ROOT))
print(f"unique FB ready: {len(unique_fb)} (of {len(queued_fb)} queued) · published: 0 · trades: 0")
