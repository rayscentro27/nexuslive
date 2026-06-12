"""
TheChoseone — Worker Router + mobile reporter.

Classifies a command, applies safety gates, routes to the correct handler, and
returns an HONEST mobile-friendly report. For worker (Codex/Claude/OpenCode)
tasks it reports the real state of the bridge:

  A. bridge live  -> "Task routed to <worker>. Job ID: <id>."
  B. not connected -> "I cannot run <worker> from Telegram yet. Queued + copy/paste prompt."
  C. blocked      -> "Blocked: would publish/send/spend/trade without approval."

Never claims a worker ran when it did not. Reuses existing systems:
  - nexus_telegram_ops (status/scout/approval/produced mobile reports)
  - showroom_assets.review_batch (approvals — explicit package id only)
  - ai_task_dispatch.create_task (queue) + hermes_agent_handoff_builder (copy/paste)
  - hermes_dev_agent_bridge (is CLI execution actually enabled?)
"""
from __future__ import annotations

import re

from lib import nexus_telegram_ops as TG
from lib import thechosenone_execution_truth as TRUTH

ADMIN_LINK = "http://127.0.0.1:4000/admin/proof-automation"
SHOWROOM_LINK = "http://127.0.0.1:4000/admin/showroom"

# Words that mean a real outward/irreversible action — gate these.
_RISKY = ("publish", "post to", "send email", "send dm", "deploy", "go live",
          "pay ", "payment", "charge", "invoice link", "place live trade",
          "live trading", "fund the account", "wire money", "transfer money")

_WORKERS = {"codex": "codex", "claude": "claude", "opencode": "opencode"}


def _bridge_live(worker: str) -> bool:
    """True only if the dev-agent CLI bridge is actually enabled to execute."""
    try:
        from lib import hermes_dev_agent_bridge as B
        return bool(B.bridge_enabled()) and bool(getattr(B, "execution_enabled", lambda: False)())
    except Exception:
        return False


def _link_line() -> str:
    return f"Open: {ADMIN_LINK}  ·  (local only — open via Chrome Remote Desktop if off-network)"


def classify(text: str) -> tuple[str, str]:
    """Return (intent, worker_target). Intent drives the handler."""
    low = (text or "").strip().lower()
    for w, tgt in _WORKERS.items():
        if low.startswith(f"task for {w}:") or low.startswith(f"task for {w} "):
            return "worker_task", tgt
    if low.startswith("run this prompt:") or low.startswith("run prompt:"):
        return "worker_task", "external_unknown"
    if re.match(r"^\s*(approve all assets in package|approve package|request revision for package)\b", low):
        return "approval", "showroom"
    if low.startswith("show package"):
        return "show_package", "showroom"
    if "what needs approval" in low or low == "needs approval":
        return "approval_queue", "showroom"
    if low in ("status", "what is running", "what's running"):
        return "status", "internal_script"
    if "scouts status" in low or low == "scout status":
        return "scouts_status", "internal_script"
    if low.startswith("status") and "scout" in low:
        return "scout_status", "internal_script"
    if low.startswith("run ") and "scout" in low:
        return "run_scout", "proof_automation"
    if "what did nexus produce" in low or "what did you produce" in low:
        return "produced", "internal_script"
    if low in ("daily report",) or "daily report" in low:
        return "report", "internal_script"
    if low in ("run proof automation test", "run proof automation"):
        return "run_proof", "proof_automation"
    if low in ("run daily ops now", "run daily ops"):
        return "run_daily_ops", "proof_automation"
    if low in ("pause automation", "pause", "resume", "resume automation",
               "stop sends", "stop trading"):
        return "control", "internal_script"
    return "unknown", "none"


def _safety_gate(text: str, intent: str) -> tuple[bool, str]:
    """Return (allowed, reason). Risky outward actions are blocked unless they are
    the already-gated internal controls (stop trading/sends are SAFE controls)."""
    low = (text or "").lower()
    if intent in ("control",):
        return True, "internal control (safe)"
    for kw in _RISKY:
        if kw in low:
            return False, f"would {kw.strip()} without approval"
    return True, "ok"


