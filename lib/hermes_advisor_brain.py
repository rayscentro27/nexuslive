"""
Hermes Advisor Brain v1 — personal/business partner first, read-only Nexus context second.

Hermes Advisor is NOT TheChosenOne. It reasons, recommends, researches honestly,
reads Ray's profile + the Operator Core as read-only evidence, and drafts clean
handoffs when execution is needed. It does not execute, does not send to customers,
does not pretend to search/watch, and does not default to "paste this to TheChosenOne".

All deterministic + local. No paid APIs, no secrets, no execution.
"""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADV = ROOT / "docs" / "hermes_advisor"
KB = ROOT / "knowledge" / "hermes_advisor"
HANDOFF_DIR = KB / "handoffs"

PROFILE_MD = ADV / "RAY_PROFILE.md"
IDENTITY_MD = ADV / "HERMES_ADVISOR_IDENTITY.md"
MODES_MD = ADV / "ADVISOR_RESPONSE_MODES.md"
CAPS_MD = ADV / "HERMES_CAPABILITIES.md"
OPER_STATUS = ROOT / "reports" / "operator" / "nexus_operator_status.json"
OPER_BRIEF = ROOT / "reports" / "operator" / "nexus_operator_brief.md"


def _read(p: Path) -> str:
    try:
        return p.read_text(errors="ignore")
    except Exception:
        return ""


def load_ray_profile() -> dict:
    """Return Ray's profile facts. Name is hard-known; goals parsed from the md."""
    md = _read(PROFILE_MD)
    prof = {
        "name": "Ray",
        "full_name": "Ray Davis",
        "source": str(PROFILE_MD.relative_to(ROOT)) if PROFILE_MD.exists() else "unknown",
        "profile_present": PROFILE_MD.exists(),
        "primary_goal": "Monetize Nexus via the Credit/Funding Readiness Review",
        "preferred_offer": "Credit/Funding Readiness Review — $97 starter / $197–$297 full",
        "wants": [
            "decisive recommendations + visible proof (not vague stock answers)",
            "Hermes Advisor as a business partner, not a command bot",
            "practical money moves over feature creep",
            "TheChosenOne for execution; Hermes for thinking/advice/research",
        ],
    }
    return prof


def load_operator_status() -> dict | None:
    try:
        return json.loads(OPER_STATUS.read_text())
    except Exception:
        return None


def load_advisor_capabilities() -> dict:
    """Honest capability map (kept in sync with HERMES_CAPABILITIES.md)."""
    return {
        "read_ray_profile": PROFILE_MD.exists(),
        "read_operator_core": OPER_STATUS.exists(),
        "read_local_reports": True,
        "web_search": False,            # not connected from Hermes Mobile
        "youtube_direct_analysis": False,
        "youtube_ingestion_pipeline": "via TheChosenOne handoff (not direct)",
        "create_handoff": True,
        "execute_commands": False,
        "send_customer_messages": False,
        "publish": False,
        "charge_payments": False,
        "trade_live": False,
        "read_oanda_demo_status": OPER_STATUS.exists(),
        "update_local_advisor_notes": True,
    }


