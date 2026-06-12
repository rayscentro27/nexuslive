"""
Hermes Mobile Conversation Bot — parallel, READ-ONLY prototype.

A conversational, phone-friendly Hermes that understands Ray + Nexus and helps
him think, decide, and direct work. It is intentionally ISOLATED from Nexus
writes: it can READ reports/logs/status + Ray-approved context docs and produce
a conversational answer, a summary, a proposed next action, an optional COMMAND
DRAFT for TheChoseone (the command bot), an optional PROMPT DRAFT, and an
optional MEMORY suggestion. It NEVER sends email/DMs, approves assets, executes
commands, trades, publishes, deploys, or spends money.

Design: deterministic V1 (no model call) so it runs free and offline. A provider
adapter (`generate`) is stubbed for a future, Ray-approved model/provider; until
then everything is template + live-state composition.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports" / "showroom"
LOGS = ROOT / "logs" / "proof_automation"
DOCS = ROOT / "docs" / "hermes_mobile"

# Hard read-only guarantee: this bot exposes no write/send/execute capability.
CAPABILITIES = {
    "read_reports": True, "read_logs": True, "read_context_docs": True,
    "write_nexus": False, "send_email": False, "send_dm": False,
    "approve_assets": False, "execute_commands": False, "trade": False,
    "publish": False, "deploy": False, "spend_money": False,
    "propose_actions": True, "draft_commands": True, "draft_prompts": True,
    "suggest_memory": True,
}
ADMIN_LINK = "http://127.0.0.1:4000/admin/proof-automation"


# ── read-only context loaders ────────────────────────────────────────────────
def _read(path: Path, limit: int = 4000) -> str:
    try:
        return path.read_text()[:limit]
    except Exception:
        return ""


def _ops_state() -> dict:
    p = LOGS / "continuous_ops_latest.json"
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _proof_assets() -> list[dict]:
    try:
        from lib import showroom_assets as SA
        return [a for a in SA.load().get("assets", {}).values()
                if a.get("asset_type", "").startswith("proof_")]
    except Exception:
        return []


def context_snapshot() -> dict:
    """Everything the bot is allowed to know, gathered read-only."""
    assets = _proof_assets()
    needs = [a for a in assets if a.get("status") == "needs_review"]
    by_pkg = Counter(a["asset_type"] for a in needs)
    ops = _ops_state()
    return {
        "assets_total": len(assets),
        "needs_review": len(needs),
        "packages": dict(by_pkg),
        "top_packages": by_pkg.most_common(3),
        "ops_mode": ops.get("mode"),
        "ops_at": ops.get("at"),
        "email_sends": ops.get("email", {}).get("sends", []),
        "instagram": ops.get("instagram", {}),
        "oanda": ops.get("oanda", {}),
        "scouts": list((ops.get("scouts") or {}).keys()) or
                  ["credit", "funding", "opportunity", "trading", "marketing", "metrics", "ai_improvement"],
    }


# ── intent classification ─────────────────────────────────────────────────────
INTENTS = [
    ("status", ["status", "what is nexus doing", "what's nexus doing", "what is running"]),
    ("attention", ["needs my attention", "what needs my attention", "what should i look at"]),
    ("scouts", ["scouts find", "scouts produce", "what did the scouts", "scout findings"]),
    ("explain", ["explain", "in plain english", "what does this report", "break down"]),
    ("decide", ["help me decide", "help me think", "should i", "what do you think"]),
    ("money30", ["make money in 30", "30 days", "revenue plan", "make money"]),
    ("improve", ["what should hermes improve", "improve nexus", "weakest part", "weakest"]),
    ("recall", ["what did i say", "earlier about", "what did we say"]),
    ("to_task", ["turn this into a task", "make this a task", "task for thechoseone", "task for the choseone"]),
    ("give_prompt", ["give me a prompt", "write a prompt", "prompt for"]),
    ("command_for_bot", ["what should thechoseone run", "command to approve", "give me the command", "command for"]),
    ("accomplished", ["what did we accomplish", "what did we get done", "what happened today", "accomplished today"]),
    ("approve_phone", ["what can i approve", "approve from my phone", "what can i approve from my phone"]),
    ("next", ["what should i do next", "what next", "next action"]),
]


def classify(text: str) -> str:
    low = (text or "").strip().lower()
    for intent, keys in INTENTS:
        if any(k in low for k in keys):
            return intent
    return "status" if low in ("status", "hi", "hey") else "open"


# ── response composition (conversational, mobile, no raw dumps) ───────────────
def _pkg_phrase(ctx: dict) -> str:
    tp = ctx["top_packages"]
    if not tp:
        return "nothing is waiting on you right now"
    return ", ".join(f"{k.replace('proof_','')} ({v})" for k, v in tp)


def respond(text: str) -> dict:
    """Main entry. Returns conversational answer + summary + proposed_action +
    optional command_draft / prompt_draft / memory_suggestion. READ-ONLY."""
    intent = classify(text)
    ctx = context_snapshot()
    out = {
        "intent": intent,
        "read_only": True,
        "answer": "",
        "summary": "",
        "proposed_action": "",
        "command_draft": None,   # a string Ray can paste to TheChoseone — NOT executed here
        "prompt_draft": None,
        "memory_suggestion": None,
        "links": [ADMIN_LINK],
    }

    if intent == "status":
        out["answer"] = (
            f"Nexus is up and in test mode. The last operations run was a one_shot "
            f"({ctx['ops_mode'] or 'one_shot'}), no scheduler yet. {ctx['needs_review']} assets "
            f"are waiting for your review — the biggest piles are {_pkg_phrase(ctx)}. "
            f"Email is allowlist-only to your two addresses, IG is queue-only, Oanda is demo/read-only."
        )
        out["summary"] = f"Running · {ctx['needs_review']} to review · all external actions gated."
        out["proposed_action"] = "Review the credit + funding packages, approve a batch or send feedback."
        out["command_draft"] = "status"

    elif intent == "attention":
        out["answer"] = (
            f"Two things really want you: (1) {ctx['needs_review']} proof assets sitting in needs_review "
            f"— mostly {_pkg_phrase(ctx)} — and (2) deciding whether to turn on a scheduler so the loop "
            f"runs without you. Nothing is on fire; nothing external has gone out."
        )
        out["summary"] = "Approvals pending + scheduler decision."
        out["proposed_action"] = "Approve the credit package (your strongest track), then decide on scheduling."
        out["command_draft"] = "what needs approval"

    elif intent == "scouts":
        out["answer"] = (
            "The scouts drafted track-specific material. Credit and Funding are the strongest — full "
            "landing pages, checklists, lead magnets, DM/email drafts, and a 30-day plan each. Opportunity, "
            "Trading, and AI-improvement produced lighter drafts. Everything is template-driven V1, so the "
            "claims still need live verification before anyone leans on them."
        )
        out["summary"] = f"{len(ctx['scouts'])} scouts · credit+funding strongest · needs live verification."
        out["proposed_action"] = "Read the credit landing page first; it's the most ready."
        out["command_draft"] = "status credit scout"

    elif intent == "explain":
        rpt = _read(REPORTS / "nexus_continuous_operations_status.md", 1500)
        out["answer"] = (
            "In plain English: Nexus ran one full pass of the whole system. It drafted assets for 5 "
            "scenarios, kept email locked to your two addresses (two test emails went out, a stranger "
            "address was blocked), queued an IG test instead of sending it, and only read Oanda in demo "
            "mode — no trade. The rest is waiting on your review. Nothing went public."
        )
        out["summary"] = "One safe pass: drafts made, sends gated, nothing public, review pending."
        out["proposed_action"] = "Skim the status report, then approve or give feedback."
        out["links"].append("reports/showroom/nexus_continuous_operations_status.md")
        if not rpt:
            out["answer"] += " (Tip: run the daily report generator to refresh the file.)"

    elif intent == "decide":
        out["answer"] = (
            "Here's how I'd frame it. Your strongest, most-proven lane is credit readiness — you know it "
            "cold and the assets are best there. Funding is a close second. I'd put energy into one lane, "
            "prove a real result (a person helped, a checklist used), and let that become the case study. "
            "Spreading across all 7 scouts dilutes the proof. Want me to draft the focused plan?"
        )
        out["summary"] = "Recommend: focus credit first, prove one real result, then expand."
        out["proposed_action"] = "Pick credit as lane #1; I'll outline the proof milestone."

    elif intent == "money30":
        out["answer"] = (
            "A realistic 30-day path, no hype: Week 1 — finalize the credit-readiness offer + landing page "
            "and your two-address email test becomes a real opt-in list. Week 2 — soft outreach to people "
            "who already know you (no cold outreach), offer the readiness review. Week 3 — deliver, collect "
            "one real testimonial/case study. Week 4 — add funding-readiness as the upsell. Revenue comes "
            "from a paid readiness review/consult — not from any automated payment yet (that stays gated)."
        )
        out["summary"] = "Focus one paid offer (credit readiness), warm audience, prove → upsell funding."
        out["proposed_action"] = "Approve the credit package so it's ready to show a warm lead."
        out["memory_suggestion"] = "30-day plan: credit readiness paid offer first, funding upsell wk4, warm audience only."

    elif intent == "improve":
        out["answer"] = (
            "Weakest part right now: the scouts are template-driven, so findings say 'needs live "
            "verification' — there's no real research feeding them yet. Second weakest: no scheduler, so "
            "everything is manual one_shot. Third: the conversation layer (me) is read-only and not on "
            "Telegram. The highest-leverage fix is wiring ONE scout (credit) to real, approved sources so "
            "its claims are trustworthy."
        )
        out["summary"] = "Weakest: template-only scouts (no live research). Fix credit scout first."
        out["proposed_action"] = "Approve a small, free research source for the credit scout."
        out["memory_suggestion"] = "Nexus weak spot 2026-06: scouts are template-only; prioritize live research for credit scout."

    elif intent == "recall":
        out["answer"] = (
            "I can only recall from approved context files and Nexus reports, not your private chats. From "
            "what's saved: you want Nexus to help people at scale and make money doing it, mobile-readable "
            "comms, proof over dashboards, aggressive build but no fake claims. Tell me the topic and I'll "
            "pull the matching note."
        )
        out["summary"] = "Recall limited to approved docs + reports (no private chat scraping)."
        out["proposed_action"] = "Name the topic; I'll surface the saved context."

    elif intent == "to_task":
        out["answer"] = (
            "Got it — here's that turned into a clean task for TheChoseone. I won't run it; you send it when "
            "you're ready."
        )
        out["summary"] = "Drafted a command for the command bot (not executed)."
        out["command_draft"] = "approve all assets in package proof_credit with notes: ship after Ray review"
        out["proposed_action"] = "Paste the command draft to TheChoseone if it looks right."

    elif intent == "give_prompt":
        out["answer"] = "Here's a ready-to-use prompt you can hand to Claude/OpenCode:"
        out["prompt_draft"] = (
            "Review the Nexus credit-readiness package (landing page, checklist, lead magnet, 30-day plan). "
            "Tighten copy for a mobile reader, remove any guaranteed-result language, and propose 3 "
            "improvements. Output: revised copy + a short changelog. Do not publish or send anything."
        )
        out["summary"] = "Prompt drafted (review/improve credit package, compliance-safe)."
        out["proposed_action"] = "Run the prompt in a review-only session."

    elif intent == "command_for_bot":
        out["answer"] = (
            "Here's the exact command for TheChoseone. I'm only drafting it — it won't execute until you "
            "send it to the command bot."
        )
        out["command_draft"] = "approve all assets in package proof_credit with notes: reviewed on mobile, approved"
        out["summary"] = "Command draft for batch-approving the credit package."
        out["proposed_action"] = "Send the draft to TheChoseone to approve."

    elif intent == "accomplished":
        em = ctx.get("email_sends", [])
        sent = sum(1 for e in em if e.get("status") in ("sent", "drafted"))
        out["answer"] = (
            f"Today Nexus ran a full safe pass: drafted assets across all tracks, processed {sent} "
            f"allowlisted email test(s), queued the IG test, read Oanda in demo, and left {ctx['needs_review']} "
            f"assets ready for your review. Nothing public, nothing spent."
        )
        out["summary"] = f"Full safe pass · {ctx['needs_review']} ready to review · zero external exposure."
        out["proposed_action"] = "Approve one package to convert today's drafts into something usable."

    elif intent == "approve_phone":
        out["answer"] = (
            f"From your phone you can batch-approve any package. Right now the queue is {_pkg_phrase(ctx)}. "
            f"Just tell TheChoseone to approve a package with a note — I'll draft it for you."
        )
        out["summary"] = "You can batch-approve packages by command; nothing auto-approves."
        out["command_draft"] = "approve all assets in package proof_credit with notes: approved from phone"
        out["proposed_action"] = "Approve credit first (strongest), then funding."

    elif intent == "next":
        out["answer"] = (
            "Next best move: approve the credit package (it's your strongest and most-ready), then decide "
            "whether to enable a scheduler so the loop runs on its own. After that, point one scout at real "
            "research so its findings stop saying 'needs verification'."
        )
        out["summary"] = "1) approve credit  2) decide scheduler  3) wire one scout to real research."
        out["command_draft"] = "what needs approval"
        out["proposed_action"] = "Start with the credit approval."

    else:  # open / unknown
        out["answer"] = (
            "I'm your conversation-side Hermes — I can explain what Nexus is doing, help you decide, draft "
            "tasks/commands for TheChoseone, or write you a prompt. I don't execute anything myself. "
            "Try: 'what needs my attention?', 'how do we make money in 30 days?', or 'turn this into a task.'"
        )
        out["summary"] = "Conversational, read-only assistant. Proposes; never executes."
        out["proposed_action"] = "Ask a question or say 'what needs my attention?'"

    return out


def format_for_telegram(resp: dict) -> str:
    """Render a respond() dict as a phone-friendly message (no raw dumps)."""
    lines = [resp["answer"].strip()]
    if resp.get("proposed_action"):
        lines += ["", f"👉 Next: {resp['proposed_action']}"]
    if resp.get("command_draft"):
        lines += ["", f"📋 Send to TheChoseone:\n  {resp['command_draft']}"]
    if resp.get("prompt_draft"):
        lines += ["", f"✏️ Prompt:\n  {resp['prompt_draft']}"]
    if resp.get("memory_suggestion"):
        lines += ["", f"🧠 Remember? {resp['memory_suggestion']}"]
    lines += ["", "_read-only · proposes, never executes_"]
    return "\n".join(lines)


def generate(prompt: str, provider: str | None = None) -> str:
    """Generate a conversational reply via the LOCAL gateway/Ollama (read-only).
    Ray-approved: local-only, no paid APIs. Falls back to the deterministic
    template if the local backend is offline. Never raises on backend failure."""
    try:
        from lib import hermes_mobile_provider as MP
        from lib import hermes_mobile_context as MC
        ctx = MC.summarize_context_for_prompt(user_message=prompt)
        res = MP.generate_mobile_reply(prompt, context=ctx, mode="read_only")
        if not res.get("used_fallback") and res.get("text"):
            return res["text"]
    except Exception:
        pass
    # deterministic, always-safe fallback
    return respond(prompt)["answer"]


def respond_llm(text: str) -> dict:
    """Like respond(), but uses the LOCAL model for the conversational 'answer'
    when available, keeping all deterministic safety fields (proposed_action,
    command_draft, links). Read-only. Falls back to template answer if offline."""
    base = respond(text)
    try:
        from lib import hermes_mobile_provider as MP
        from lib import hermes_mobile_context as MC
        ctx = MC.summarize_context_for_prompt(user_message=text)
        res = MP.generate_mobile_reply(text, context=ctx, mode="read_only")
        base["provider"] = res.get("provider")
        base["model"] = res.get("model")
        base["used_fallback"] = res.get("used_fallback", True)
        if not res.get("used_fallback") and res.get("text"):
            base["answer"] = res["text"].strip()
    except Exception as e:
        base["provider"] = "fallback"
        base["used_fallback"] = True
        base["provider_error"] = str(e)[:60]
    return base