def route_or_block_command(text: str, source: str = "telegram", user: str = "ray") -> dict:
    """Main entry. Creates a receipt, routes/gates, returns {receipt, report}."""
    rec = TRUTH.create_command_receipt(text, source=source, user=user)
    intent, target = classify(text)
    TRUTH.update_command_receipt(rec, parsed_intent=intent, worker_target=target,
                                 execution_state="parsed")

    allowed, reason = _safety_gate(text, intent)
    if not allowed:
        TRUTH.update_command_receipt(rec, execution_state="blocked",
                                     safety_gate_result=f"blocked: {reason}",
                                     next_action="Rephrase or request explicit approval.")
        return {"receipt": rec, "report": _fmt(rec,
                f"🚫 Blocked: this would {reason}.", "I did not run it.",
                "If you want this, approve it explicitly first.")}
    TRUTH.update_command_receipt(rec, safety_gate_result="ok")

    if intent == "worker_task":
        return _handle_worker_task(rec, text, target)
    if intent == "approval":
        return _handle_approval(rec, text)
    if intent == "approval_queue":
        return _internal(rec, "Approvals", TG.mobile_approval_queue(), worker="showroom")
    if intent == "status":
        return _internal(rec, "Nexus status", TG.mobile_status())
    if intent in ("scouts_status",):
        return _internal(rec, "Scouts", _scouts_overview())
    if intent == "scout_status":
        return _internal(rec, "Scout", TG.command_report(text))
    if intent == "produced":
        return _internal(rec, "Produced", TG.what_produced_text())
    if intent == "report":
        return _internal(rec, "Daily report", "Open: reports/showroom/nexus_continuous_operations_status.md\n"
                         + TG._safety_line())
    if intent in ("run_scout", "run_proof", "run_daily_ops"):
        return _handle_run(rec, text, intent)
    if intent == "show_package":
        pkg = text.split("show package", 1)[-1].strip()
        return _internal(rec, f"Package {pkg}", _show_package(pkg))
    if intent == "control":
        return _internal(rec, "Control", TG.command_report(text))
    # unknown
    TRUTH.update_command_receipt(rec, execution_state="report_ready",
                                 next_action="Try a known command.")
    return {"receipt": rec, "report": _fmt(rec, "I didn't recognize that command.",
            "Nothing was run.", "Try: status · what needs approval · run proof automation test")}


# ── handlers ──────────────────────────────────────────────────────────────────
def _handle_worker_task(rec: dict, text: str, worker: str) -> dict:
    prompt = re.split(r":", text, 1)[-1].strip() if ":" in text else text
    live = _bridge_live(worker) if worker in ("codex", "claude", "opencode") else False
    if live:
        # A. bridge live (not the case today, but honest if it ever is)
        try:
            from lib import ai_task_dispatch as D
            row = D.create_task(created_by=rec["user"], source="telegram_thechoseone",
                                title=f"{worker} task", instructions=prompt,
                                task_type="coding", assigned_worker=worker)
            job = str(row.get("id"))
        except Exception:
            job = "queue_error"
        TRUTH.update_command_receipt(rec, worker_target=worker, job_id=job,
                                     execution_state="routed_to_worker",
                                     next_action="I will post the report when complete.")
        TRUTH.verify_worker_handoff(rec)
        return {"receipt": rec, "report": _fmt(rec,
                f"Task routed to {worker}. Job ID: {job}.",
                "Worker bridge is LIVE.", "I'll post the report when it completes.")}
    # B. not connected — queue + copy/paste prompt (HONEST)
    job, handoff_path = _queue_and_handoff(rec, worker, prompt)
    TRUTH.update_command_receipt(rec, worker_target=worker, job_id=job,
                                 execution_state="queued", report_path=handoff_path,
                                 truth_note=f"{worker} CLI bridge not connected (execution OFF)",
                                 next_action="Copy the prepared prompt into the agent, or approve bridge setup.")
    return {"receipt": rec, "report": _fmt(rec,
            f"I can't directly run {worker} from Telegram yet (bridge execution is OFF).",
            f"Queued (job {job}) and prepared a copy/paste prompt.",
            f"Prompt: {handoff_path or 'prepared'}  ·  or approve worker-bridge setup.")}


