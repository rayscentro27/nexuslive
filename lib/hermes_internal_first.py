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


def try_internal_first(raw: str) -> InternalFirstReply | None:
    text = (raw or "").strip().lower()
    if not text:
        return None
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
        # Read live status of known provider routes
        openrouter_key = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
        openrouter_model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
        hermes_url = os.getenv("HERMES_GATEWAY_URL", "http://127.0.0.1:8642")
        ollama_primary = os.getenv("HERMES_REASONING_MODEL", "qwen3:8b")
        oracle_host = "161.153.40.41"
        lines = [
            "Internally, these are the known Nexus provider routes:",
            f"• OpenRouter API ({openrouter_model}): {'configured ✓' if openrouter_key else 'key missing ✗'} — used for Telegram conversational replies",
            f"• Hermes local Ollama ({ollama_primary}): {hermes_url} — tunnel required, currently unreachable if tunnel is down",
            f"• Oracle VM Ollama (qwen2.5:14b): {oracle_host} — frequently unreachable (100% packet loss when down)",
            "• Claude Code CLI: available locally for coding tasks",
            "• OpenClaw: ChatGPT session routing — active when OPENCLAW_ENABLED=true",
            "",
            "Best current fallback: OpenRouter (deepseek-chat) for conversation, Claude Code CLI for code tasks.",
            "To check live Ollama status, run /models or ask 'worker status'.",
        ]
        return InternalFirstReply(
            text="\n".join(lines),
            confidence=CONF_INTERNAL_CONFIRMED,
            source="env_config + known_topology",
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

    return None
