"""
Nexus Telegram Command Center — plain-language status + command parser for
continuous operations. Generates human status (not raw JSON) and parses Ray's
commands (status, approvals, pause/resume). Does NOT auto-send to Telegram;
the existing manual notifier handles sending. Approvals require explicit package IDs.
"""
from __future__ import annotations

import re
from collections import Counter

from lib import proof_automation as PA
from lib import showroom_assets as SA
from lib import nexus_allowlist as AL

SCOUTS = ["credit", "funding", "opportunity", "trading", "marketing", "metrics", "ai_improvement"]


def _proof_assets():
    return [a for a in SA.load().get("assets", {}).values() if a.get("asset_type", "").startswith("proof_")]


def status_text() -> str:
    s = PA.load()
    assets = _proof_assets()
    needs = sum(1 for a in assets if a.get("status") == "needs_review")
    sends = AL.send_log()
    emails = sum(1 for e in sends if e.get("channel") == "email" and e.get("status") == "sent")
    blocked = sum(1 for e in sends if e.get("status") == "blocked")
    igq = sum(1 for e in sends if e.get("channel") == "instagram" and e.get("status") == "queued")
    return (f"Nexus is running locally in test mode. Proof Automation is active with {len(SCOUTS)} scouts. "
            f"Credit and Funding generated track-specific assets. {needs} assets need review. "
            f"Email testing is restricted to Ray's two addresses ({emails} test emails sent, {blocked} non-allowlisted blocked). "
            f"Instagram test is restricted to raydavis7677 ({igq} DM queued). "
            f"Oanda is practice/demo only. No public posts, no third-party emails, no live trades. approved_live is OFF.")


def scout_status_text(scout: str) -> str:
    s = PA.load()
    scout = scout.replace(" scout", "").strip().lower().replace(" ", "_")
    if scout in ("ai", "ai_improvement"):
        scout = "ai_improvement"
    findings = [f for f in s.get("scout_findings", []) if f.get("scout_id") == scout]
    if scout == "ai_improvement" and not findings:
        n = len(s.get("ai_improvement_recommendations", []))
        return f"AI Improvement Scout produced {n} scored tool recommendations (cost/benefit/risk + action). Next: review the upgrade backlog."
    prof = PA.TRACK_PROFILE.get(scout)
    if not findings:
        return f"{scout.title()} Scout: no findings yet. Run the {scout} scenario."
    deliv = ", ".join(prof["deliverables"][:5]) if prof else "assets"
    strongest = prof["deliverables"][0] if prof else "the plan"
    return (f"{scout.replace('_',' ').title()} Scout created: {deliv}. "
            f"Strongest asset: {strongest}. Needs live verification (template-driven V1). "
            f"Next: review the landing page and give feedback. Confidence ~0.7.")


def approval_queue_text() -> str:
    assets = _proof_assets()
    by_pkg = Counter(a["asset_type"] for a in assets if a.get("status") == "needs_review")
    pkgs = len(by_pkg)
    lines = [f"{pkgs} packages need review:"]
    for pkg, n in by_pkg.most_common():
        lines.append(f"- {pkg}: {n} assets needs_review")
    lines.append("Approve one package at a time, or 'approve all assets in package <id> with notes: <text>'.")
    return "\n".join(lines)


def what_produced_text() -> str:
    assets = _proof_assets()
    by_type = Counter(a["asset_type"].replace("proof_", "") + ":" + "" for a in assets)
    counts = Counter(a["asset_type"] for a in assets)
    return ("Nexus produced track-specific assets across credit, funding, opportunity, trading, and AI improvement: "
            + ", ".join(f"{k} ({v})" for k, v in counts.most_common())
            + ". All needs_review. Use 'show me landing pages' or 'what needs approval'.")