def _queue_and_handoff(rec: dict, worker: str, prompt: str) -> tuple[str, str | None]:
    job = "local-only"
    try:
        from lib import ai_task_dispatch as D
        row = D.create_task(created_by=rec["user"], source="telegram_thechoseone",
                            title=f"{worker} task (manual)", instructions=prompt,
                            task_type="coding", assigned_worker=worker)
        job = str(row.get("id"))
    except Exception:
        job = "queue_unavailable"
    path = None
    try:
        from lib import hermes_agent_handoff_builder as H
        target = "claude_code" if worker == "claude" else ("codex" if worker == "codex" else "opencode")
        ho = H.build_handoff(target_agent=target,
                             task_summary=(prompt[:80] or "manual task"),
                             task_detail=prompt,
                             acceptance_criteria=["produce the named artifact", "no publish/send/deploy"],
                             dispatch_id=rec["command_id"], submitted_by=rec["user"])
        path = ho._data.get("file_path") or getattr(ho, "handoff_id", None)
    except Exception:
        path = None
    return job, path


def _handle_approval(rec: dict, text: str) -> dict:
    res = TG.parse_command(text)  # enforces explicit package id; never blanket-approves
    ok = res.get("type") == "batch_approval" and res.get("result", {}).get("ok")
    TRUTH.update_command_receipt(rec, worker_target="showroom",
                                 execution_state="worker_completed" if ok else "failed",
                                 job_id=res.get("result", {}).get("package_id"),
                                 next_action="Verify in Showroom." if ok else "Provide an explicit package id.")
    return {"receipt": rec, "report": _fmt(rec, res.get("reply", "approval processed"),
            "Showroom updated." if ok else "No change (needs explicit package id).",
            _link_line())}


def _handle_run(rec: dict, text: str, intent: str) -> dict:
    """Acknowledge run requests honestly. We do NOT auto-spawn here; we report how
    to run it (or that it's queued), never claim it finished."""
    cmd = {"run_scout": "python3 scripts/run_nexus_continuous_operations.py --mode one_shot",
           "run_proof": "python3 scripts/run_nexus_continuous_operations.py --mode one_shot",
           "run_daily_ops": "python3 scripts/run_nexus_daily_operations_report.py"}[intent]
    TRUTH.update_command_receipt(rec, worker_target="proof_automation",
                                 execution_state="queued",
                                 next_action=f"Run: {cmd}  (or approve auto-run).")
    return {"receipt": rec, "report": _fmt(rec,
            "Queued for the proof-automation runner (internal script).",
            "Not auto-executed from here — honest receipt created.",
            f"Run: {cmd}")}


def _internal(rec: dict, title: str, body: str, worker: str = "internal_script") -> dict:
    TRUTH.update_command_receipt(rec, execution_state="report_ready",
                                 worker_target=worker)
    return {"receipt": rec, "report": _fmt(rec, body, None, None, title=title)}


# ── views / formatting ──────────────────────────────────────────────────────
def _scouts_overview() -> str:
    lines = ["7 scouts available. Last run: see daily ops. Top status:"]
    for sc in TG.SCOUTS[:3]:
        lines.append(f"• {sc}: " + TG.scout_status_text(sc + " scout").split(". ")[0])
    lines += ["", "More: 'details scouts'. Stale-queue warning: assets in needs_review await approval."]
    return "\n".join(lines)


def _show_package(pkg: str) -> str:
    from lib import showroom_assets as SA
    assets = [a for a in SA.load().get("assets", {}).values() if a.get("asset_type") == pkg]
    if not assets:
        return f"No package '{pkg}'. Try 'what needs approval' for valid IDs."
    from collections import Counter
    by = Counter(a.get("status") for a in assets)
    return (f"Package {pkg}: {len(assets)} assets · " + ", ".join(f"{k}={v}" for k, v in by.items())
            + f"\nApprove: approve all assets in package {pkg} with notes: <text>\n" + _link_line())


def _fmt(rec: dict, summary: str, status_line: str | None,
         next_action: str | None, title: str | None = None) -> str:
    """Mobile report: ≤12 lines, title + summary + next + link/safety + receipt id."""
    head = title or "TheChoseone"
    lines = [f"*{head}*", summary.strip()]
    if status_line:
        lines.append(status_line)
    na = next_action or rec.get("next_action")
    if na:
        lines += ["", f"👉 {na}"]
    lines += ["", f"_state: {rec.get('execution_state')} · worker: {rec.get('worker_target')} · "
              f"id: {rec['command_id']}_  (‘details {rec['command_id']}’ for full receipt)"]
    return "\n".join(lines)


def details(command_id: str) -> str:
    rec = TRUTH.get_command_status(command_id)
    return TRUTH.summarize_execution_receipt(rec) if rec else f"No receipt {command_id}."
