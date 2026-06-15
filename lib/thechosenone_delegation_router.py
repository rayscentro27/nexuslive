"""
TheChoseone — delegation router.

Receives a structured prompt (from Hermes or a human), classifies it into a SAFE
route, decides the honest execution mode, and writes an execution-truth receipt.
It never performs outward/irreversible actions, and it never claims a worker ran
when no verified bridge exists.

Routes: research · showroom · proof_automation · codex · claude · opencode · trading · blocked

Composes existing infra:
  - lib/thechosenone_execution_truth.py   (receipts)
  - lib/hermes_advisor_web_research.py     (research handoff drafts)
  - lib/hermes_to_thechosenone_prompt_builder.py (copy/paste prompts)

Pure routing + receipt I/O only. No network, no paid APIs, no secrets in receipts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from lib import thechosenone_execution_truth as TRUTH

ROOT = Path(__file__).resolve().parent.parent
ROUTES_CONFIG = ROOT / "config" / "thechosenone_delegation_routes.json"

ROUTES = ["research", "showroom", "proof_automation", "codex", "claude",
          "opencode", "trading", "blocked"]
WORKER_ROUTES = ("codex", "claude", "opencode")

# Outward/irreversible actions — block unless explicitly approved elsewhere.
_BLOCK = re.compile(
    r"(?i)\b(send (an )?emails?|email the leads|send (a )?dms?|dm (the )?(prospects|leads)|"
    r"publish|post to|go live|deploy|pay\b|payment|charge\b|invoice link|wire money|"
    r"transfer money|place (a )?live trade|live trading|fund the account|approve all)\b"
)

# Light secret scrub for receipts (never store tokens/keys/ids).
_SECRET = re.compile(
    r"(?i)\b(token|api[_-]?key|secret|password|bearer|chat[_-]?id|"
    r"goclearonline|supabase|oanda\s*account)\b[\s:=]*\S+"
)
_LONGNUM = re.compile(r"\b\d{8,}\b")


# Negation cues that begin a *safety disclaimer* — risky verbs after these are
# the user telling us NOT to do them, so they must not trip the block gate.
_NEGATION_CUE = re.compile(r"(?i)\b(do not|don't|don t|do n't|never|without|no\s+(emails?|dms?|sends?))\b")


def _action_part(text: str) -> str:
    """Return only the part of the prompt before the first negation/safety cue.
    'create offer ... Do not publish, charge' -> 'create offer ...' (so the
    user's own 'do not publish' disclaimer does not get blocked)."""
    m = _NEGATION_CUE.search(text or "")
    return (text or "")[:m.start()] if m else (text or "")


def sanitize(text: str) -> str:
    """Strip obvious secrets/long ids so nothing sensitive lands in a receipt."""
    t = _SECRET.sub("[redacted]", text or "")
    t = _LONGNUM.sub("[redacted]", t)
    return t.strip()


def load_routes() -> dict:
    try:
        return json.loads(ROUTES_CONFIG.read_text()).get("routes", {})
    except Exception:
        return {}


def bridge_verified(worker: str) -> bool:
    """True only if a real, execution-enabled worker bridge exists. Default False
    (honest): codex/claude/opencode are dry_run_only until this proves otherwise."""
    try:
        from lib import hermes_dev_agent_bridge as B
        return bool(getattr(B, "bridge_enabled", lambda: False)()) and \
            bool(getattr(B, "execution_enabled", lambda: False)())
    except Exception:
        return False


def _extract_package(text: str) -> str:
    m = re.search(r"package\s+([A-Za-z0-9_\-]+)", text or "", re.I)
    return m.group(1) if m else ""


def classify_prompt(text: str) -> dict:
    """Return {intent, route, worker_target, safety, execution_mode, package?}.

    Safety is checked FIRST: an unsafe outward action is always 'blocked'."""
    raw = (text or "").strip()
    low = raw.lower()

    # 1) Safety gate first — outward/irreversible actions never route to a worker.
    #    Scan only the ACTION part so the user's own "Do not publish/charge"
    #    safety disclaimer does not falsely trip the block.
    mblock = _BLOCK.search(_action_part(low))
    if mblock:
        return {"intent": "unsafe_action", "route": "blocked", "worker_target": "none",
                "safety": f"blocked: would {mblock.group(0).strip()} without approval",
                "execution_mode": "blocked"}

    # 2) Explicit worker sends.
    for w in WORKER_ROUTES:
        if (low.startswith(f"send this to {w}:") or low.startswith(f"task for {w}:")
                or low.startswith(f"route to {w}:") or low.startswith(f"ask {w} to ")):
            live = bridge_verified(w)
            return {"intent": "worker_task", "route": w, "worker_target": w,
                    "safety": "safe",
                    "execution_mode": "queued" if live else "dry_run_only"}

    # 3) Showroom / monetization.
    if (low.startswith("create monetization task from package")
            or "turn package" in low or "into offer" in low or "into a paid offer" in low
            or low.startswith("review package")
            or low.startswith("create showroom package from")
            or low.startswith("create offer from")
            or ("offer" in low and ("package" in low or "proof_credit" in low))
            or "monetiz" in low):
        return {"intent": "monetization", "route": "showroom", "worker_target": "showroom",
                "safety": "safe", "execution_mode": "queued",
                "package": _extract_package(raw)}

    # 4) Proof automation (dry-run).
    if "proof automation" in low or low == "run proof automation dry run":
        return {"intent": "proof_automation", "route": "proof_automation",
                "worker_target": "proof_automation", "safety": "safe",
                "execution_mode": "dry_run_only"}

    # 5) Trading (education/demo only).
    if (low.startswith("backtest strategy idea:") or low.startswith("analyze trading strategy:")
            or "backtest" in low or "strategy idea" in low):
        return {"intent": "trading_analysis", "route": "trading",
                "worker_target": "internal_script", "safety": "safe",
                "execution_mode": "report_ready"}

    # 6) Research (default for info-seeking).
    if (low.startswith("run web research:") or low.startswith("research ")
            or low == "research" or "web research" in low
            or re.search(r"\b(find|look up|sources?|affiliate|requirements|payout|competitor)\b", low)):
        return {"intent": "research", "route": "research", "worker_target": "none",
                "safety": "safe", "execution_mode": _research_mode()}

    # 7) Fallback — treat as research handoff (safe, never executes).
    return {"intent": "unclassified", "route": "research", "worker_target": "none",
            "safety": "safe", "execution_mode": _research_mode()}


def _research_mode() -> str:
    """report_ready only if a safe live web provider is wired; else dry_run_only
    (honest: there is no verified provider today)."""
    try:
        from lib import hermes_advisor_web_research as WR
        return "report_ready" if WR.web_enabled() else "dry_run_only"
    except Exception:
        return "dry_run_only"


def _topic_after(text: str, *prefixes: str) -> str:
    low = (text or "")
    for p in prefixes:
        idx = low.lower().find(p)
        if idx >= 0:
            return low[idx + len(p):].strip(" :")
    return low.strip()


def _build_outputs(cls: dict, text: str) -> tuple[list[str], str | None]:
    """Return (what_i_will_return, artifact_path). Imports of builders are lazy
    so this module stays cheap to import."""
    route = cls["route"]
    if route == "research":
        from lib import hermes_advisor_web_research as WR
        topic = _topic_after(text, "run web research:", "research")
        draft = WR.draft_research_task(topic)
        return (["Source links",
                 "Summary of best affiliate offers",
                 "Payout/cost if available",
                 "Approval requirements",
                 "Compliance risks",
                 "Recommended next step"],
                None), draft  # type: ignore
    if route == "showroom":
        from lib import hermes_to_thechosenone_prompt_builder as PB
        pkg = cls.get("package") or _extract_package(text) or "(specify package id)"
        # Preserve exactly what Ray typed after the colon (incl. "$97–$297"
        # price ranges); otherwise use a default goal that names the price band.
        goal = (_topic_after(text, ":") if ":" in text
                else "Turn this into a $97–$297 manual Credit/Funding Readiness Review offer.")
        draft = PB.build_task_prompt(
            task=f"Turn package {pkg} into a reviewable paid offer.",
            goal=goal,
            context="Default monetization priority: Credit/Funding readiness first. "
                    "Compliance-safe; nothing published.",
            inputs=[f"Package: {pkg}", "Price band: $97–$297", "Channel: manual review only"],
            required_output=["Offer name + compliance-safe promise.",
                             "Deliverables + price options.",
                             "Draft showroom entry, not published.",
                             "A clear go/no-go recommendation for Ray."],
            success_criteria="Ray can approve/reject a concrete offer; nothing published, "
                             "charged, or emailed.",
            route="showroom")
        return (["A draft offer built from the package.",
                 "Price options + compliance-safe copy.",
                 "A showroom draft entry for your approval (not published)."],
                "reports/showroom/macmini_safe_mode_latest.md"), draft  # path is illustrative
    if route in WORKER_ROUTES:
        return (["A copy/paste prompt for the worker.",
                 "Honest status: dry_run_only (no verified bridge) or queued (bridge live).",
                 "An execution-truth receipt."], None), None
    if route == "proof_automation":
        return (["A dry-run of proof automation.",
                 "Execution-truth receipts for each step.",
                 "A summary of what WOULD run live."], None), None
    if route == "trading":
        return (["An education/demo analysis of the strategy idea.",
                 "Backtest-style reasoning (no live orders).",
                 "Clear note: nothing is traded with real money."], None), None
    return (["A written summary.", "A recommended next step."], None), None


def delegate(text: str, source: str = "telegram", user: str = "ray") -> dict:
    """Main entry. Classify → write receipt → return {receipt, response, draft}."""
    cls = classify_prompt(text)
    san = sanitize(text)

    rec = TRUTH.create_command_receipt(sanitize(text), source=source, user=user)
    (outputs, artifact), draft = _build_outputs(cls, text)

    # Map honest execution_mode to a TRUTH execution_state.
    state = {"queued": "queued", "dry_run_only": "dry_run_only",
             "report_ready": "report_ready", "blocked": "blocked"}[cls["execution_mode"]]

    TRUTH.update_command_receipt(
        rec,
        parsed_intent=cls["intent"],
        worker_target=cls["worker_target"],
        execution_state=state,
        safety_gate_result=cls["safety"],
        # extra delegation fields (receipt schema is open):
        original_prompt=san,
        sanitized_prompt=san,
        route=cls["route"],
        execution_mode=cls["execution_mode"],
        output_artifact_path=artifact,
        final_status=cls["execution_mode"],
        errors=[],
        report_path=artifact,
    )

    response = render_response(cls, outputs, rec, draft)
    return {"receipt": rec, "response": response, "classification": cls, "draft": draft}


def render_response(cls: dict, outputs: list[str], rec: dict, draft: str | None) -> str:
    """The fixed TheChoseone reply format."""
    if cls["route"] == "blocked":
        reason = cls["safety"].replace("blocked:", "").strip()
        lines = ["Blocked.", "", f"Reason: {reason}", "",
                 "Safe alternative:",
                 "I can draft a report, task, or review for you instead — say the word.",
                 "", "Receipt:", "logs/thechosenone/latest_command_receipt.json"]
        return "\n".join(lines)

    lines = ["Task received.", "", f"Route: {cls['route']}", "", "Status:",
             cls["execution_mode"], "", "What I will return:"]
    for i, o in enumerate(outputs, 1):
        lines.append(f"{i}. {o}")

    # Honest truth notes about provider / worker-bridge availability.
    if cls["route"] == "research" and cls["execution_mode"] == "dry_run_only":
        lines += ["", "Web research provider is not verified yet. Task recorded as dry_run_only."]
    if cls["route"] in WORKER_ROUTES and cls["execution_mode"] == "dry_run_only":
        lines += ["", "Worker bridge not verified. Task recorded as dry_run_only."]

    lines += ["", "Safety:",
              "No applications, emails, DMs, purchases, posts, paid APIs, approvals, "
              "or live actions will run.",
              "", "Receipt:", "logs/thechosenone/latest_command_receipt.json"]
    if draft:
        lines += ["", "Drafted task / prompt:", draft]
    return "\n".join(lines)