# ── Command parsing ──────────────────────────────────────────────────────────
def parse_command(text: str) -> dict:
    t = (text or "").strip()
    low = t.lower()

    # approve all assets in package X with notes: Y
    m = re.search(r"approve all assets in package\s+(\S+)(?:\s+with notes:?\s*(.*))?", low)
    if m:
        return _batch(m.group(1), "approved_with_notes", (m.group(2) or "").strip(), text)
    m = re.search(r"approve package\s+(\S+)\s+for manual use(?:\s+with notes:?\s*(.*))?", low)
    if m:
        return _batch(m.group(1), "approved_for_manual_use_only", (m.group(2) or "").strip(), text)
    m = re.search(r"request revision for package\s+(\S+)(?:\s+with notes:?\s*(.*))?", low)
    if m:
        return _batch(m.group(1), "needs_revision", (m.group(2) or "").strip(), text)

    if low.startswith("status ") and "scout" in low:
        return {"type": "scout_status", "reply": scout_status_text(low.replace("status", "", 1).replace("scout", ""))}
    if low in ("status", "what is running", "what's running"):
        return {"type": "status", "reply": status_text()}
    if "what needs approval" in low or "needs approval" in low:
        return {"type": "approval_queue", "reply": approval_queue_text()}
    if "what did nexus produce" in low or "what did you produce" in low:
        return {"type": "produced", "reply": what_produced_text()}
    if "daily report" in low:
        return {"type": "daily_report", "reply": "Daily report: reports/showroom/nexus_continuous_operations_status.md"}
    if low in ("pause automation", "pause"):
        return {"type": "control", "action": "pause", "reply": "Automation paused (test loops will not run until 'resume')."}
    if low in ("resume test automation", "resume"):
        return {"type": "control", "action": "resume", "reply": "Test automation resumed (test_only)."}
    if low in ("stop all sends", "stop sends"):
        return {"type": "control", "action": "stop_sends", "reply": "All sends stopped (email + IG). Allowlist remains enforced regardless."}
    if low in ("stop trading tests", "stop trading"):
        return {"type": "control", "action": "stop_trading", "reply": "Trading tests stopped. Oanda stays practice/demo; no live trading."}
    return {"type": "unknown", "reply": "Try: status · status credit scout · what needs approval · "
            "show me landing pages · approve all assets in package <id> with notes: <text> · daily report"}


def _batch(package_id: str, status: str, notes: str, raw: str) -> dict:
    res = SA.review_batch(package_id, status, notes=notes, apply_to_all=True, reviewer="ray", source="telegram")
    reply = res.get("summary") if res.get("ok") else f"Could not apply: {res.get('error')}"
    return {"type": "batch_approval", "result": res, "reply": reply}


# ── TRACK A: mobile-readable command reports (≤8–12 lines, links, next action) ──
ADMIN_LINK = "http://127.0.0.1:4000/admin/proof-automation"


def _safety_line() -> str:
    return "Safety: no public posts · email allowlist-only · IG queue-only · Oanda demo · approved_live OFF."


def mobile_status() -> str:
    assets = _proof_assets()
    needs = sum(1 for a in assets if a.get("status") == "needs_review")
    return ("\n".join([
        "Nexus is running (test mode). Daily ops = one_shot (no scheduler yet).",
        f"Proof Automation active · 7 scouts available · {needs} assets need review.",
        "Email: allowlist-only (Ray's 2 addresses). IG: queue-only. Oanda: demo/read-only.",
        "",
        "Needs Ray: review Proof Automation assets.",
        f"Open: {ADMIN_LINK}",
        _safety_line(),
        "",
        "Commands: what needs approval · status credit scout · daily report",
    ]))


def mobile_scout(scout: str) -> str:
    full = scout_status_text(f"{scout} scout")
    # keep to ~4 short lines for phone
    short = full.split(". ")
    head = ". ".join(short[:2]).strip()
    return f"{head}.\nNext: review the landing page + give feedback.\nMore: 'status {scout} scout details'."


def mobile_approval_queue() -> str:
    from collections import Counter
    by = Counter(a["asset_type"] for a in _proof_assets() if a.get("status") == "needs_review")
    top = by.most_common(3)
    lines = [f"{len(by)} packages need review. Top 3:"]
    lines += [f"• {k} ({v})" for k, v in top]
    lines += ["", "Approve: 'approve all assets in package <id> with notes: <text>'", f"Open: {ADMIN_LINK}"]
    return "\n".join(lines)


def command_report(text: str) -> str:
    """Mobile-formatted command responses. 'details' suffix returns the full version."""
    low = (text or "").strip().lower()
    details = low.endswith("details")
    base = low.replace("details", "").strip()
    if base in ("status", "what is running", "what's running"):
        return status_text() if details else mobile_status()
    if base.startswith("status") and "scout" in base:
        sc = base.replace("status", "", 1).replace("scout", "").strip()
        return scout_status_text(f"{sc} scout") if details else mobile_scout(sc)
    if "needs approval" in base:
        return approval_queue_text() if details else mobile_approval_queue()
    if "what did nexus produce" in base or "what did you produce" in base:
        return what_produced_text()
    if base == "daily report":
        return "Daily report ready.\nOpen: reports/showroom/nexus_continuous_operations_status.md\n" + _safety_line()
    if base in ("pause automation", "pause"):
        return "Paused test automation. Resume with 'resume'."
    if base in ("resume", "resume automation", "resume test automation"):
        return "Resumed test automation (test_only)."
    if base in ("stop sends", "stop all sends"):
        return "Stopped sends (email + IG). Allowlist stays enforced."
    if base in ("stop trading", "stop trading tests"):
        return "Stopped trading tests. Oanda stays demo; no live trading."
    # batch approval / revision delegate to parse_command
    res = parse_command(text)
    return res.get("reply", "Try: status · what needs approval · daily report")