# ── Intent classification (advisor-first; never defaults to command bot) ──
def classify_advisor_intent(message: str) -> str:
    t = (message or "").strip().lower()
    if not t:
        return "casual_conversation"
    has_url = bool(re.search(r"https?://|youtube\.com|youtu\.be", t))

    # capability questions ("can you …")
    if re.search(r"\b(can you|are you able|do you have|can hermes)\b", t) and \
       any(k in t for k in ("search", "internet", "web", "watch", "youtube", "video", "buy", "book", "access", "browse")):
        return "capability_truth"

    # research: links, trends, web lookups, new tools
    if has_url or any(k in t for k in ("trending", "search the internet", "search the web", "look up",
                                       "find the best", "new tool", "what's trending", "whats trending",
                                       "research ", "watch a youtube", "take a look at a youtube")):
        return "research_request"

    # execution approval
    if any(k in t for k in ("i approve", "approve this", "move forward", "let's move forward",
                            "lets move forward", "go ahead", "do it", "make it happen", "ship it",
                            "let's go", "lets go")):
        return "execution_handoff"

    # social-first first-dollar funnel questions
    if any(k in t for k in (
        "prospect list", "without a list", "no list", "$97 review", "97 review",
        "post today", "comments ready", "comment ready", "dm workflow",
        "social publishing", "facebook publishing", "instagram publishing",
        "first paid client"
    )):
        return "social_first_funnel"

    # money question -> advisory blend (handled specially)
    if "make money" in t or "money today" in t or "money pipeline" in t:
        return "money_advisory"

    # operator/status interpretation
    if any(k in t for k in ("showroom", "oanda", "automation status", "what is blocked", "what's blocked",
                            "blocked", "what needs approval", "needs approval", "assets do we have",
                            "assets for review", "operator status", "system status", "what's running")):
        return "operator_interpretation"

    # reflective / strategy partner
    if any(k in t for k in ("what would you do if you were me", "what would you do", "what do you think",
                            "is this worth it", "should we", "your take", "your opinion")):
        return "reflective_business_partner"

    # advisory
    if any(k in t for k in ("what do you recommend", "recommend", "what should we do",
                            "what should i do", "next move", "what's next", "whats next")):
        return "advisory"

    # casual: greetings / identity / small talk / short msgs
    if any(k in t for k in ("good morning", "morning", "good evening", "good night", "hello", "hey", "hi ",
                            "how are you", "how did you sleep", "how's it going", "hows it going",
                            "do you know my name", "what's my name", "whats my name", "who am i")) or len(t) <= 24:
        return "casual_conversation"

    return "reflective_business_partner"


# ── Operator summary helpers ──
def _oper_money(st):
    m = st.get("monetization", {}) if st else {}
    return m


def _oper_blockers(st):
    return (st or {}).get("blockers", [])


def build_advisor_context(message: str) -> dict:
    return {
        "intent": classify_advisor_intent(message),
        "profile": load_ray_profile(),
        "capabilities": load_advisor_capabilities(),
        "operator": load_operator_status(),
        "message": message,
    }


def format_handoff(title: str, goal: str, context: str = "", inputs: str = "",
                   actions: str = "", approval: str = "pending Ray approval",
                   expected: str = "", do_not: str = "send to customers / publish / charge / trade live") -> str:
    return "\n".join([
        "── HANDOFF FOR THECHOSENONE ──",
        f"Title: {title}",
        f"Goal: {goal}",
        f"Context: {context or '(from Hermes Advisor conversation)'}",
        f"Inputs: {inputs or '(none)'}",
        f"Actions: {actions or '(define exact command/steps)'}",
        "Safety: read-only/approval-gated; no live trading, no customer sends, no payments",
        f"Approval status: {approval}",
        f"Expected output: {expected or '(receipt/report)'}",
        "Receipt/report path: reports/operator/ or relevant logs/",
        f"Do not: {do_not}",
    ])


def save_handoff(title: str, body: str) -> str:
    try:
        HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:50] or "handoff"
        fp = HANDOFF_DIR / f"{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{slug}.md"
        fp.write_text(body + "\n")
        return str(fp.relative_to(ROOT))
    except Exception:
        return "(could not write handoff)"


