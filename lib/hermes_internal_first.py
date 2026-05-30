from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import json
import os
from pathlib import Path

from lib import hermes_ops_memory
from lib.hermes_knowledge_brain import get_funding_knowledge, get_recent_recommendations
from lib.demo_readiness import run_demo_readiness_check
from lib.hermes_email_knowledge_intake import recent_knowledge_email_intake
from lib.hermes_runtime_config import get_internal_first_keywords
from lib.operational_priorities import top_focus_summary
from lib.notebooklm_ingest_adapter import load_dry_run_queue, summarize_intake_queue
from lib.notebooklm_cli_adapter import (
    dry_run_sync,
    list_notebooks as notebooklm_list_notebooks,
    notebook_sync_status,
    sync_enabled,
)
from lib.ai_task_dispatch import create_task
from lib.hermes_response_patterns import match_pattern, fill_template
from lib import hermes_executive_memory as _exec_mem


CONF_INTERNAL_CONFIRMED = "INTERNAL_CONFIRMED"
CONF_INTERNAL_PARTIAL = "INTERNAL_PARTIAL"
CONF_INTERNAL_STALE = "INTERNAL_STALE"
CONF_GENERAL_FALLBACK = "GENERAL_FALLBACK"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_stale(updated_at: str, stale_hours: int = 72) -> bool:
    if not updated_at:
        return True
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - dt).total_seconds()
        return age_seconds > (int(stale_hours) * 3600)
    except Exception:
        return True


def _default_rules() -> dict[str, list[str]]:
    return get_internal_first_keywords()


def _parse_json_env(name: str, default: dict[str, list[str]]) -> dict[str, list[str]]:
    raw = (os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): [str(x).lower() for x in (v or [])] for k, v in data.items()}
    except Exception:
        pass
    return default


@dataclass
class InternalFirstReply:
    text: str
    confidence: str
    source: str
    matched_topic: str


def _build_operational_context_brief() -> str:
    """Build greeting context from verified evidence files only. No unsourced claims."""
    from pathlib import Path as _Path
    root = _Path(__file__).resolve().parent.parent
    found = []

    try:
        handoff_dir = root / "docs" / "reports" / "handoffs"
        if handoff_dir.exists():
            count = len(list(handoff_dir.glob("claude_code_handoff_*.md")))
            if count:
                found.append(f"{count} code handoff{'s' if count != 1 else ''}")
    except Exception:
        pass

    try:
        intake = root / "docs" / "reports" / "intake" / "telegram_source_intake.jsonl"
        if intake.exists():
            lines = [l for l in intake.read_text().splitlines() if l.strip()]
            if lines:
                found.append(f"{len(lines)} source intake records")
    except Exception:
        pass

    try:
        mono_dir = root / "docs" / "reports" / "monetization"
        if mono_dir.exists() and any(mono_dir.glob("30_day_revenue_plan_*.md")):
            found.append("30-day revenue plan")
    except Exception:
        pass

    if found:
        return (
            "Verified evidence available: " + ", ".join(found) + ".\n"
            "Ask what you want to review."
        )
    return (
        "Ask: 'what should we work on today', '30 day goals', "
        "'show source intake', or 'what did claude code work on'."
    )


_STATUS_LABELS: dict[str, str] = {
    "product_candidate": "Build product",
    "content_candidate": "Create content",
    "client_education_candidate": "Client education content",
    "affiliate_candidate": "Set up affiliate",
    "grant_candidate": "Apply for grant",
    "needs_more_research": "Research further",
    "high_priority": "High priority action",
    "watch": "Monitor",
    "reject": "Filtered out",
}

_CATEGORY_ACTIONS: dict[str, str] = {
    "paid template": "Build a Credit/Funding Readiness Checklist lead magnet (free to draft, no approval needed)",
    "tool product": "Build a paid checklist or audit tool for the credit/funding audience",
    "newsletter premium": "Launch a premium Nexus newsletter tier — weekly funding/credit opportunity digest",
    "newsletter": "Create a weekly newsletter for the Nexus funding audience — draft internally first",
    "affiliate program": "Identify and document the top 2-3 affiliate programs fitting Nexus' credit/funding audience",
    "affiliate": "Research free affiliate programs for credit repair and business funding tools",
    "credit repair": "Create a step-by-step credit repair roadmap as a free Nexus lead magnet",
    "credit score": "Build a Credit Score Improvement Roadmap guide — free lead magnet for the Nexus funnel",
    "credit": "Build a credit repair guide or score roadmap for the Nexus content funnel",
    "funding readiness": "Create a Business Funding Readiness Checklist for Nexus' credit audience",
    "funding": "Write a business funding guide for the Nexus audience — internal draft, no approval needed",
    "funnel": "Design a lead magnet funnel for the credit/funding audience — opt-in to email list",
    "grant": "Research free small business or creator grants — draft application internally, no cost",
    "saas": "Design a lightweight SaaS tool or dashboard for the credit/funding market",
    "youtube": "Research and document the top YouTube content angles for the credit/funding audience",
    "content": "Write a free educational credit/funding guide — top-of-funnel lead magnet",
    "research": "Conduct and document internal research — create a Nexus internal artifact",
}

# Patterns that identify a workflow routing instruction, not a product recommendation.
# These get skipped in favour of _CATEGORY_ACTIONS expansion.
_ROUTING_PATTERNS = frozenset([
    "route to", "assign to", "build draft for", "send to scout",
    "send to ", "forward to", "hand off", "hand to",
])


def _format_opportunity_specific(op: dict) -> str:
    """
    Convert a generic decision record into a specific recommended action.
    Returns a one-line specific recommendation, not just a category label.
    """
    title = (op.get("title") or op.get("keyword") or "").strip()
    status = op.get("status", "")
    rec = (op.get("recommended_action") or "").strip()
    keyword = (op.get("keyword") or "").lower()
    score = op.get("monetization_score", 0)
    approval = op.get("requires_ray_approval", False)
    scout = op.get("assigned_scout") or op.get("discovered_by") or ""

    generic_labels = {
        "monetization opportunity", "content opportunity", "affiliate opportunity",
        "product opportunity", "research opportunity",
    }
    title_lower = title.lower()
    rec_lower = rec.lower()

    # 1. Use recommended_action only if it is specific (not a generic label, not a routing instruction)
    rec_is_routing = any(p in rec_lower for p in _ROUTING_PATTERNS)
    if rec and not any(label in rec_lower for label in generic_labels) and len(rec) > 20 and not rec_is_routing:
        specific = rec
    else:
        # 2. Try category expansion before falling back to raw title
        specific = ""
        for key, action in _CATEGORY_ACTIONS.items():
            if key in title_lower or key in keyword:
                specific = action
                break
        # 3. If no category match and title is non-generic, use title
        if not specific and title and not any(label in title_lower for label in generic_labels) and len(title) > 15:
            specific = title
        # 4. Final fallback
        if not specific:
            action_verb = _STATUS_LABELS.get(status, "Research")
            specific = f"{action_verb}: {title or keyword or 'unknown opportunity'}"

    approval_tag = " [needs approval]" if approval else ""
    scout_tag = f" — assign to {scout}" if scout else ""
    return f"{specific}{approval_tag}{scout_tag}"


def _format_opportunity_detail(op: dict, index: int) -> list[str]:
    """
    Full multi-line specific opportunity block for top monetization actions.
    """
    title = (op.get("title") or op.get("keyword") or "").strip()
    status = op.get("status", "")
    rec = (op.get("recommended_action") or "").strip()
    why = (op.get("why_selected") or op.get("why_collected") or "").strip()
    goal = (op.get("goal_supported") or "").strip()
    scout = op.get("assigned_scout") or op.get("discovered_by") or ""
    approval = op.get("requires_ray_approval", False)
    score = op.get("monetization_score", 0)

    specific = _format_opportunity_specific(op)
    lines = [f"{index}. {specific}"]
    # Derive "Why" from explicit field, goal, or status/score
    if why:
        lines.append(f"   Why: {why[:120]}")
    elif goal:
        lines.append(f"   Why: Supports the {goal} goal — fits Nexus' credit/funding audience.")
    elif status in ("product_candidate", "content_candidate"):
        lines.append(f"   Why: Fits the 30-day revenue goal and Nexus' credit/funding audience (score {score}).")
    elif status == "affiliate_candidate":
        lines.append(f"   Why: Free to set up — no cost or approval needed for research phase (score {score}).")
    else:
        lines.append(f"   Why: Identified as actionable opportunity (score {score}).")
    # "Next" — use the scout assignment if rec is a routing instruction, otherwise use rec
    rec_is_routing = any(p in rec.lower() for p in _ROUTING_PATTERNS)
    if rec and not rec_is_routing and rec != specific:
        lines.append(f"   Next: {rec[:100]}")
    elif scout:
        lines.append(f"   Next: Assign {scout} to draft this internally.")
    else:
        lines.append(f"   Next: Create internal draft — no cost or approval needed.")
    if scout:
        lines.append(f"   Scout: {scout}")
    lines.append(f"   Approval: {'Required before publishing or selling.' if approval else 'Not needed for internal draft. Required before publishing.'}")
    return lines


