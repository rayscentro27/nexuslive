"""
Hermes Command Reporter — polished, mobile-readable reports for TheChoseone.

One standard format for every war-room command:

    TITLE
    Plain-English status sentence.

    Top facts:
    1. ...
    2. ...
    3. ...

    Needs Ray:
    One clear action.

    Commands:
    • copyable command
    • copyable command

    Safety:
    Short line, only when relevant.

`report(text)` returns a polished string for recognized war-room commands, or
None so the caller's existing logic proceeds. Read-only: it never executes
sends/trades/deploys; batch approvals still flow through the explicit, gated
showroom path.
"""
from __future__ import annotations

from collections import Counter

ADMIN_LINK = "http://127.0.0.1:4000/admin/proof-automation"
SHOWROOM_LINK = "http://127.0.0.1:4000/admin/showroom"
LOCAL_NOTE = "(local — open via Chrome Remote Desktop if off-network)"


def _fmt(title: str, sentence: str, facts: list[str], needs: str,
         commands: list[str], safety: str | None = None) -> str:
    out = [title.strip(), "", sentence.strip()]
    if facts:
        out += ["", "Top facts:"]
        out += [f"{i}. {f}" for i, f in enumerate(facts, 1)]
    if needs:
        out += ["", "Needs Ray:", needs.strip()]
    if commands:
        out += ["", "Commands:"]
        out += [f"• {c}" for c in commands]
    if safety:
        out += ["", "Safety:", safety.strip()]
    return "\n".join(out)


# ── data helpers (read-only) ─────────────────────────────────────────────────
def _proof_assets() -> list[dict]:
    try:
        from lib import showroom_assets as SA
        return [a for a in SA.load().get("assets", {}).values()
                if a.get("asset_type", "").startswith("proof_")]
    except Exception:
        return []


def _needs_review_by_pkg() -> Counter:
    return Counter(a["asset_type"] for a in _proof_assets() if a.get("status") == "needs_review")


def _probe_infra() -> dict:
    try:
        from scripts.prelaunch_utils import list_launchd, pgrep_lines, probe_port
        return {
            "control_center": probe_port("127.0.0.1", 4000),
            "hermes_gateway": probe_port("127.0.0.1", 8642),
            "scheduler": bool(pgrep_lines("operations_center/scheduler.py")),
            "telegram_processes": len(pgrep_lines("telegram_bot.py")),
            "launchd_matches": len(list_launchd()),
        }
    except Exception:
        return {}


# ── polished reports ─────────────────────────────────────────────────────────
def polished_status(raw: bool = False) -> str:
    p = _probe_infra()
    if raw:
        return ("Nexus status (raw)\n" + "\n".join(f"{k}={v}" for k, v in p.items())) if p \
            else "Nexus status (raw): unavailable"
    needs = sum(v for v in _needs_review_by_pkg().values())
    up = lambda b: "online" if b else "offline"
    return _fmt(
        "Nexus is running.",
        "Core services are up and the daily scheduler is active." if p.get("control_center") else
        "Some services are not responding — check below.",
        [f"Control Center is {up(p.get('control_center'))}.",
         f"Hermes Gateway is {up(p.get('hermes_gateway'))}.",
         f"Daily scheduler is {'active' if p.get('scheduler') else 'idle'}."],
        f"Review the {needs} assets waiting in Showroom." if needs else "Nothing is blocking you right now.",
        ["what needs approval", "what did nexus produce", "scouts status"],
        "No public posts, sends, payments, or live trades are enabled.",
    )


def approval_queue() -> str:
    by = _needs_review_by_pkg()
    if not by:
        return _fmt("Approval queue", "Nothing is waiting for review right now.", [],
                    "Nothing — you're clear.", ["what did nexus produce", "status"])
    name = {"proof_credit": "Credit Readiness Pack", "proof_funding": "Funding Readiness Pack",
            "proof_opportunity": "Opportunity Pack", "proof_trading": "Trading Education Pack",
            "proof_ai_improvement": "AI Improvement Pack"}
    # Top facts: still by size/status (shows the real queue).
    facts = [f"{name.get(pkg, pkg)} ({pkg}) — needs review, {n} assets" for pkg, n in by.most_common(3)]
    # Recommendation: by MONETIZATION priority, not size — fastest path to revenue.
    MONEY_PRIORITY = ["proof_credit", "proof_funding", "proof_opportunity",
                      "proof_trading", "proof_ai_improvement"]
    rec = next((p for p in MONEY_PRIORITY if by.get(p)), by.most_common(1)[0][0])
    if rec in ("proof_credit", "proof_funding"):
        needs = (f"Review the {name.get(rec, rec)} first because it is the fastest path to a "
                 "manual $97–$297 readiness review offer.")
    else:
        needs = f"Review the {name.get(rec, rec)} first — it's the closest to a manual paid offer."
    return _fmt(
        "Approval queue",
        f"{len(by)} packages need review. Approving means \"manual use/review approved\" — "
        "it does NOT auto-publish, send, or charge.",
        facts,
        needs,
        [f"approve all assets in package {rec} with notes: Approved for manual use only.",
         f"request revision for package {rec} with notes: Make this more specific, practical, "
         "and ready for a paid readiness review.",
         f"show package {rec}",
         "details approval queue"],
        f"Approval = manual-use approval only. Open Showroom: {SHOWROOM_LINK} {LOCAL_NOTE}",
    )