# ── Deterministic, honest per-mode answers (used as the safe fallback) ──
def answer_deterministic(message: str) -> str:
    ctx = build_advisor_context(message)
    intent = ctx["intent"]
    prof = ctx["profile"]
    name = prof["name"]
    caps = ctx["capabilities"]
    st = ctx["operator"]
    t = (message or "").strip().lower()

    if intent == "casual_conversation":
        if any(k in t for k in ("do you know my name", "what's my name", "whats my name", "who am i")):
            return f"Yes — you're {name} ({prof['full_name']}). What's on your mind?"
        if "how did you sleep" in t or "how are you" in t or "how's it going" in t or "hows it going" in t:
            return "Running clean and ready. What do you want to think through?"
        if any(k in t for k in ("good morning", "morning")):
            return f"Morning, {name}. Want my read on today's top money move, or just catching up?"
        if any(k in t for k in ("good night", "good evening")):
            return f"Evening, {name}. Want a quick wrap-up of where things stand before you log off?"
        return f"Hey {name} — I'm here. Want advice, a recommendation, or me to read the system status?"

    if intent == "capability_truth":
        lines = ["Straight answer on what I can do from Hermes Advisor:"]
        if any(k in t for k in ("search", "internet", "web", "browse")):
            lines.append("- Web search: NO — not connected here. I won't fake trends or results.")
        if any(k in t for k in ("youtube", "video", "watch")):
            lines.append("- Watch a YouTube video directly: NO. I can draft a transcript/research handoff for TheChosenOne instead.")
        if any(k in t for k in ("buy", "book")):
            lines.append("- Buy/book things: NO — no purchasing capability, and that would need your approval anyway.")
        lines += [
            "- What I CAN do: read your profile, read the Operator Core status, read local Nexus reports,"
            " reason/recommend, and draft a clean handoff for TheChosenOne.",
            "Want me to create a research handoff?",
        ]
        return "\n".join(lines)

    if intent == "research_request":
        url = re.search(r"https?://\S+", message or "")
        target = url.group(0) if url else "that topic"
        if not caps["web_search"]:
            ho = format_handoff(
                title="Research / transcript ingestion",
                goal=f"Research {target} and summarize for Ray",
                inputs=target,
                actions="Ingest via Nexus research/transcript pipeline (yt-dlp for YouTube); summarize key points + monetization angle",
                expected="research summary + opportunity score")
            path = save_handoff("research " + target, ho)
            return ("I can't search the web or watch videos directly from Hermes Advisor (not connected) — "
                    f"I won't pretend I did.\nI've drafted a research handoff for TheChosenOne:\n{ho}\n"
                    f"(saved: {path})\nApprove it and TheChosenOne can run the ingestion.")
        return "Web search is connected — running it now."  # placeholder if ever wired

    if intent == "execution_handoff":
        # Infer the most recent discussed item from operator monetization, else ask.
        m = _oper_money(st) if st else {}
        item = (m.get("approval_items") or m.get("assets") or ["the current offer step"])[0]
        ho = format_handoff(
            title=f"Approved by Ray: {item}",
            goal=f"Move forward on: {item}",
            context="Ray approved in Hermes Advisor conversation",
            actions="Execute the approved step (still respects approval-gating for any external send/publish/payment)",
            approval="APPROVED by Ray for internal prep; external send/publish/payment still needs explicit confirm",
            expected="receipt + status update")
        path = save_handoff(f"approved {item}", ho)
        return (f"Got it, {name} — reading that as approval to move on **{item}**.\n"
                f"I've drafted the execution handoff:\n{ho}\n(saved: {path})\n"
                "Note: I can draft + queue this, but direct execution routing into TheChosenOne isn't wired from "
                "Hermes Advisor yet — paste/confirm to TheChosenOne to run it, or tell me and I'll keep it queued.")

    if intent == "money_advisory":
        m = _oper_money(st) if st else {}
        ready = m.get("assets", []) if m else []
        approvals = m.get("approval_items", []) if m else []
        nxt = (st or {}).get("top_3_next_actions", []) if st else []
        return "\n".join([
            f"My take, {name}: lead with the **Credit/Funding Readiness Review** ($97 starter / $197–$297 full).",
            "Why: it reuses assets you already have (proof_credit, report/checklist workflows) and the buyers are high-intent — fastest path to cash with no new build.",
            f"Ready now: {len(ready)} draft assets" + (f" (e.g. {', '.join(ready[:4])})" if ready else " (run the operator to refresh)"),
            f"Needs your approval: {', '.join(approvals) or 'outreach + publish steps'}",
            "Risk: it stalls if nothing gets approved — drafts don't make money until outreach goes out.",
            f"Next move: {nxt[0] if nxt else 'approve the offer, then approve outreach.'}",
            "Want me to draft the outreach handoff for TheChosenOne?",
        ])

    if intent == "social_first_funnel":
        social_report = ROOT / "reports" / "capability_map" / "social_publishing_capability_20260617.md"
        funnel_report = ROOT / "reports" / "value_test" / "social_first_funnel_plan_20260617.md"
        dm_report = ROOT / "reports" / "value_test" / "social_first_dm_comment_workflow_20260617.md"
        post_plan = ROOT / "reports" / "value_test" / "facebook_posting_plan_97_starter_20260617.md"

        if "blocking" in t or "blocked" in t or "social publishing" in t or "facebook publishing" in t or "instagram publishing" in t:
            return "\n".join([
                "Social publishing is still blocked for real outbound posting.",
                "- Facebook: no usable Page ID/publishing implementation confirmed.",
                "- Instagram: no Instagram Business ID/feed/Reels publisher confirmed.",
                "- Postiz: no POSTIZ_URL or POSTIZ_API_KEY configured.",
                "- Meta: app credentials are partial, but publishing/account config is incomplete.",
                "- Safe path today: local dry-run queue + manual posting after Ray approves the exact account and post.",
                f"Report: {social_report.relative_to(ROOT) if social_report.exists() else 'social report not generated yet'}",
            ])

        if "dm workflow" in t or "comment" in t or "ready" in t:
            return "\n".join([
                "If someone comments READY, use a manual DM workflow:",
                "1. Public reply: 'Got it. I will send the Credit/Funding Readiness Checklist. Readiness education only, no funding or approval guarantee.'",
                "2. DM the checklist bullets: formation docs, EIN letter, recent bank statements, business identity consistency, funding goal.",
                "3. Offer the $97 Starter Review: readiness scorecard, top 5 gaps, 1-page next-step checklist.",
                "4. Send intake questions only after they show interest.",
                "5. Send payment instructions only after Ray approves the payment method.",
                f"Workflow: {dm_report.relative_to(ROOT) if dm_report.exists() else 'DM workflow report not generated yet'}",
            ])

        if "post today" in t or "what should we post" in t:
            return "\n".join([
                "Post this today, manually, after Ray approves the exact account:",
                "'The worst time to get funding-ready is the day you need cash. I am testing a $97 Credit/Funding Readiness Starter Review this week. You get a readiness scorecard, top 5 gaps, and a 1-page next-step checklist. No credit pull. No funding application. No approval guarantee. Comment READY or DM READY for the checklist.'",
                "Use it on Ray-owned Facebook profile/page first, then Instagram story/reel adaptation.",
                f"Posting plan: {post_plan.relative_to(ROOT) if post_plan.exists() else 'Facebook plan not generated yet'}",
            ])

        return "\n".join([
            "Because Ray has no prospect list, sell the $97 review through a social-first funnel:",
            "1. Post educational readiness content on Ray-owned Facebook/Instagram.",
            "2. CTA: comment or DM READY for the Credit/Funding Readiness Checklist.",
            "3. Manually reply with the checklist and compliance boundary.",
            "4. Ask intake questions.",
            "5. Offer the $97 Starter Review.",
            "6. Collect payment only through Ray-approved manual payment or separately approved live Stripe.",
            "7. Fulfill manually, then upsell $197/$297 only if the buyer wants a deeper review.",
            "Fastest path: one approved Facebook profile post today + story prompt + manual READY replies.",
            f"Plan: {funnel_report.relative_to(ROOT) if funnel_report.exists() else 'funnel report not generated yet'}",
        ])

    if intent == "operator_interpretation":
        if not st:
            return ("I read the Operator Core for this, but reports/operator/nexus_operator_status.json isn't "
                    "generated yet. Smallest next step: run `python3 scripts/run_nexus_operator_core.py`, then ask me again.")
        if "showroom" in t:
            s = st.get("showroom", {})
            return (f"Showroom: route {s.get('route')} — component exists={s.get('component_exists')}, "
                    f"pushed={s.get('pushed')}, deployed={s.get('deployed')}. Registry: {s.get('asset_registry')}.\n"
                    f"Read meaning: it's built locally but not live yet. Follow-up: {(s.get('followups') or ['—'])[0]}")
        if "oanda" in t:
            o = st.get("oanda_demo", {})
            return (f"Oanda demo: practice={o.get('practice_demo_confirmed')}, live blocked={o.get('live_funded_blocked')}, "
                    f"auto_trading={o.get('raw_auto_trading')}. Latest: {o.get('latest_result')} "
                    f"(fills {o.get('fills')}, cancels {o.get('cancels')}, rejects {o.get('rejects')}).\n"
                    "Read meaning: it's running safely on fake money, strategy-only.")
        if "blocked" in t:
            bl = _oper_blockers(st)
            if not bl:
                return "Nothing is blocking right now per the Operator Core."
            return "Here's what's actually blocked (from Operator Core):\n" + "\n".join(
                f"- {b.get('blocker')} → {b.get('fix')}" for b in bl)
        if "approval" in t or "assets" in t or "review" in t:
            a = st.get("automation", {}); m = st.get("monetization", {})
            return (f"Approval queue: {a.get('approval_queue_count')} items ({a.get('approval_queue_path')}).\n"
                    f"Assets for review: {len(m.get('assets', []))} in {m.get('package_path')}.\n"
                    f"My read: the drafts are ready; the bottleneck is your approval on outreach/publish.")
        # generic status
        return (f"Overall: {st.get('overall_status')}. Comm {st.get('communication',{}).get('status')}, "
                f"automation {st.get('automation',{}).get('status')}, monetization {st.get('monetization',{}).get('status')}. "
                "Ask 'what is blocked' for the specifics.")

    # advisory / reflective_business_partner
    nxt = (st or {}).get("top_3_next_actions", []) if st else []
    return "\n".join([
        f"My take, {name}:",
        "- Focus the Credit/Funding Readiness Review to first revenue — it's the shortest path you have.",
        "- Why: assets already drafted; the only gap is your approval to send outreach + publish the lead magnet.",
        "- Risk: spreading into new features/automation again delays the first dollar.",
        f"- If I were you, my one next move: {nxt[0] if nxt else 'approve the offer + outreach today'}.",
        "Want me to draft that as a handoff for TheChosenOne?",
    ])