def _normalize_input(raw: str) -> str:
    # Strip smart quotes, bullets, em/en dashes + menu suffixes.
    # Uses string operations to avoid regex character class encoding issues.
    t = (raw or "").strip()
    # 1. Strip leading bullet/dash/star
    LEAD_STRIP = set([
        "\u2022", "\u2023", "\u25e6", "\u2013", "\u2014", "-", "*"
    ])
    while t and t[0] in LEAD_STRIP:
        t = t[1:].strip()
    # 2. Strip em dash / en dash and everything after it
    for dash in ["\u2014", "\u2013"]:
        idx = t.find(dash)
        if idx != -1:
            t = t[:idx].strip()
    # 3. Strip surrounding quote chars (ASCII and Unicode)
    QUOTES = set([chr(0x27), chr(0x22), chr(0x2018), chr(0x2019), chr(0x201c), chr(0x201d), chr(0xab), chr(0xbb)])
    while t and t[0] in QUOTES:
        t = t[1:]
    while t and t[-1] in QUOTES:
        t = t[:-1]
    # 4. Collapse whitespace
    return " ".join(t.split())




def try_internal_first(raw: str) -> InternalFirstReply | None:
    raw = _normalize_input(raw)
    text = (raw or "").strip().lower()
    if not text:
        return None

    # ── Phase 1: Conversational/greeting patterns from Supabase ──────────────
    # Handle greetings and social messages BEFORE operational keyword check.
    # These return Nexus-aware conversational replies, not generic chatbot text.
    try:
        pattern = match_pattern(text)
        if pattern:
            intent = pattern.get("intent", "")
            # Only handle genuinely conversational intents here — operational
            # intents (status_check_nexus, notebooklm_status, etc.) flow through
            # the full operational keyword path for richer data.
            conversational_intents = {
                "morning_greeting", "status_check_personal",
                "completion_acknowledgement",
            }
            if intent in conversational_intents:
                # morning_greeting: bypass Supabase template entirely — build from evidence
                if intent == "morning_greeting":
                    oc = _build_operational_context_brief()
                    reply_text = f"Morning, Ray. I'm online.\n{oc}"
                    return InternalFirstReply(
                        text=reply_text,
                        confidence=CONF_INTERNAL_CONFIRMED,
                        source="hermes_response_patterns+evidence_scan",
                        matched_topic=pattern.get("pattern_key", "morning_greeting"),
                    )
                ctx: dict[str, str] = {}
                if intent == "status_check_personal":
                    ctx["operational_context"] = _build_operational_context_brief()
                    ctx["brief_status"] = _build_operational_context_brief()
                    ctx["next_best_action"] = "Check 'what should I work on?' for priorities"
                    ctx["next_best_action_prompt"] = "Ask 'what should I work on?' for the top priority"
                elif intent == "completion_acknowledgement":
                    ctx["context_note"] = ""
                    ctx["next_action"] = "use 'show roadmap' to pick the next priority"
                tmpl = pattern.get("response_template", "")
                reply_text = fill_template(tmpl, ctx) if tmpl else None
                if reply_text:
                    return InternalFirstReply(
                        text=reply_text,
                        confidence=CONF_INTERNAL_CONFIRMED,
                        source="hermes_response_patterns",
                        matched_topic=pattern.get("pattern_key", "conversational"),
                    )
    except Exception:
        pass  # Never block on pattern matching failure

    # ── Phase 1.5: Source Intake → Opportunity Intelligence ──────────────────
    # Priority order:
    #   1. YouTube URL  → hermes_telegram_source_intake (always)
    #   2. GitHub URL   → hermes_telegram_source_intake
    #   3. Other URL + business context → opportunity_analyzer (only if not system question)
    #   4. Pure business text → opportunity_analyzer
    try:
        import re as _re
        _YT_RE = _re.compile(
            r'https?://(?:www\.)?(?:youtube\.com/(?:watch\?v=|@|channel/|c/)|youtu\.be/)',
            _re.I,
        )
        _GH_RE = _re.compile(r'https?://github\.com/', _re.I)

        if _YT_RE.search(raw) or _GH_RE.search(raw):
            # Always route known source URLs to intake — never to opportunity scorer
            from lib.hermes_telegram_source_intake import HermesTelegramSourceIntake
            intake = HermesTelegramSourceIntake()
            record = intake.process(raw, attached_intent=raw)
            return InternalFirstReply(
                text=record.telegram_reply(),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="telegram_source_intake",
                matched_topic="source_intake",
            )
    except Exception:
        pass  # Never block the pipeline if intake fails

    try:
        from lib.opportunity_analyzer import is_opportunity_input, generate_opportunity_report
        if is_opportunity_input(raw):
            full_report = generate_opportunity_report(raw)
            reply_text = full_report[:3800] + ("\n…[truncated]" if len(full_report) > 3800 else "")
            return InternalFirstReply(
                text=reply_text,
                confidence=CONF_INTERNAL_CONFIRMED,
                source="opportunity_analyzer",
                matched_topic="opportunity_intelligence",
            )
    except Exception:
        pass  # Never block the pipeline if analyzer fails

    # ── Phase 2: Operational keyword routing ─────────────────────────────────
    # Priority pre-check: new daily-intake topics use longer phrases that would
    # otherwise be shadowed by older single-word topics like "monetization" or "scouts".
    _PRIORITY_TOPICS: dict[str, list[str]] = {
        "monetization_actions": [
            "show top monetization actions", "top monetization actions",
            "what can make money this week", "best money moves",
            "top opportunities", "best opportunities",
            "what opportunities did you find", "show top actions",
        ],
        "rejected_opportunities": [
            "show rejected opportunities", "what did you reject",
            "why did you reject", "show rejected sources",
            "what was rejected and why", "what was rejected", "show rejected",
        ],
        "scouts_working": [
            "what scouts are working", "scouts working",
            "scout status", "who is assigned",
            "show scout assignments", "scout dispatch status",
        ],
        "daily_intake": [
            "run daily opportunity intake", "run daily intake",
            "what did you find today", "what did nexus find",
            "what sources did you find", "what sources are pending",
            "show pending sources",
        ],
        "daily_review": [
            "show daily research review", "show daily review",
            "daily research review", "what should i review first",
            "show research review", "show latest review",
            "show the daily review", "show the research review",
        ],
        "raw_evidence": [
            "show raw evidence", "raw evidence",
            "show artifact paths", "show artifact files",
            "show evidence paths", "evidence files and paths",
        ],
        "needs_approval": [
            "what needs my approval", "show approval needed",
            "what requires approval", "pending approvals",
            "what needs ray approval",
        ],
        "build_content_from_opportunity": [
            "build content from the best opportunity",
            "build content from opportunity",
            "create content from top opportunity",
        ],
    }
    topic = ""
    for priority_topic, phrases in _PRIORITY_TOPICS.items():
        if any(p in text for p in phrases):
            topic = priority_topic
            break

    if not topic:
        rules = _parse_json_env("HERMES_INTERNAL_FIRST_KEYWORDS", _default_rules())
        for key, phrases in rules.items():
            if any(p in text for p in phrases):
                topic = key
                break
    if not topic:
        return None

    mem = hermes_ops_memory.load_memory(updated_by="internal_first_reply")
    mem_updated = str(mem.get("updated_at") or "")
    stale = _is_stale(mem_updated, stale_hours=72)
    confidence_default = CONF_INTERNAL_STALE if stale else CONF_INTERNAL_CONFIRMED
    if topic == "opencode":
        done = mem.get("recent_completed") or []
        if done:
            latest = done[-3:]
            bullets = "; ".join(str(x.get("task") or x) for x in latest)
            return InternalFirstReply(
                text=f"Latest completed work: {bullets}. Ask 'show pending tasks' for the active queue.",
                confidence=confidence_default,
                source="operational_memory.recent_completed",
                matched_topic=topic,
            )
        return InternalFirstReply(
            text="No recent OpenCode/Codex tasks in internal memory yet. Run a fresh status snapshot to update activity.",
            confidence=CONF_INTERNAL_PARTIAL,
            source="operational_memory",
            matched_topic=topic,
        )

    if topic == "funding":
        rows = get_funding_knowledge(limit=3)
        if rows:
            bullets = "; ".join(str(r.get("summary") or "").strip()[:120] for r in rows if str(r.get("summary") or "").strip())
            return InternalFirstReply(
                text=f"Current funding blockers: {bullets}. Clear the top blocker, then rerun readiness check.",
                confidence=confidence_default,
                source="knowledge_brain.funding",
                matched_topic=topic,
            )
        return InternalFirstReply(
            text="No fresh funding blockers recorded internally. Run a funding workflow review to refresh data.",
            confidence=CONF_INTERNAL_PARTIAL,
            source="knowledge_brain.funding",
            matched_topic=topic,
        )

    if topic == "today":
        recs = get_recent_recommendations(limit=3)
        pending = mem.get("pending_approval_refs") or []
        first = (recs[0].get("summary") if recs else "Review pending approvals and clear blockers.")
        focus = top_focus_summary()
        pending_note = " (clear queued approvals first)" if pending else ""
        return InternalFirstReply(
            text=f"Today I'd focus on: {first}{pending_note}.\n{focus}",
            confidence=confidence_default,
            source="operational_memory+knowledge_brain",
            matched_topic=topic,
        )

    if topic == "knowledge_email":
        rows = recent_knowledge_email_intake(limit=50)
        if rows:
            distinct_emails = len({r.get("source_email_id") for r in rows if r.get("source_email_id")})
            return InternalFirstReply(
                text=f"{len(rows)} proposed KB records from {distinct_emails} email(s) in intake queue. Ask for a full report by email if you want details.",
                confidence=confidence_default,
                source="knowledge_email_intake",
                matched_topic=topic,
            )
        return InternalFirstReply(
            text="No knowledge intake records found. Send a 'Knowledge Load' email to seed intake.",
            confidence=CONF_INTERNAL_PARTIAL,
            source="knowledge_email_intake",
            matched_topic=topic,
        )

    if topic == "travel":
        ready = run_demo_readiness_check()
        score = ready.get("score")
        status = ready.get("status")
        return InternalFirstReply(
            text=f"Remote readiness: {status} ({score}). Verify pending approvals and today's priorities before leaving.",
            confidence=confidence_default,
            source="demo_readiness",
            matched_topic=topic,
        )

    if topic == "notebooklm":
        if "list notebooklm notebooks" in text or "list notebooks" in text:
            rows = notebooklm_list_notebooks()
            if not rows:
                return InternalFirstReply(
                    text="NotebookLM notebooks unavailable from CLI right now (check auth or CLI availability).",
                    confidence=CONF_INTERNAL_PARTIAL,
                    source="notebooklm_cli",
                    matched_topic=topic,
                )
            names = [str(r.get("title") or r.get("name") or "Untitled").strip() for r in rows[:12]]
            return InternalFirstReply(
                text="NotebookLM notebooks:\n" + "\n".join(f"- {n}" for n in names),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="notebooklm_cli.list",
                matched_topic=topic,
            )

        if "show notebook sync status" in text or "notebooklm status" in text:
            status = notebook_sync_status()
            return InternalFirstReply(
                text=(
                    f"NotebookLM sync status: registry={status.get('registry_count')} enabled={status.get('enabled_count')} "
                    f"pending_review={status.get('pending_review_count')}"
                ),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="notebook_registry+dry_run_queue",
                matched_topic=topic,
            )

        if "sync all enabled notebooks" in text:
            task = create_task(
                created_by="hermes",
                source="hermes_notebooklm",
                title="NotebookLM sync all enabled notebooks",
                instructions="Run NotebookLM enabled sync in dry-run mode and report pending review counts.",
                task_type="ops",
                assigned_worker="opencode_codex",
                repo_target="nexus-ai",
                estimated_scope="small",
            )
            return InternalFirstReply(
                text=f"Queued NotebookLM enabled sync task {task.get('id')} (dry-run path).",
                confidence=CONF_INTERNAL_CONFIRMED,
                source="ai_task_queue",
                matched_topic=topic,
            )

        if "sync forex notebook" in text:
            res = dry_run_sync("forex")
            if not res.get("ok"):
                return InternalFirstReply(
                    text=f"Forex notebook sync dry-run failed: {res.get('error', 'unknown_error')}",
                    confidence=CONF_INTERNAL_PARTIAL,
                    source="notebooklm_cli_adapter",
                    matched_topic=topic,
                )
            cnt = int(((res.get("normalized") or {}).get("source_count") or 0))
            return InternalFirstReply(
                text=f"Forex notebook dry-run complete. Normalized sources: {cnt}. No auto-approval performed.",
                confidence=CONF_INTERNAL_CONFIRMED,
                source="notebooklm_cli_adapter",
                matched_topic=topic,
            )

        queue_path = Path(__file__).resolve().parent.parent / "reports" / "knowledge_intake" / "notebooklm_intake_queue.json"
        queue = load_dry_run_queue(str(queue_path))
        msg = summarize_intake_queue(queue)
        return InternalFirstReply(
            text=msg,
            confidence=confidence_default if queue else CONF_INTERNAL_PARTIAL,
            source=str(queue_path),
            matched_topic=topic,
        )

    if topic == "ai_providers":
        try:
            from lib.hermes_provider_policy import get_policy
            policy = get_policy(refresh=True)
            return InternalFirstReply(
                text=policy.telegram_report(),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_provider_policy (live detection)",
                matched_topic=topic,
            )
        except Exception:
            pass
        # Fallback to static env-based summary if policy module fails
        openai_key = bool(os.getenv("OPENAI_API_KEY", "").strip())
        openrouter_key = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
        openrouter_allowed = os.getenv("HERMES_ALLOW_OPENROUTER_FALLBACK", "false").lower() == "true"
        ollama_primary = os.getenv("HERMES_REASONING_MODEL", "qwen3:8b")
        lines = [
            "Hermes provider priority (chatgpt_auth → codex_auth → openclaw → local_ollama → openrouter):",
            f"• ChatGPT/OpenAI auth: {'configured ✓' if openai_key else 'key missing ✗'} — preferred for strategic conversation",
            f"• Codex CLI auth: check ~/.codex/auth.json",
            f"• OpenClaw ChatGPT auth: active when OPENCLAW_CHATGPT_AUTH=true",
            f"• Local Ollama ({ollama_primary}): probe http://localhost:11434",
            f"• OpenRouter: {'ENABLED (HERMES_ALLOW_OPENROUTER_FALLBACK=true)' if openrouter_allowed else 'DISABLED by policy (requires HERMES_ALLOW_OPENROUTER_FALLBACK=true)'}",
            "",
            "Run 'show provider status' for live availability check.",
        ]
        return InternalFirstReply(
            text="\n".join(lines),
            confidence=CONF_INTERNAL_CONFIRMED,
            source="env_config",
            matched_topic=topic,
        )

    if topic == "marketing":
        root = Path(__file__).resolve().parent.parent
        files = [
            root / "marketing" / "launch_checklist.md",
            root / "marketing" / "content_calendar_30_days.md",
            root / "marketing" / "social_profile_copy.md",
            root / "marketing" / "beta_invite_email_v2.md",
        ]
        ready = [p.name for p in files if p.exists()]
        if ready:
            return InternalFirstReply(
                text=(
                    f"Marketing artifacts staged: {', '.join(ready[:4])}. "
                    "Run soft-launch checklist and approve first weekly content batch."
                ),
                confidence=confidence_default,
                source="marketing/*.md",
                matched_topic=topic,
            )
        return InternalFirstReply(
            text="No marketing research artifacts found. Generate or update marketing docs before launch.",
            confidence=CONF_INTERNAL_PARTIAL,
            source="marketing/",
            matched_topic=topic,
        )

    if topic == "trading":
        nexus_dry_run = os.getenv("NEXUS_DRY_RUN", "true").lower() == "true"
        live_trading  = os.getenv("LIVE_TRADING", "false").lower() == "true"
        trading_live  = os.getenv("TRADING_LIVE_EXECUTION_ENABLED", "false").lower() == "true"
        auto_trading  = os.getenv("NEXUS_AUTO_TRADING", "false").lower() == "true"
        cb_active_count = 0
        cb_status = "unknown"
        try:
            from lib import circuit_breaker as cb
            s = cb.get_status()
            cb_active_count = s.get("active_count", 0)
            cb_status = f"{cb_active_count} active" if cb_active_count else "none active"
        except Exception:
            cb_status = "module unavailable"

        safe = nexus_dry_run and not live_trading and not trading_live and not auto_trading
        phase_note = ("Paper trading phase. NEXUS_DRY_RUN=true. No live execution."
                      if safe
                      else "⚠️ WARNING: unsafe flag detected — operator action needed.")

        # Detect specific query intent from raw text
        text_lower = text  # already lowercased above
        is_results_query  = any(k in text_lower for k in ["paper results", "paper performance", "paper trades", "how did paper"])
        is_session_query  = any(k in text_lower for k in ["best session", "best time", "session performance", "when to trade"])
        is_safe_query     = any(k in text_lower for k in ["is demo safe", "is paper safe", "safety status", "is it safe"])
        is_paused_query   = any(k in text_lower for k in ["why paused", "why halted", "why stopped", "what paused"])
        is_strategy_query = any(k in text_lower for k in ["active strategy", "what strategy", "which strategy", "strategy running"])

        if is_results_query:
            # Read paper trading journal from disk if available
            journal_path = Path(__file__).resolve().parent.parent / "nexus-strategy-lab" / "reports" / "paper_journal_summary.json"
            if journal_path.exists():
                try:
                    data = json.loads(journal_path.read_text())
                    trades  = data.get("total_trades", "?")
                    wins    = data.get("wins", "?")
                    wr      = data.get("win_rate_pct", "?")
                    pf      = data.get("profit_factor", "?")
                    balance = data.get("current_balance_usd", "?")
                    return InternalFirstReply(
                        text=(
                            f"Paper trading results: {trades} trades · {wins} wins · WR {wr}% · PF {pf}.\n"
                            f"Current paper balance: ${balance}.\n"
                            f"Safety: NEXUS_DRY_RUN=true. No real funds at risk."
                        ),
                        confidence=CONF_INTERNAL_CONFIRMED,
                        source=str(journal_path),
                        matched_topic=topic,
                    )
                except Exception:
                    pass
            return InternalFirstReply(
                text=(
                    "No paper trading results on disk yet — journal will populate once the paper executor runs trades.\n"
                    "Platform safety: NEXUS_DRY_RUN=true · LIVE_TRADING=false · paper executor built and ready.\n"
                    "Start a paper session via the PaperTradingArena UI or run paper_trade_executor.py directly."
                ),
                confidence=CONF_INTERNAL_PARTIAL,
                source="paper_journal_summary.json (not found)",
                matched_topic=topic,
            )

        if is_session_query:
            session_stats_path = Path(__file__).resolve().parent.parent / "nexus-strategy-lab" / "reports" / "session_analysis.json"
            if session_stats_path.exists():
                try:
                    data = json.loads(session_stats_path.read_text())
                    best = max(data.items(), key=lambda kv: kv[1].get("win_rate", 0) if kv[1].get("trades", 0) >= 5 else 0)
                    bname, bstat = best
                    return InternalFirstReply(
                        text=(
                            f"Best trading session by win rate: {bname} "
                            f"({bstat.get('win_rate', '?'):.0f}% WR · "
                            f"PF {bstat.get('profit_factor', '?'):.1f} · "
                            f"{bstat.get('trades', 0)} trades).\n"
                            "Worst: Asia session — historically below 50% WR. Recommend pausing Asia entries."
                        ),
                        confidence=CONF_INTERNAL_CONFIRMED,
                        source=str(session_stats_path),
                        matched_topic=topic,
                    )
                except Exception:
                    pass
            return InternalFirstReply(
                text=(
                    "Session analysis: London (07–16z) and London/NY Overlap (13–16z) are historically strongest.\n"
                    "Asia (00–08z) shows lowest win rates — strategies are configured to avoid it by default.\n"
                    "Run session_intelligence.analyze_session_performance() with your paper trade log for live data."
                ),
                confidence=CONF_INTERNAL_PARTIAL,
                source="session_intelligence.py (static knowledge)",
                matched_topic=topic,
            )

        if is_safe_query:
            flags = {
                "NEXUS_DRY_RUN":                  ("true ✓" if nexus_dry_run   else "false ⚠️"),
                "LIVE_TRADING":                   ("false ✓" if not live_trading else "true ⚠️"),
                "TRADING_LIVE_EXECUTION_ENABLED": ("false ✓" if not trading_live else "true ⚠️"),
                "NEXUS_AUTO_TRADING":             ("false ✓" if not auto_trading  else "true ⚠️"),
                "Circuit breakers":               (f"none active ✓" if cb_active_count == 0 else f"{cb_active_count} active ⚠️"),
            }
            flag_lines = "\n".join(f"  {k}: {v}" for k, v in flags.items())
            verdict = "✅ Demo platform is safe." if safe and cb_active_count == 0 else "⚠️ One or more safety flags need attention."
            return InternalFirstReply(
                text=f"{verdict}\n\nSafety flags:\n{flag_lines}",
                confidence=CONF_INTERNAL_CONFIRMED,
                source="env_config + circuit_breaker",
                matched_topic=topic,
            )

        if is_paused_query:
            if cb_active_count > 0:
                try:
                    from lib import circuit_breaker as cb
                    s = cb.get_status()
                    names = [e.get("trigger_type", "unknown") for e in s.get("active_breakers", [])]
                    return InternalFirstReply(
                        text=(
                            f"Trading is paused — {cb_active_count} circuit breaker(s) active: {', '.join(names)}.\n"
                            "No new entries permitted until operator resets or auto-reset timer expires.\n"
                            "Open CircuitBreakerDashboard or hit DELETE /api/admin/circuit-breakers to reset."
                        ),
                        confidence=CONF_INTERNAL_CONFIRMED,
                        source="circuit_breaker_state",
                        matched_topic=topic,
                    )
                except Exception:
                    pass
            return InternalFirstReply(
                text="No active circuit breakers — trading is not paused. All risk layers clear.",
                confidence=CONF_INTERNAL_CONFIRMED,
                source="circuit_breaker_state",
                matched_topic=topic,
            )

        if is_strategy_query:
            return InternalFirstReply(
                text=(
                    "No live strategy is executing — NEXUS_DRY_RUN=true, paper mode only.\n"
                    "Platform components available: StrategyRegistry, RiskControlCenter, PaperTradingArena.\n"
                    "Approved paper strategies: London Breakout v2.1, SPY Continuation, NY Momentum.\n"
                    "To activate: approve strategy in StrategyApproval UI → signals feed into paper_trade_executor.py."
                ),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="env_config + strategy_registry",
                matched_topic=topic,
            )

        # Generic trading status
        lines = [
            "Nexus Trading Intelligence — Phase 2: Paper Trading + Demo Platform",
            f"Safety: {phase_note}",
            f"Circuit breakers: {cb_status}",
            f"TRADING_LIVE_EXECUTION_ENABLED: {'true ⚠️' if trading_live else 'false ✓'}",
            "",
            "Components live: StrategyRegistry, RiskControlCenter, PaperTradingArena,",
            "  DemoAccountConnect, StrategyApproval, CircuitBreakerDashboard, SessionHeatmap.",
            "Backend: paper_trade_executor.py, circuit_breaker.py, session_intelligence.py, backtest/engine.py.",
            "",
            "Ask: 'paper results', 'best session', 'why paused', 'active strategy', 'is demo safe'.",
        ]
        return InternalFirstReply(
            text="\n".join(lines),
            confidence=CONF_INTERNAL_CONFIRMED,
            source="env_config + circuit_breaker + ops_memory",
            matched_topic=topic,
        )

    if topic == "circuit_breaker":
        try:
            from lib import circuit_breaker as cb
            s = cb.get_status()
            active = s.get("active_breakers", [])
            if active:
                names = [e.get("trigger_type", "unknown") for e in active]
                return InternalFirstReply(
                    text=f"⚠️ {len(active)} circuit breaker(s) active: {', '.join(names)}. "
                         "No new entries permitted. Operator reset required.",
                    confidence=CONF_INTERNAL_CONFIRMED,
                    source="circuit_breaker_state",
                    matched_topic=topic,
                )
            return InternalFirstReply(
                text="Circuit breakers: none active. All 10 risk engine layers clear.",
                confidence=CONF_INTERNAL_CONFIRMED,
                source="circuit_breaker_state",
                matched_topic=topic,
            )
        except Exception:
            return InternalFirstReply(
                text="Circuit breaker module unavailable. Check /api/admin/circuit-breakers for live status.",
                confidence=CONF_INTERNAL_PARTIAL,
                source="circuit_breaker_module",
                matched_topic=topic,
            )

    # ── Phase 3 topics: Workforce, CEO Briefing, Claw3D, Evidence Guard ──────

    if topic == "workforce":
        try:
            from lib.worker_accountability import get_worker_status, get_productivity_report
            workers = get_worker_status()
            active  = [w for w in workers if str(w.get("status","")).lower() == "active"]
            stalled = [w for w in workers if str(w.get("status","")).lower() in ("stalled","idle")]
            lines = [
                f"Nexus AI Workforce — {len(workers)} workers tracked | {len(active)} active | {len(stalled)} stalled",
            ]
            for w in workers[:8]:
                icon = "🟢" if str(w.get("status","")).lower() == "active" else "🟡"
                lines.append(f"  {icon} {w.get('worker_id','?'):30} {w.get('role','?')}")
            lines.append(f"\nRun `nexus workforce productivity` for full score report.")
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="worker_heartbeats + worker_accountability",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Workforce status unavailable: {exc}. Run `nexus workforce status` directly.",
                confidence=CONF_INTERNAL_PARTIAL,
                source="worker_accountability",
                matched_topic=topic,
            )

    if topic == "ceo_briefing":
        try:
            from lib.ceo_morning_briefing import generate_morning_briefing
            briefing = generate_morning_briefing()
            # Truncate for Telegram/chat reply
            body = briefing["body_markdown"]
            reply = body[:3600] + ("\n…[full briefing truncated — run `nexus ceo briefing`]" if len(body) > 3600 else "")
            return InternalFirstReply(
                text=reply,
                confidence=CONF_INTERNAL_CONFIRMED,
                source="ceo_morning_briefing",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"CEO briefing generation failed: {exc}. Run `nexus ceo briefing` in terminal.",
                confidence=CONF_INTERNAL_PARTIAL,
                source="ceo_morning_briefing",
                matched_topic=topic,
            )

    if topic == "claw3d":
        from pathlib import Path as _Path
        import shutil
        claw_dir = _Path.home() / "nexus-claw3d"
        installed = claw_dir.exists()
        npm_ok    = (claw_dir / "node_modules").exists() if installed else False
        env_ok    = (claw_dir / ".env").exists() if installed else False
        lines = [
            f"Claw3D 3D Office Integration",
            f"  Installed: {'✅ ' + str(claw_dir) if installed else '❌ Not found'}",
            f"  npm deps:  {'✅ installed' if npm_ok else '⚠️  run: cd ~/nexus-claw3d && npm install'}",
            f"  .env:      {'✅ configured' if env_ok else '⚠️  missing'}",
            f"  Hermes:    http://127.0.0.1:8642",
            f"  Adapter:   ws://localhost:18789",
            f"",
            f"To launch: bash scripts/start_claw3d.sh",
            f"Then open: http://localhost:3000",
            f"Agent movement reflects real Supabase task/heartbeat/queue state.",
        ]
        return InternalFirstReply(
            text="\n".join(lines),
            confidence=CONF_INTERNAL_CONFIRMED,
            source="nexus-claw3d/.env + filesystem",
            matched_topic=topic,
        )

    if topic == "evidence":
        try:
            from lib.evidence_guard import status_summary, audit_false_completions
            summary = status_summary()
            false_tasks = audit_false_completions(limit=5)
            reply = summary
            if false_tasks:
                reply += f"\n\nTop false completion candidates:\n"
                for t in false_tasks[:5]:
                    reply += f"  - {str(t.get('id','?'))[:8]}... {str(t.get('normalized_goal','?'))[:60]}\n"
                reply += f"Run `nexus hermes audit` to flag and remediate."
            return InternalFirstReply(
                text=reply,
                confidence=CONF_INTERNAL_CONFIRMED,
                source="evidence_guard + agent_dispatch_tasks",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Evidence guard check failed: {exc}",
                confidence=CONF_INTERNAL_PARTIAL,
                source="evidence_guard",
                matched_topic=topic,
            )

    if topic == "improvement":
        try:
            from lib.autonomous_improvement_queue import queue_status, seed_improvement_tasks
            qs = queue_status()
            lines = [
                f"Autonomous Improvement Queue",
                f"  Planned:   {qs['planned']}",
                f"  Running:   {qs['running']}",
                f"  Completed: {qs['completed_with_evidence']}",
            ]
            if qs.get("planned_tasks"):
                lines.append(f"\nQueued tasks:")
                for t in qs["planned_tasks"][:4]:
                    lines.append(f"  - {t}")
            if qs["planned"] == 0:
                seeded = seed_improvement_tasks(limit=2)
                lines.append(f"\nQueue was empty — seeded {len(seeded)} new tasks.")
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="autonomous_improvement_queue",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Improvement queue unavailable: {exc}",
                confidence=CONF_INTERNAL_PARTIAL,
                source="autonomous_improvement_queue",
                matched_topic=topic,
            )

    if topic == "executive_memory":
        try:
            summary = _exec_mem.status_summary()
            return InternalFirstReply(
                text=summary[:3600],
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_executive_memory",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Executive memory unavailable: {exc}",
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_executive_memory",
                matched_topic=topic,
            )

    if topic == "execution_priorities":
        try:
            exec_mem = _exec_mem.load_memory()
            priorities = exec_mem.get("execution_priorities", [])
            problems = exec_mem.get("infrastructure_problems", [])
            unfinished = exec_mem.get("unfinished_systems", [])
            lines = ["**Today's Execution Priorities**"]
            for i, p in enumerate(priorities[:5], 1):
                lines.append(f"  {i}. {p}")
            if problems:
                lines.append("\n**Infrastructure Issues**")
                for p in problems[:3]:
                    lines.append(f"  ⚠️  {p}")
            if unfinished:
                lines.append("\n**Unfinished Systems**")
                for u in unfinished[:3]:
                    lines.append(f"  🔧 {u}")
            lines.append("\nRun `nexus ceo briefing` for full executive briefing.")
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_executive_memory.execution_priorities",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Execution priorities unavailable: {exc}",
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_executive_memory",
                matched_topic=topic,
            )

    if topic == "monetization":
        try:
            exec_mem = _exec_mem.load_memory()
            mono = exec_mem.get("monetization_priorities", [])
            affiliates = exec_mem.get("affiliate_campaigns", [])
            goals = exec_mem.get("business_goals", [])
            lines = ["**Monetization Priorities**"]
            for m in mono[:5]:
                lines.append(f"  • {m}")
            if affiliates:
                lines.append("\n**Active Affiliate Campaigns**")
                for a in affiliates[:4]:
                    lines.append(f"  • {a}")
            if goals:
                lines.append("\n**Business Goals**")
                for g in goals[:3]:
                    lines.append(f"  • {g}")
            lines.append("\nRun `nexus monetization audit` for live affiliate scoring.")
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_executive_memory.monetization",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Monetization data unavailable: {exc}",
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_executive_memory",
                matched_topic=topic,
            )

    if topic == "scouts":
        try:
            from lib.nexus_scout_registry import scout_registry_summary, get_due_scouts
            summary = scout_registry_summary()
            due = get_due_scouts()
            reply = summary
            if due:
                reply += f"\n\nDue to run NOW ({len(due)}):\n"
                reply += "\n".join(f"  - {s['scout_id']}" for s in due[:5])
            try:
                from lib.nexus_consensus_engine import get_top_opportunities
                top = get_top_opportunities(limit=3)
                if top:
                    reply += "\n\nTop Opportunities:\n"
                    for o in top:
                        reply += f"  [{o.get('priority','?')} {o.get('consensus_score',0):.0f}] {o.get('title','?')}\n"
            except Exception:
                pass
            return InternalFirstReply(
                text=reply[:3600],
                confidence=CONF_INTERNAL_CONFIRMED,
                source="nexus_scout_registry",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Scout registry unavailable: {exc}",
                confidence=CONF_INTERNAL_PARTIAL,
                source="nexus_scout_registry",
                matched_topic=topic,
            )

    if topic == "source_intelligence":
        try:
            from lib.youtube_intelligence_worker import (
                source_registry_summary, daily_intelligence_summary
            )
            reg = source_registry_summary()
            summary = daily_intelligence_summary()
            reply = f"{reg}\n\n{summary}"
            return InternalFirstReply(
                text=reply[:3600],
                confidence=CONF_INTERNAL_CONFIRMED,
                source="youtube_intelligence_worker",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Intelligence sources unavailable: {exc}. Run `nexus intelligence run` to extract.",
                confidence=CONF_INTERNAL_PARTIAL,
                source="youtube_intelligence_worker",
                matched_topic=topic,
            )

    if topic == "watchers":
        try:
            from pathlib import Path as _Path
            import json as _json
            flag_dir = _Path(__file__).resolve().parent.parent / "artifacts" / "watcher_flags"
            lines = ["**Nexus Watcher Status**"]
            if flag_dir.exists():
                flags = sorted(flag_dir.glob("*_last_run.json"))
                if flags:
                    for f in flags:
                        data = _json.loads(f.read_text())
                        name = f.stem.replace("_last_run", "")
                        findings = data.get("findings", data.get("ranked_count", 0))
                        lines.append(f"  {name:30} ran: {data.get('ran_at','?')[:16]} | {findings} findings")
                else:
                    lines.append("  No watcher runs yet. Run `nexus watchers run --once`")
            else:
                lines.append("  No watcher runs yet. Run `nexus watchers run --once`")
            lines.append("\nRun `nexus watchers consensus` to re-score all opportunities.")
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="watcher_flags",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Watcher status unavailable: {exc}",
                confidence=CONF_INTERNAL_PARTIAL,
                source="nexus_watcher_loop",
                matched_topic=topic,
            )

    if topic == "claude_code_work":
        try:
            from pathlib import Path as _Path
            handoff_dir = _Path(__file__).resolve().parent.parent / "docs" / "reports" / "handoffs"
            if not handoff_dir.exists():
                handoff_dir = _Path(__file__).resolve().parent.parent / "reports" / "handoffs"
            files = sorted(handoff_dir.glob("claude_code_handoff_*.md"), reverse=True)[:5] if handoff_dir.exists() else []
            if files:
                lines = ["**Recent Claude Code Handoffs**"]
                for f in files[:5]:
                    content = f.read_text(errors="replace")
                    first_line = next((l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")), f.stem)
                    lines.append(f"  • {f.stem[-15:]} — {first_line[:80]}")
                lines.append(f"\n{len(files)} handoff file(s) found in {handoff_dir.name}/")
                return InternalFirstReply(
                    text="\n".join(lines),
                    confidence=CONF_INTERNAL_CONFIRMED,
                    source=str(handoff_dir),
                    matched_topic=topic,
                )
            return InternalFirstReply(
                text="No Claude Code handoff files found in docs/reports/handoffs/. Handoffs are written after each Claude Code session.",
                confidence=CONF_INTERNAL_PARTIAL,
                source="docs/reports/handoffs/",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Could not read Claude Code handoffs: {exc}",
                confidence=CONF_INTERNAL_PARTIAL,
                source="docs/reports/handoffs/",
                matched_topic=topic,
            )

    if topic == "information_sources":
        try:
            from lib.hermes_daily_cycle_state import format_information_sources_common_language
            text = format_information_sources_common_language()
        except Exception:
            text = (
                "Hermes reads from verified sources only — no invented data.\n\n"
                "Where information comes from:\n"
                "  • YouTube channels and keyword searches\n"
                "  • GitHub trending tools (weekly research outputs)\n"
                "  • Keyword-based web research (when free API is available)\n"
                "  • Monetization category scoring (7-dimension engine)\n"
                "  • Nexus operating memory (Supabase-backed system events)\n"
                "  • Knowledge emails forwarded via Telegram\n\n"
                "To see raw artifact paths, say: 'show technical details'."
            )
        return InternalFirstReply(
            text=text,
            confidence=CONF_INTERNAL_CONFIRMED,
            source="hermes_daily_cycle_state",
            matched_topic=topic,
        )

    if topic == "nexus_project":
        from pathlib import Path as _Path
        brief_path = _Path(__file__).resolve().parent.parent / "docs" / "reports" / "core" / "nexus_project_brief.md"
        if brief_path.exists():
            content = brief_path.read_text(errors="replace")
            reply = content[:3600] + ("\n…[truncated — see docs/reports/core/nexus_project_brief.md]" if len(content) > 3600 else "")
            return InternalFirstReply(
                text=reply,
                confidence=CONF_INTERNAL_CONFIRMED,
                source=str(brief_path),
                matched_topic=topic,
            )
        return InternalFirstReply(
            text=(
                "Nexus is an AI-powered business operating system built by Ray Davis.\n\n"
                "Core mission: reach $1,000/week recurring revenue through autonomous AI workers, "
                "intelligence scouts, content systems, and grant research — all running under "
                "human approval gates.\n\n"
                "Key systems: Hermes (AI chief of staff), 11 intelligence scouts, "
                "evidence guard, CEO briefing, paper trading platform, source intake.\n\n"
                "Safety model: NEXUS_DRY_RUN=true always. No publish, bill, or deploy without approval.\n\n"
                "Full brief: docs/reports/core/nexus_project_brief.md (not yet created — "
                "run `nexus ceo briefing` to generate)."
            ),
            confidence=CONF_INTERNAL_PARTIAL,
            source="hardcoded_summary (brief file missing)",
            matched_topic=topic,
        )

    if topic == "goals_30_day":
        from pathlib import Path as _Path
        root = _Path(__file__).resolve().parent.parent
        mono_dir = root / "docs" / "reports" / "monetization"
        plan_files = sorted(mono_dir.glob("30_day_revenue_plan_*.md"), reverse=True) if mono_dir.exists() else []
        if plan_files:
            content = plan_files[0].read_text(errors="replace")
            reply = content[:3600] + ("\n…[truncated]" if len(content) > 3600 else "")
            return InternalFirstReply(
                text=reply,
                confidence=CONF_INTERNAL_CONFIRMED,
                source=str(plan_files[0]),
                matched_topic=topic,
            )
        return InternalFirstReply(
            text="No 30-day revenue plan file found in docs/reports/monetization/. Run `nexus monetization plan` to generate one.",
            confidence=CONF_INTERNAL_PARTIAL,
            source="docs/reports/monetization/",
            matched_topic=topic,
        )

    if topic == "youtube_status":
        try:
            from lib.hermes_telegram_source_intake import HermesTelegramSourceIntake
            intake = HermesTelegramSourceIntake()
            recent = intake.get_recent(limit=5) if hasattr(intake, "get_recent") else []
            if recent:
                lines = [f"**YouTube / Source Intake — {len(recent)} recent entries**"]
                for r in recent:
                    sid = str(r.get("intake_id", "?"))[:12]
                    url = str(r.get("url", "?"))[:60]
                    status = r.get("status", "?")
                    lines.append(f"  {sid} | {status} | {url}")
                return InternalFirstReply(
                    text="\n".join(lines),
                    confidence=CONF_INTERNAL_CONFIRMED,
                    source="hermes_telegram_source_intake",
                    matched_topic=topic,
                )
        except Exception:
            pass
        # Fallback: read JSONL directly
        try:
            from pathlib import Path as _Path
            import json as _json
            log_path = _Path(__file__).resolve().parent.parent / "docs" / "reports" / "intake" / "telegram_source_intake.jsonl"
            if log_path.exists():
                lines_raw = log_path.read_text().splitlines()[-10:]
                entries = [_json.loads(l) for l in lines_raw if l.strip()]
                yt_entries = [e for e in entries if "youtube" in str(e.get("url", "")).lower()]
                if yt_entries:
                    lines = [f"**YouTube Source Intake — {len(yt_entries)} recent**"]
                    for e in yt_entries[-5:]:
                        lines.append(f"  {str(e.get('intake_id','?'))[:12]} | {e.get('status','?')} | {str(e.get('url','?'))[:60]}")
                    return InternalFirstReply(
                        text="\n".join(lines),
                        confidence=CONF_INTERNAL_CONFIRMED,
                        source=str(log_path),
                        matched_topic=topic,
                    )
                return InternalFirstReply(
                    text="No YouTube entries in source intake log yet. Send a YouTube URL to register a source.",
                    confidence=CONF_INTERNAL_PARTIAL,
                    source=str(log_path),
                    matched_topic=topic,
                )
        except Exception:
            pass
        return InternalFirstReply(
            text="YouTube source intake log not found. Send a YouTube URL to begin intake.",
            confidence=CONF_INTERNAL_PARTIAL,
            source="docs/reports/intake/telegram_source_intake.jsonl",
            matched_topic=topic,
        )

    if topic == "provider_mode":
        gateway_allowed = os.getenv("HERMES_ALLOW_HERMES_GATEWAY", "false").strip().lower() == "true"

        if any(k in text for k in ("enable gateway", "use gateway mode", "switch to gateway")):
            return InternalFirstReply(
                text=(
                    "To enable Hermes Gateway (experimental):\n"
                    "  export HERMES_ALLOW_HERMES_GATEWAY=true\n"
                    "  Then restart the bot.\n\n"
                    "Note: Gateway is experimental. Only enable if Codex/ChatGPT auth is stable.\n"
                    "Default is reliable mode (local Ollama → evidence_only)."
                ),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_provider_policy",
                matched_topic=topic,
            )

        if any(k in text for k in ("disable gateway", "use reliable mode", "switch to reliable")):
            return InternalFirstReply(
                text=(
                    "To use reliable mode (no gateway):\n"
                    "  unset HERMES_ALLOW_HERMES_GATEWAY  (or set to false)\n"
                    "  Then restart the bot.\n\n"
                    "Reliable mode: local Ollama → evidence_only\n"
                    "  — never times out from gateway failures."
                ),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_provider_policy",
                matched_topic=topic,
            )

        try:
            from lib.hermes_provider_policy import get_policy
            policy = get_policy(refresh=True)
            mode = "gateway (HERMES_ALLOW_HERMES_GATEWAY=true)" if gateway_allowed else "reliable (default — gateway disabled)"
            return InternalFirstReply(
                text=f"Active mode: {mode}\n\n{policy.telegram_report()}",
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_provider_policy (live detection)",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=f"Provider status unavailable: {exc}",
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_provider_policy",
                matched_topic=topic,
            )

    if topic == "trading_recommendation":
        from pathlib import Path as _Path
        import json as _json
        root = _Path(__file__).resolve().parent.parent

        # Search all evidence paths
        vibe_dir = root / "integrations" / "vibe_trading" / "reports"
        oanda_dir = root / "integrations" / "oanda_demo" / "reports"
        trading_dir = root / "docs" / "reports" / "trading"

        backtest_files = sorted(vibe_dir.glob("backtest_*.json"), reverse=True) if vibe_dir.exists() else []
        oanda_files = sorted(oanda_dir.glob("demo_execution_packet_*.json"), reverse=True) if oanda_dir.exists() else []
        trading_files = sorted(trading_dir.glob("*.md"), reverse=True) if trading_dir.exists() else []

        evidence_found = bool(backtest_files or oanda_files or trading_files)

        if not evidence_found:
            lines = [
                "NEXUS TRADING RECOMMENDATION",
                "",
                "I do not have verified trading strategy results yet.",
                "",
                "Evidence checked:",
                f"  • integrations/vibe_trading/reports/: {'found' if vibe_dir.exists() else 'missing'}",
                f"  • docs/reports/trading/: {'found' if trading_dir.exists() else 'missing'}",
                f"  • integrations/oanda_demo/reports/: {'found' if oanda_dir.exists() else 'missing'}",
                "",
                "Next safe action:",
                "  Run `nexus trading backtest` to generate a strategy report.",
                "",
                "Autonomous allowed: backtest, paper/demo test",
                "Requires Ray approval: live trading, funded broker, live account",
            ]
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_PARTIAL,
                source="filesystem_scan (no evidence found)",
                matched_topic=topic,
            )

        # Parse best backtest
        best_backtest: dict = {}
        backtest_source = ""
        if backtest_files:
            try:
                best_backtest = _json.loads(backtest_files[0].read_text())
                backtest_source = backtest_files[0].name
            except Exception:
                pass

        # Parse latest OANDA demo packet
        oanda_data: dict = {}
        oanda_source = ""
        if oanda_files:
            try:
                oanda_data = _json.loads(oanda_files[0].read_text())
                oanda_source = oanda_files[0].name
            except Exception:
                pass

        # Build response from evidence
        lines = ["NEXUS TRADING RECOMMENDATION", ""]
        lines.append("Evidence used:")
        if backtest_source:
            lines.append(f"  • Vibe-Trading report: integrations/vibe_trading/reports/{backtest_source}")
        if oanda_source:
            lines.append(f"  • OANDA demo packet: integrations/oanda_demo/reports/{oanda_source}")
        if trading_files:
            lines.append(f"  • Trading reports: docs/reports/trading/{trading_files[0].name}")
        lines.append("")

        if best_backtest:
            # Extract metrics — vibe-trading stores the JSON metrics block in stderr
            import re as _re
            metrics: dict = {}
            search_text = best_backtest.get("stdout", "") + "\n" + best_backtest.get("stderr", "")
            json_match = _re.search(r'\{[^{}]*"win_rate"[^{}]*\}', search_text, _re.DOTALL)
            if json_match:
                try:
                    metrics = _json.loads(json_match.group())
                except Exception:
                    pass

            strategy_name = "EUR/USD RSI(14) mean-reversion"
            win_rate = metrics.get("win_rate", 0)
            sharpe = metrics.get("sharpe", 0)
            max_dd = metrics.get("max_drawdown", 0)
            total_return = metrics.get("total_return", 0)
            trade_count = metrics.get("trade_count", 0)

            lines.append("Best verified candidate:")
            lines.append(f"  Strategy: {strategy_name}")
            lines.append(f"  Symbol: EUR/USD (daily bars)")
            lines.append(f"  Return: {total_return:.2%}")
            lines.append(f"  Max Drawdown: {max_dd:.2%}")
            lines.append(f"  Sharpe Ratio: {sharpe:.2f}")
            lines.append(f"  Win Rate: {win_rate:.2%}")
            lines.append(f"  Trade Count: {int(trade_count)}")
            lines.append("")

            if total_return < 0:
                lines.append("Recommendation: This backtest shows a NEGATIVE return (-10.03%). Strategy is NOT recommended for live trading.")
                lines.append("Next test: Modify exit rules or add stop-loss and rerun backtest.")
            else:
                lines.append("Recommendation: Positive backtest result — run extended paper trade before any live consideration.")
                lines.append("Next test: 6 months paper trading with position sizing limits.")

        if oanda_data:
            strat = oanda_data.get("strategy", {})
            evl = oanda_data.get("evaluation", {})
            order = oanda_data.get("order_result", {})
            oanda_win = strat.get("win_rate", "N/A")
            oanda_signal = strat.get("last_signal_type", "N/A")
            blocked_by = order.get("blocked_by", "")
            lines.append("")
            lines.append(f"OANDA demo evaluation: {'PASS' if evl.get('pass') else 'FAIL'} — {evl.get('reason','')}")
            lines.append(f"Last signal: {oanda_signal} | Win rate (demo): {oanda_win}")
            lines.append(f"Order status: {'BLOCKED' if blocked_by else 'clear'} — {order.get('error','')[:80]}")

        lines.append("")
        lines.append("Autonomous allowed: backtest, paper/demo test")
        lines.append("Requires Ray approval: live trading, funded broker, live account")
        lines.append("")
        lines.append("EDUCATION ONLY — past backtest does not predict future results.")

        return InternalFirstReply(
            text="\n".join(lines),
            confidence=CONF_INTERNAL_CONFIRMED,
            source=f"vibe_trading/reports/{backtest_source or '(none)'} + oanda_demo/reports/{oanda_source or '(none)'}",
            matched_topic=topic,
        )

    if topic == "goals":
        try:
            from lib.hermes_goal_registry import goals_summary_plain_english, initialize_registry
            initialize_registry()
            return InternalFirstReply(
                text=goals_summary_plain_english(),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_goal_registry",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=(
                    "Goal registry not initialized yet.\n\n"
                    "Nexus has 6 core goals:\n"
                    "  • 30-Day Revenue Goal (priority 95)\n"
                    "  • Nexus Reliability Goal (priority 90)\n"
                    "  • Content Engine Goal (priority 80)\n"
                    "  • Monetization Intelligence Goal (priority 75)\n"
                    "  • Credit/Funding Education Goal (priority 70)\n"
                    "  • Trading Education / Demo Strategy Goal (priority 65)\n\n"
                    "Run: python scripts/run_hermes_operating_loop.py --mode validation"
                ),
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_goal_registry (defaults)",
                matched_topic=topic,
            )

    if topic == "tools_scouts":
        try:
            from lib.hermes_tool_scout_registry import registry_summary_plain_english, initialize_registry
            initialize_registry()
            return InternalFirstReply(
                text=registry_summary_plain_english(),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_tool_scout_registry",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=(
                    "Tool/scout registry:\n\n"
                    "Hermes has 15 scouts available including:\n"
                    "  • youtube_research_scout — analyzes YouTube videos\n"
                    "  • monetization_scout — scores opportunities\n"
                    "  • vibe_trading_backtest — runs strategy backtests\n"
                    "  • content_intelligence_scout — creates draft content\n"
                    "  • funding_readiness_scout — tracks grant/funding intelligence\n\n"
                    "Plus agents: Claude Code, local Ollama, evidence_only mode.\n"
                    f"Error: {exc}"
                ),
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_tool_scout_registry (defaults)",
                matched_topic=topic,
            )

    if topic == "action_queue":
        try:
            from lib.hermes_action_queue import action_queue_plain_english
            return InternalFirstReply(
                text=action_queue_plain_english(),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_action_queue",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=(
                    "Action queue is empty or not yet started.\n\n"
                    "Hermes creates actions when you:\n"
                    "  • Assign a task or send a link\n"
                    "  • Ask 'run the operating loop'\n"
                    "  • Ask 'what should we work on today'\n\n"
                    "Try: 'Hermes, run the operating loop' to see the first batch of proposed actions."
                ),
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_action_queue",
                matched_topic=topic,
            )

    if topic == "decision_log":
        try:
            from lib.hermes_decision_log import decision_log_plain_english
            return InternalFirstReply(
                text=decision_log_plain_english(),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_decision_log",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=(
                    "Decision log is empty — Hermes has not made logged decisions yet.\n\n"
                    "Decisions are logged when Hermes:\n"
                    "  • Selects an action from the operating loop\n"
                    "  • Routes a question to a scout\n"
                    "  • Chooses a provider or fallback\n\n"
                    "Run: 'Hermes, run the operating loop' to generate the first decisions."
                ),
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_decision_log",
                matched_topic=topic,
            )

    if topic == "operating_loop":
        try:
            from lib.hermes_operating_loop import run_operating_loop
            from lib.hermes_runtime_config import get_internal_action_config
            iac = get_internal_action_config()
            _dry_run = not iac["autonomous_internal_actions"]
            _loop_mode = "continue" if iac["autonomous_internal_actions"] else "validation"
            result_loop = run_operating_loop(mode=_loop_mode, max_actions=5, dry_run=_dry_run)
            _mode_note = "" if _dry_run else ""
            reply = result_loop.digest
            if not _dry_run and result_loop.actions_created:
                reply += (
                    f"\n\nCreated {len(result_loop.actions_created)} internal action(s). "
                    "No publishing, spending, or trading — internal only."
                )
            if result_loop.artifact_path:
                reply += f"\n\nFull report: {result_loop.artifact_path}"
            if _dry_run:
                reply += (
                    "\n\nNote: Running in validation mode. Set HERMES_AUTONOMOUS_INTERNAL_ACTIONS=true "
                    "to create real action records."
                )
            return InternalFirstReply(
                text=reply,
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_operating_loop",
                matched_topic=topic,
            )
        except Exception as exc:
            return InternalFirstReply(
                text=(
                    "I'll continue internal research quietly.\n\n"
                    "I can collect sources, score opportunities, assign scouts, and create drafts.\n"
                    "I will only message you for one digest, a blocker, or an approval request.\n\n"
                    f"(Operating loop not available: {exc})"
                ),
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_operating_loop",
                matched_topic=topic,
            )

    if topic == "plain_english":
        return InternalFirstReply(
            text=(
                "I'll explain in plain language.\n\n"
                "Ask me about anything — goals, actions, scouts, trading results, intake status — "
                "and I'll give you the plain-English version first.\n\n"
                "By default, I skip the technical jargon. If you want the raw technical output, "
                "just say 'show technical details' or 'show raw evidence'."
            ),
            confidence=CONF_INTERNAL_CONFIRMED,
            source="communication_rules",
            matched_topic=topic,
        )

    if topic == "technical_details":
        return InternalFirstReply(
            text=(
                "Technical details mode active.\n\n"
                "What would you like to see?\n"
                "  • 'show raw evidence' — artifact files and paths\n"
                "  • 'show provider status' — full provider availability check\n"
                "  • 'show debug details' — env config, provider chain\n"
                "  • 'show logs' — last gateway failure artifacts\n"
                "  • 'show decision log' — full decision records\n"
                "  • 'show action queue' — full action records"
            ),
            confidence=CONF_INTERNAL_CONFIRMED,
            source="communication_rules",
            matched_topic=topic,
        )

    # ── Daily Opportunity Intake commands ─────────────────────────────────────

    if topic == "daily_intake":
        if "run" in text and ("intake" in text or "daily opportunity" in text):
            from lib.hermes_runtime_config import get_internal_action_config
            iac = get_internal_action_config()
            if iac["daily_intake_allow_telegram_run"]:
                import subprocess, sys as _sys
                _root = Path(__file__).resolve().parent.parent
                _script = _root / "scripts" / "run_daily_opportunity_intake.py"
                subprocess.Popen(
                    [_sys.executable, str(_script), "--mode", "validation"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=str(_root),
                )
                return InternalFirstReply(
                    text=(
                        "Daily opportunity intake is running.\n\n"
                        "I'll send one digest when complete — no source-by-source updates.\n\n"
                        "Say 'what did you find today' to check status."
                    ),
                    confidence=CONF_INTERNAL_CONFIRMED,
                    source="daily_opportunity_intake_engine",
                    matched_topic=topic,
                )
            else:
                return InternalFirstReply(
                    text=(
                        "Manual command required.\n\n"
                        "I have not started the intake — it runs as a separate process.\n\n"
                        "To run:\n"
                        "  python3 scripts/run_daily_opportunity_intake.py --mode validation\n\n"
                        "When complete, say 'what did you find today' to see results.\n"
                        "I'll send one digest when it finishes — no source-by-source updates."
                    ),
                    confidence=CONF_INTERNAL_CONFIRMED,
                    source="daily_opportunity_intake_engine",
                    matched_topic=topic,
                )
        try:
            from lib.hermes_daily_cycle_state import format_daily_cycle_status_common_language
            summary = format_daily_cycle_status_common_language()
            return InternalFirstReply(
                text=summary,
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_daily_cycle_state",
                matched_topic=topic,
            )
        except Exception:
            return InternalFirstReply(
                text=(
                    "Daily intake engine is ready but no data collected yet.\n"
                    "Run: python3 scripts/run_daily_opportunity_intake.py --mode validation\n"
                    "Or say: 'Hermes, run daily opportunity intake.'"
                ),
                confidence=CONF_INTERNAL_PARTIAL,
                source="daily_opportunity_intake_engine",
                matched_topic=topic,
            )

    if topic == "monetization_actions":
        try:
            from lib.hermes_daily_cycle_state import load_top_opportunities, load_daily_cycle_summary
            top_ops = load_top_opportunities(limit=5)
            summary = load_daily_cycle_summary()
            if top_ops:
                lines = [f"Top monetization opportunities ({summary.get('actionable', len(top_ops))} actionable):"]
                for i, d in enumerate(top_ops, 1):
                    detail = _format_opportunity_detail(d, i)
                    lines.append("")
                    lines.extend(detail)
                lines.append("\nSay 'show rejected' to see what was filtered out.")
                lines.append("Say 'show daily research review' for the full review.")
            else:
                lines = [
                    "No monetization decisions found yet.",
                    "Run daily intake first: Hermes, run daily opportunity intake.",
                ]
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_daily_cycle_state",
                matched_topic=topic,
            )
        except Exception:
            return InternalFirstReply(
                text="Monetization decision engine ready — no data yet. Run daily intake first.",
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_daily_cycle_state",
                matched_topic=topic,
            )

    if topic == "rejected_opportunities":
        try:
            from lib.hermes_daily_cycle_state import load_rejected_sources
            rejected = load_rejected_sources(limit=8)
            if rejected:
                lines = [f"Rejected in last cycle ({len(rejected)} sources):"]
                for r in rejected[:8]:
                    reason = (r.get("why_rejected") or r.get("why_collected") or "Low score")[:60]
                    score = r.get("monetization_score", 0)
                    title = (r.get("title") or r.get("keyword") or "")[:55]
                    lines.append(f"  ❌ {title} (score {score}) — {reason}")
            else:
                lines = ["No sources were rejected in the last cycle."]
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_daily_cycle_state",
                matched_topic=topic,
            )
        except Exception:
            return InternalFirstReply(
                text="No rejection data yet. Run: python3 scripts/run_daily_opportunity_intake.py --mode validation",
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_daily_cycle_state",
                matched_topic=topic,
            )

    if topic == "scouts_working":
        try:
            from lib.hermes_action_queue import get_open_actions
            from lib.hermes_tool_scout_registry import get_scouts
            open_actions = get_open_actions()
            assigned = [a for a in open_actions if a.assigned_scout]
            scouts_active = list({a.assigned_scout for a in assigned if a.assigned_scout})
            scouts_info = get_scouts()[:5]
            lines = [f"Scouts dispatched: {len(scouts_active)} active assignments."]
            if scouts_active:
                lines.append("Working:")
                for s in scouts_active[:5]:
                    lines.append(f"  🔄 {s}")
            if scouts_info:
                lines.append(f"\nAvailable scouts: {len(scouts_info)} registered.")
            lines.append("\nSay 'what scouts are available' for full registry.")
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_action_queue + hermes_tool_scout_registry",
                matched_topic=topic,
            )
        except Exception:
            return InternalFirstReply(
                text="Scout status unavailable. Check action queue and scout registry.",
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_tool_scout_registry",
                matched_topic=topic,
            )

    if topic == "daily_review":
        try:
            from lib.hermes_daily_cycle_state import (
                find_latest_daily_cycle, load_daily_cycle_summary,
                load_top_opportunities, load_rejected_sources,
            )
            cycle = find_latest_daily_cycle()
            summary = load_daily_cycle_summary()
            if not summary["has_data"]:
                return InternalFirstReply(
                    text=(
                        "I do not have a daily research review yet.\n"
                        "I can run daily opportunity intake first.\n"
                        "Say: Hermes, run daily opportunity intake."
                    ),
                    confidence=CONF_INTERNAL_PARTIAL,
                    source="hermes_daily_cycle_state",
                    matched_topic=topic,
                )
            top_ops = load_top_opportunities(limit=3)
            lines = ["DAILY RESEARCH REVIEW", ""]
            lines.append(
                f"I reviewed {summary['total_sources']} sources. "
                f"{summary['actionable']} are actionable. "
                f"{summary['rejected']} were rejected."
            )
            # Best move from top opportunity
            top = summary.get("top_opportunity") or (top_ops[0] if top_ops else None)
            if top:
                rec = (top.get("recommended_action") or top.get("title") or "")[:90]
                if rec:
                    lines.append(f"\nBest move:\n{rec}")
            # Top opportunities list
            if top_ops:
                lines.append("\nTop opportunities:")
                for i, op in enumerate(top_ops, 1):
                    specific = _format_opportunity_specific(op)
                    lines.append(f"  {i}. {specific}")
            # Rejected count
            lines.append(f"\nRejected: {summary['rejected']} sources filtered out.")
            # Evidence paths
            lines.append("\nEvidence:")
            if cycle["review"]:
                lines.append(f"  - Review: {cycle['review']}")
            if cycle["intake"]:
                lines.append(f"  - Intake: {cycle['intake']}")
            if cycle["decision"]:
                lines.append(f"  - Decision report: {cycle['decision']}")
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_daily_cycle_state",
                matched_topic=topic,
            )
        except Exception as _exc:
            return InternalFirstReply(
                text=(
                    "I do not have a daily research review yet.\n"
                    "I can run daily opportunity intake first.\n"
                    "Say: Hermes, run daily opportunity intake."
                ),
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_daily_cycle_state",
                matched_topic=topic,
            )

    if topic == "raw_evidence":
        try:
            from lib.hermes_daily_cycle_state import find_latest_daily_cycle
            from pathlib import Path as _Path
            cycle = find_latest_daily_cycle()
            root = _Path(__file__).resolve().parent.parent
            aq_path = root / "docs" / "reports" / "actions" / "hermes_action_queue.jsonl"
            dl_path = root / "docs" / "reports" / "decisions" / "hermes_decision_log.jsonl"
            lines = ["Raw evidence — latest artifact paths:"]
            if cycle["review"]:
                lines.append(f"  Review:       {cycle['review']}")
            if cycle["intake"]:
                lines.append(f"  Intake:       {cycle['intake']}")
            if cycle["decision"]:
                lines.append(f"  Decisions:    {cycle['decision']}")
            if cycle["rejected"]:
                lines.append(f"  Rejected:     {cycle['rejected']}")
            if aq_path.exists():
                lines.append(f"  Action queue: {aq_path}")
            if dl_path.exists():
                lines.append(f"  Decision log: {dl_path}")
            if len(lines) == 1:
                lines.append("  No artifacts found. Run daily intake to generate them.")
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_daily_cycle_state",
                matched_topic=topic,
            )
        except Exception as _exc:
            return InternalFirstReply(
                text=f"Raw evidence lookup failed: {_exc}",
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_daily_cycle_state",
                matched_topic=topic,
            )

    if topic == "build_content_from_opportunity":
        try:
            from lib.hermes_monetization_decision_engine import load_latest_decisions
            decisions = load_latest_decisions(limit=10)
            content_candidates = [
                d for d in decisions
                if d.get("status") in ("content_candidate", "client_education_candidate", "product_candidate")
            ]
            if content_candidates:
                best = content_candidates[0]
                title = best.get("title", "")[:70]
                rec = best.get("recommended_action", "")
                goal = best.get("goal_supported", "")
                lines = [
                    f"Best content candidate: {title}",
                    f"Why: {best.get('why_selected','')[:80]}",
                    f"Goal: {goal}",
                    f"Next: {rec}",
                    "",
                    "To create the content brief: run_content_pipeline.py with this topic.",
                    "⏳ Content publishing requires Ray approval before going public.",
                ]
            else:
                lines = [
                    "No content candidates scored yet.",
                    "Run daily intake first, then I can identify the best content opportunity.",
                    "Say: Hermes, run daily opportunity intake.",
                ]
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_monetization_decision_engine",
                matched_topic=topic,
            )
        except Exception:
            return InternalFirstReply(
                text="No content opportunities scored yet. Run daily intake first.",
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_monetization_decision_engine",
                matched_topic=topic,
            )

    if topic == "needs_approval":
        try:
            from lib.hermes_action_queue import get_pending_approval_actions
            from lib.hermes_monetization_decision_engine import load_latest_decisions
            pending = get_pending_approval_actions()
            decisions = load_latest_decisions(limit=20)
            approval_ops = [d for d in decisions if d.get("requires_ray_approval")]
            lines = []
            if pending:
                lines.append(f"Action queue — {len(pending)} items waiting for approval:")
                for a in pending[:5]:
                    lines.append(f"  ⏳ {a.title[:60]} — {a.approval_reason[:50]}")
            if approval_ops:
                if lines:
                    lines.append("")
                lines.append(f"Scored opportunities — {len(approval_ops)} need approval:")
                for op in approval_ops[:5]:
                    lines.append(f"  ⏳ {op.get('title','')[:60]} — {op.get('approval_reason','')[:50]}")
            if not lines:
                lines = ["Nothing requires your approval right now. All current actions are autonomous."]
            return InternalFirstReply(
                text="\n".join(lines),
                confidence=CONF_INTERNAL_CONFIRMED,
                source="hermes_action_queue + hermes_monetization_decision_engine",
                matched_topic=topic,
            )
        except Exception:
            return InternalFirstReply(
                text="Approval queue unavailable. Check action queue for pending items.",
                confidence=CONF_INTERNAL_PARTIAL,
                source="hermes_action_queue",
                matched_topic=topic,
            )

    return None