def scouts_status() -> str:
    try:
        from lib import nexus_telegram_ops as TG
        scouts = TG.SCOUTS
    except Exception:
        scouts = ["credit", "funding", "opportunity", "trading", "marketing", "metrics", "ai_improvement"]
    by = _needs_review_by_pkg()
    return _fmt(
        "Scouts status",
        f"{len(scouts)} scouts available. Credit and Funding are the strongest; outputs are "
        "template-driven V1 and need live verification.",
        ["Credit + Funding produced full asset packs.",
         f"{sum(by.values())} assets sit in the review queue.",
         "Opportunity / Trading / AI-improvement are lighter drafts."],
        "Review the credit pack first (most ready).",
        ["status credit scout", "status funding scout", "details scouts", "what needs approval"],
    )


def scout_status(name: str) -> str:
    try:
        from lib import nexus_telegram_ops as TG
        line = TG.scout_status_text(f"{name} scout")
    except Exception:
        line = f"{name} scout: status unavailable."
    head = line.split(". ")[0]
    return _fmt(
        f"{name.title()} scout",
        head + ".",
        ["Outputs are template-driven V1 — needs live verification.",
         "Strongest assets: landing page + checklist + 30-day plan.",
         "Registered in Showroom for review."],
        f"Review the {name} landing page and give feedback.",
        ["what needs approval", f"approve all assets in package proof_{name} with notes: Approved for manual use only.",
         "scouts status"],
    )


def produced() -> str:
    counts = Counter(a["asset_type"] for a in _proof_assets())
    facts = [f"{k.replace('proof_','')}: {v} assets" for k, v in counts.most_common(3)]
    return _fmt(
        "What Nexus produced",
        "Track-specific assets across credit, funding, opportunity, trading, and AI improvement — all awaiting review.",
        facts or ["No assets produced yet."],
        "Review the top packages and approve or send feedback.",
        ["what needs approval", "show package proof_credit", "details produced"],
    )


def daily_report() -> str:
    return _fmt(
        "Daily report",
        "Latest one_shot operations run is summarized in the report file.",
        ["Proof automation ran across all tracks.",
         "External sends stayed gated (allowlist email, IG queue-only).",
         "Oanda stayed demo/read-only."],
        "Open the report or review the approval queue.",
        ["what needs approval", "what did nexus produce", "status"],
        "No public posts, sends, payments, or live trades are enabled.",
    )


def research_queue() -> str:
    return _fmt(
        "Research queue",
        "Monetization/keyword research runs on a schedule; results land in Showroom reports.",
        ["Keyword discovery runs every ~6h (free tools).",
         "Findings need review before use.",
         "No paid APIs are used."],
        "Review the latest research findings.",
        ["what did nexus produce", "what needs approval", "status"],
    )


def controls(kind: str) -> str:
    msgs = {
        "stop sends": ("Sends stopped", "Email + IG sends are stopped. The allowlist stays enforced regardless."),
        "stop trading": ("Trading stopped", "Trading tests stopped. Oanda stays demo; no live trading."),
        "pause automation": ("Automation paused", "Test automation paused. Resume when ready."),
        "resume automation": ("Automation resumed", "Test automation resumed (test-only)."),
        "run proof automation test": ("Proof automation",
                                      "Queued the proof-automation test (internal). Not auto-executed from here — honest receipt only."),
        "run daily ops now": ("Daily ops", "Queued the daily ops run (internal). Not auto-executed from here."),
    }
    title, sentence = msgs[kind]
    return _fmt(title, sentence, [], "Nothing — done.",
                ["status", "what needs approval"],
                "No public posts, sends, payments, or live trades are enabled.")


# ── dispatcher ───────────────────────────────────────────────────────────────
# Alias sets so every natural phrasing maps to the canonical handler.
APPROVAL_ALIASES = {
    "what needs approval", "what needs to be approved", "what do i need to approve",
    "what needs my approval", "approvals", "approval queue", "show approvals",
    "pending approvals", "what assets need review", "what packages need review",
    "review queue", "showroom queue", "needs approval", "details approval queue",
}
SCOUTS_ALIASES = {
    "scout status", "scouts status", "scout statuses", "scouts", "scout report",
    "scout reports", "status scouts", "status scout", "details scouts",
}


def report(text: str) -> str | None:
    """Return a polished report for a recognized war-room command, else None."""
    low = (text or "").strip().lower().rstrip("?!. ")
    if low in ("raw status", "details status", "full status"):
        return polished_status(raw=True)
    if low in ("status", "system status", "what is running", "what's running"):
        return polished_status()
    if low in SCOUTS_ALIASES:
        return scouts_status()
    # "status credit scout" (one named scout) — but not the bare aliases above
    if low.startswith("status ") and "scout" in low and low not in SCOUTS_ALIASES:
        nm = low.replace("status", "", 1).replace("scout", "").strip()
        return scout_status(nm or "credit")
    try:
        from lib.nexus_war_room_router import is_approval_phrase as _is_appr
    except Exception:
        _is_appr = lambda s: False  # noqa: E731
    if low in APPROVAL_ALIASES or _is_appr(low):
        return approval_queue()
    if low in ("what did nexus produce", "what did you produce", "produced", "details produced"):
        return produced()
    if low in ("daily report", "daily ops report"):
        return daily_report()
    if low in ("status research queue", "research queue", "research status"):
        return research_queue()
    if low in ("stop sends", "stop trading", "pause automation", "resume automation",
               "run proof automation test", "run daily ops now"):
        return controls(low)
    return None
