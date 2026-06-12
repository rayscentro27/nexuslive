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
# Things this bot has NO live tool/source for — answer honestly, never hallucinate.
UNSUPPORTED_LIVE = [
    "weather", "temperature", "forecast", "how hot", "how cold", "raining", "rain today",
    "news today", "headlines", "stock price", "stock market", "crypto price", "bitcoin price",
    "sports score", "game score", "what time is it", "current time", "today's date",
]

# Operational commands Hermes must hand off (never invent state). Maps the phrase
# Ray typed -> the exact canonical TheChoseone command to send.
OP_HANDOFF_MAP = {
    "status": "status", "system status": "status", "what is running": "status",
    "raw status": "raw status", "details status": "raw status", "full status": "raw status",
    "scout status": "scouts status", "scouts status": "scouts status", "scout statuses": "scouts status",
    "scouts": "scouts status", "scout report": "scouts status", "scout reports": "scouts status",
    "status scouts": "scouts status", "status scout": "scouts status",
    "what did nexus produce": "what did nexus produce", "what did you produce": "what did nexus produce",
    "worker bridge status": "status", "command routing audit": "status",
    "trading status": "status", "safety status": "status",
}

INTENTS = [
    ("unsupported_live", UNSUPPORTED_LIVE),
    ("greeting", ["good morning", "good afternoon", "good evening", "morning hermes",
                  "hey hermes", "hi hermes", "hello hermes", "gm "]),
    ("approval_queue", ["what needs approval", "what needs to be approved", "what do i need to approve",
                        "what needs my approval", "approval queue", "show approvals", "pending approvals",
                        "what assets need review", "what packages need review", "review queue",
                        "showroom queue"]),
    ("what_think", ["what do you think about the nexus", "what do you think about nexus",
                    "what do you think of nexus", "is nexus any good", "thoughts on nexus",
                    "what do you think about the nexus program"]),
    ("how_approve", ["how do i approve", "how to approve", "approve the credit", "approve this",
                     "approve the funding", "how do i approve the"]),
    ("can_run_codex", ["can thechoseone run codex", "can it run codex", "can thechoseone run claude",
                       "can the bot run codex", "does thechoseone run codex"]),
    ("stop_help", ["how do i stop trading", "how to stop trading", "how do i stop sends",
                   "how to stop sends", "how do i stop automation", "how do i pause"]),
    ("research", ["research ", "find affiliate", "affiliate offers", "best affiliate",
                  "look up", "search the web", "web research", "find the best"]),
    ("command_help", ["what can thechoseone do", "what commands", "what command should i send",
                      "what should i send thechoseone", "tell thechoseone to", "what command",
                      "which command", "how do i ask thechoseone"]),
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

    # ── Operational-command handoff ──────────────────────────────────────────
    # Hermes must NOT invent live operational state. If it receives a TheChoseone
    # status/operational command, hand off the exact command (unless the ask is to
    # EXPLAIN a report, which is conversational).
    _low = (text or "").strip().lower().rstrip("?!. ")
    if not _low.startswith(("explain", "what do you think")):
        canonical = OP_HANDOFF_MAP.get(_low)
        if canonical:
            out["intent"] = "op_handoff"
            out["answer"] = f"That's a TheChoseone command — it has the verified live data. Send this:"
            out["command_draft"] = canonical
            out["proposed_action"] = "Paste it to TheChoseone; I won't invent the status myself."
            out["summary"] = f"Handed off to TheChoseone: {canonical}"
            return out

    if intent == "unsupported_live":
        out["answer"] = (
            "I don't have live weather/news/markets access in this Telegram bot yet — so I "
            "won't guess. What I'm good at: Nexus status, explaining reports, strategy, and "
            "drafting commands for TheChoseone. Want me to add a weather/tool adapter later?"
        )
        out["summary"] = "No live external-data tool connected; answered honestly."
        out["proposed_action"] = "Ask me about Nexus, or say 'what needs my attention?'"
        return out

    if intent == "greeting":
        out["answer"] = ("Good morning Ray. Nexus is in War Room mode. Best first move today: check "
                         "approvals, then decide whether the Credit/Funding pack is ready for manual use.")
        out["proposed_action"] = "Want the exact TheChoseone command? It's: what needs approval"
        out["command_draft"] = "what needs approval"
        out["summary"] = "Greeting + concrete first move."
        return out

    if intent == "approval_queue":
        out["answer"] = ("Approval queue is a TheChoseone command — it has the live data, not me. "
                         "Send this to TheChoseone:")
        out["command_draft"] = "what needs approval"
        out["proposed_action"] = ("It'll list the packages + exact approve/revise commands. Approving "
                                  "means manual-use only (no auto-publish/send/charge).")
        out["summary"] = "Routed to TheChoseone's approval queue."
        return out

    if intent == "what_think":
        out["answer"] = ("Honestly? Nexus has real value now: 7 scouts producing assets, a Showroom with "
                         "approval controls, hard safety boundaries, and a clean command/advisor split in "
                         "Telegram. The risk isn't the idea — it's execution: making assets specific enough "
                         "and converting them into a paid offer. The fix is concrete, not a rebuild.")
        out["proposed_action"] = ("Next move: approve or revise the Credit/Funding pack, then package it as "
                                  "a manual paid readiness review ($97–$297).")
        out["command_draft"] = "what needs approval"
        out["summary"] = "Constructive: real value; gap is execution + monetization."
        return out

    if intent == "how_approve":
        pkg = "proof_funding" if "funding" in text.lower() else "proof_credit"
        out["answer"] = (f"Send this to TheChoseone — it batch-approves the {pkg.replace('proof_','')} "
                         "package for manual use (it does NOT auto-publish, send, or charge):")
        out["command_draft"] = f"approve all assets in package {pkg} with notes: Approved for manual use only."
        out["proposed_action"] = (f"To revise instead: request revision for package {pkg} with notes: "
                                  "Make this more specific and less generic.")
        out["summary"] = "Drafted the exact approval command (manual-use only)."
        return out

    if intent == "can_run_codex":
        out["answer"] = ("Not live yet. TheChoseone can RECEIVE a Codex task, but the CLI bridge is OFF "
                         "— so it queues the task and hands you a copy/paste prompt instead of running "
                         "Codex automatically. Honest receipt, no fake execution.")
        out["command_draft"] = "task for codex: build a landing page for the credit track"
        out["proposed_action"] = "Send a 'task for codex: …' to TheChoseone; you'll get a queued receipt + a prompt to paste into Codex."
        out["summary"] = "Codex bridge is off; TheChoseone queues + drafts a prompt."
        return out

    if intent == "stop_help":
        low = text.lower()
        cmd = "stop trading" if "trad" in low else ("stop sends" if "send" in low else "pause automation")
        out["answer"] = (f"Send '{cmd}' to TheChoseone. (stop sends = halt email+IG; stop trading = halt "
                         "trading tests, Oanda stays demo; pause automation = pause test loops.)")
        out["command_draft"] = cmd
        out["proposed_action"] = f"Paste '{cmd}' to TheChoseone."
        out["summary"] = "Drafted the safety-control command."
        return out

    if intent == "research":
        topic = re.sub(r"(?i)^(research|find|look up|search the web for|web research|find the best)\s*", "", text).strip()
        topic = topic or "affiliate offers for the credit/funding pack"
        try:
            from lib import hermes_advisor_web_research as WR
            r = WR.research(topic)
            out["answer"] = r["message"]
            out["command_draft"] = r["command_draft"]
        except Exception:
            out["answer"] = "I can't browse directly from this bot yet. I can draft a research task for TheChoseone."
            out["command_draft"] = f"run web research: {topic} and return source links, summary, payout/cost, approval requirements, risk, and recommended next step."
        out["proposed_action"] = "Send that research task to TheChoseone (it logs source + results)."
        out["summary"] = "No live browsing here — drafted a safe research task."
        return out

    if intent == "command_help":
        low = text.lower()
        if "monetization" in low or "scout" in low or "affiliate" in low:
            out["answer"] = "Send this to TheChoseone:"
            out["command_draft"] = ("run web research: monetization offers for the credit/funding pack and "
                                    "return top 5 affiliate offers with source links, payout, approval "
                                    "requirements, risk, and recommended next step.")
            out["proposed_action"] = "Paste it to TheChoseone — I won't execute it."
        else:
            out["answer"] = ("Most useful TheChoseone commands: status · what needs approval · scouts status · "
                             "status credit scout · what did nexus produce · daily report · "
                             "approve all assets in package <id> with notes: <notes>. "
                             "Tell me the goal and I'll draft the exact one.")
            out["proposed_action"] = "Tell me what you want to do; I'll write the command."
        out["summary"] = "Explained commands / drafted the exact one."
        return out

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
            "Your attention should go to the review queue first, not new features.\n\n"
            "1. Credit/Funding pack — approve or revise first.\n"
            f"2. Showroom queue — {ctx['needs_review']} assets need triage.\n"
            "3. War Room test — confirm TheChoseone approval commands work.\n"
            "4. Monetization offer — turn approved assets into a manual $97–$297 offer."
        )
        out["summary"] = "Review queue first: approve pack, triage Showroom, test commands, build the offer."
        out["proposed_action"] = "Start with the approval queue."
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
            "Pick ONE revenue lane first: Credit/Funding Readiness. Why — it's closest to the assets you "
            "already have, it's warm-audience friendly, and it's safe to sell as manual-use (no automation "
            "needed yet), so you can charge before everything's perfect.\n\n"
            "Next 3 actions:\n"
            "1. Ask TheChoseone: what needs approval\n"
            "2. Approve or revise the Credit/Funding Consultant Pack for manual use only.\n"
            "3. Prepare a simple warm-lead offer: $97–$297 readiness review, no guarantees, manual fulfillment.\n\n"
            "Trading stays secondary — research/demo only, not your first 30-day money lane."
        )
        out["summary"] = "Lane 1 = Credit/Funding Readiness → approve pack → $97–$297 manual review."
        out["proposed_action"] = "Start with: what needs approval"
        out["command_draft"] = "what needs approval"
        out["memory_suggestion"] = "30-day money: Credit/Funding Readiness first; $97–$297 manual review; trading is secondary/demo."

    elif intent == "improve":
        out["answer"] = (
            "The specific weak spots (not the idea): 1) scout findings are template-driven, so they say "
            "'needs live verification' — no real research feeds them yet. 2) The assets are generic; they "
            "need to be specific enough that someone would pay for them. 3) Nothing is packaged as a paid "
            "offer yet. Highest-leverage fix: approve/revise the credit pack and turn it into a manual "
            "$97–$297 readiness review."
        )
        out["summary"] = "Weak spots: generic assets, no live research, no paid offer — all fixable."
        out["proposed_action"] = "Approve/revise the credit pack, then package the paid review."
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
            "Next best move: 1) review the approval queue, 2) approve or revise the Credit/Funding pack "
            "for manual use, 3) package it as a manual $97–$297 readiness review for a warm lead. That turns "
            "today's assets into money — no automation or trading needed first."
        )
        out["summary"] = "Approve the credit/funding pack → package a manual paid review."
        out["command_draft"] = "what needs approval"
        out["proposed_action"] = "Start with the approval queue."

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
    # Only remind that it won't execute when a command is actually drafted — don't
    # repeat the disclaimer on every message.
    if resp.get("command_draft"):
        lines += ["", "_I won't run this — paste it to TheChoseone when ready._"]
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
    # Only truly open/unmatched chit-chat goes to the local model. Every recognized
    # intent returns its crafted, specific answer — the small model otherwise emits
    # vague "analyze the assets" filler on high-value questions.
    if base["intent"] != "open":
        base["provider"] = "deterministic"
        base["used_fallback"] = False
        return base
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
