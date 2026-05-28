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
    """Build a short operational context for greeting responses using executive memory."""
    try:
        exec_mem = _exec_mem.load_memory()
        priorities = exec_mem.get("execution_priorities", [])[:2]
        problems = exec_mem.get("infrastructure_problems", [])[:1]
        parts = []
        if priorities:
            parts.append("Priorities: " + " | ".join(str(p) for p in priorities))
        if problems:
            parts.append("Issues: " + str(problems[0]))
        if parts:
            return " ".join(parts) + "."
    except Exception:
        pass
    # Fallback to ops memory
    try:
        mem = hermes_ops_memory.load_memory(updated_by="greeting_context")
        active = (mem.get("active_priorities") or [])[:2]
        if active:
            return f"Active: {', '.join(str(x) for x in active)}."
    except Exception:
        pass
    return ""


def try_internal_first(raw: str) -> InternalFirstReply | None:
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
                "completion_acknowledgement", "blocker_triage",
            }
            if intent in conversational_intents:
                ctx: dict[str, str] = {}
                if intent in {"morning_greeting", "status_check_personal"}:
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

    # ── Phase 1.5: Opportunity Intelligence ──────────────────────────────────
    # Intercept URLs, business ideas, SaaS tools, affiliate programs, niche ideas
    # before keyword routing so they receive full scored analysis, not a stub reply.
    try:
        from lib.opportunity_analyzer import is_opportunity_input, score_opportunity, generate_opportunity_report
        if is_opportunity_input(raw):
            scored = score_opportunity(raw)
            score = scored.get("score", 0)
            category = scored.get("category", "Unknown")
            full_report = generate_opportunity_report(raw)
            # Truncate to ~3800 chars to stay within Telegram/response limits
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
    rules = _parse_json_env("HERMES_INTERNAL_FIRST_KEYWORDS", _default_rules())
    topic = ""
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
        pending_note = f" ({len(pending)} pending approval{'s' if len(pending) != 1 else ''} to clear first)" if pending else ""
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

    return None