# ── Recent conversation memory (short-term; local, no secrets) ──
_RECENT = ROOT / "logs" / "hermes_advisor_recent.json"


def remember(role: str, text: str) -> None:
    try:
        _RECENT.parent.mkdir(parents=True, exist_ok=True)
        hist = json.loads(_RECENT.read_text()) if _RECENT.exists() else []
        hist.append({"role": role, "text": (text or "")[:500],
                     "ts": datetime.now(timezone.utc).isoformat()})
        _RECENT.write_text(json.dumps(hist[-10:]))
    except Exception:
        pass


def recent_context(n: int = 6) -> str:
    try:
        hist = json.loads(_RECENT.read_text())[-n:]
        return "\n".join(f"{h['role']}: {h['text']}" for h in hist)
    except Exception:
        return ""


# ── Local Ollama (localhost only; skip *-cloud; no paid APIs) ──
def _pick_local_model():
    import os, urllib.request
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    try:
        from lib.hermes_mobile_provider import validate_provider_is_local
        ok, _ = validate_provider_is_local(host)
        if not ok:
            return None, host
    except Exception:
        if "localhost" not in host and "127.0.0.1" not in host:
            return None, host
    try:
        with urllib.request.urlopen(host + "/api/tags", timeout=5) as r:
            names = [m.get("name") for m in json.loads(r.read()).get("models", [])]
    except Exception:
        return None, host
    local = [n for n in names if n and not n.endswith("-cloud")]  # never cloud
    if not local:
        return None, host
    pref = os.environ.get("HERMES_ADVISOR_MODEL") or os.environ.get("HERMES_MOBILE_MODEL")
    if pref and pref in local:
        return pref, host
    for cand in ("gemma3:1b", "qwen2.5:0.5b"):
        if cand in local:
            return cand, host
    return local[0], host


# Circuit breaker: if Ollama is too slow once, skip it for a cooldown so the bot
# stays snappy and falls back to the deterministic advisor instantly.
_OLLAMA_STATE = ROOT / "logs" / "hermes_advisor_ollama.json"
_OLLAMA_COOLDOWN_SEC = 1800


def _ollama_skip() -> bool:
    try:
        until = json.loads(_OLLAMA_STATE.read_text()).get("slow_until", 0)
        return datetime.now(timezone.utc).timestamp() < float(until)
    except Exception:
        return False


def _ollama_mark_slow() -> None:
    try:
        _OLLAMA_STATE.parent.mkdir(parents=True, exist_ok=True)
        _OLLAMA_STATE.write_text(json.dumps(
            {"slow_until": datetime.now(timezone.utc).timestamp() + _OLLAMA_COOLDOWN_SEC}))
    except Exception:
        pass


def _ollama_generate(system: str, prompt: str, timeout: float = 15.0, max_tokens: int = 320):
    import urllib.request
    model, host = _pick_local_model()
    if not model:
        return None
    body = json.dumps({"model": model, "system": system, "prompt": prompt, "stream": False,
                       "options": {"num_predict": max_tokens, "temperature": 0.6}}).encode()
    try:
        req = urllib.request.Request(host + "/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return (json.loads(r.read()).get("response") or "").strip() or None
    except Exception:
        return None


def _grounded_system(ctx: dict) -> str:
    prof = ctx["profile"]; st = ctx["operator"]
    op = ""
    if st:
        m = st.get("monetization", {}); o = st.get("oanda_demo", {})
        op = (f"Operator Core: overall={st.get('overall_status')}; offer={m.get('primary_offer')} "
              f"{' / '.join(m.get('prices', []))}; approval_queue={st.get('automation', {}).get('approval_queue_count')}; "
              f"ready_assets={len(m.get('assets', []))}; oanda={o.get('latest_result')} (practice, live blocked); "
              f"blockers={len(st.get('blockers', []))}.")
    return (
        "You are Hermes Advisor — Ray's personal/business AI partner. Direct, useful, opinionated, honest. "
        "You are NOT a command bot. Talk naturally like a partner, not a template.\n"
        f"RAY: {prof['full_name']} (call him {prof['name']}). Top goal: {prof['primary_goal']}. "
        f"Preferred offer: {prof['preferred_offer']}. He wants decisive recommendations + proof, not vague answers.\n"
        f"{op}\n"
        "HARD TRUTH (never violate): you CANNOT search the web, watch YouTube, execute commands, send messages, "
        "publish, charge payments, or trade. Never claim you did any of those. If asked, say honestly you can't from "
        "here and offer to draft a handoff for TheChosenOne. Do NOT say 'paste this to TheChosenOne' by default — only "
        "draft a handoff when execution is genuinely needed. Be concise (a few sentences). Ask at most one question."
    )


_FAKE_PATTERNS = [
    r"\bi (searched|googled|looked it up|found (it )?online)\b",
    r"\baccording to (my|a|the) (search|google|web)\b",
    r"\bi watched (the|this) video\b", r"\bin (the|this) video\b", r"\bthe video (says|shows|is about)\b",
    r"\bi (executed|ran the command|sent the email|sent it|posted|published|placed the trade|charged)\b",
    r"\btrending (right )?now\b", r"\bhere are the (latest|current) (trends|search results)\b",
]


def _honesty_violation(text: str) -> bool:
    low = (text or "").lower()
    return any(re.search(p, low) for p in _FAKE_PATTERNS)


def _strip_paste(text: str) -> str:
    return re.sub(r"(?i)paste (this|it)( in| into)? to the ?chose?n? ?one\.?",
                  "I can draft a handoff for TheChosenOne.", text or "")


# ── Blended entry: local Ollama reasoning, grounded, with honest fallback ──
def answer_with_advisor_mode(message: str) -> str:
    ctx = build_advisor_context(message)
    intent = ctx["intent"]
    deterministic = answer_deterministic(message)
    remember("Ray", message)
    # Honesty/structure-critical modes stay deterministic (guaranteed honest + handoff structure).
    if intent in ("capability_truth", "research_request", "execution_handoff"):
        remember("Hermes", deterministic)
        return deterministic
    # Reasoning/conversation modes -> local Ollama, grounded; fall back if weak/unsafe.
    # Circuit breaker: if Ollama was recently too slow, skip it (instant deterministic).
    if _ollama_skip():
        remember("Hermes", deterministic)
        return deterministic
    system = _grounded_system(ctx)
    convo = recent_context()
    prompt = (f"Recent conversation:\n{convo}\n\n" if convo else "") + f"Ray: {message}\nHermes:"
    llm = _ollama_generate(system, prompt)
    if not llm:
        _ollama_mark_slow()  # too slow / unavailable -> cool down
        remember("Hermes", deterministic)
        return deterministic
    if len(llm) < 12 or _honesty_violation(llm):
        remember("Hermes", deterministic)
        return deterministic
    out = _strip_paste(llm)
    remember("Hermes", out)
    return out
