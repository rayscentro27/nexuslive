#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

from audit_hermes_common import (
    AUDIT_DIR,
    ROOT,
    ensure_audit_dir,
    extract_paths_and_tables,
    find_mock_stale_occurrences,
    first_header,
    line_number,
    latest_matching,
    now_timestamp,
    rel,
    safe_bot,
    trace_route,
    write_json,
    write_md,
)


def _layer_status() -> dict[str, str]:
    from lib.hermes_cfo_loop_shadow import get_cfo_loop_mode
    from lib.hermes_memory_v2_shadow import get_memory_v2_mode, is_primary_mode_active

    cfo_mode = get_cfo_loop_mode()
    memory_mode = get_memory_v2_mode()
    return {
        "cfo_mode": cfo_mode,
        "memory_mode": memory_mode,
        "memory_primary_active": "active" if is_primary_mode_active() else memory_mode,
    }


def build_layers() -> list[dict]:
    status = _layer_status()
    layers = [
        {
            "layer": "Telegram bot entrypoint",
            "file_path": "telegram_bot.py",
            "purpose": "Primary inbound Telegram handler and top-level routing orchestration.",
            "state": "active",
            "pattern": "def handle_inbound_message",
        },
        {
            "layer": "telegram_bot.py routing order",
            "file_path": "telegram_bot.py",
            "purpose": "Pre-router order for memory commands, CFO phases, continuity, TelegramRouter, and shadow logging.",
            "state": "active",
            "pattern": "def handle_inbound_message",
        },
        {
            "layer": "Command intake",
            "file_path": "hermes_command_router/intake.py",
            "purpose": "Deterministic phrase-to-intent normalization and approval flags.",
            "state": "active",
            "pattern": "def classify_intent",
        },
        {
            "layer": "Command router",
            "file_path": "hermes_command_router/router.py",
            "purpose": "Maps normalized intents to plain handlers, reports, or model-backed fallback.",
            "state": "active",
            "pattern": "def run_command",
        },
        {
            "layer": "Phase 6 daily operating cycle",
            "file_path": "lib/hermes_daily_operating_cycle.py",
            "purpose": "Builds today's internal plan, top revenue move, blockers, and approval summaries.",
            "state": "active",
            "pattern": "def build_daily_operating_plan",
        },
        {
            "layer": "Daily cycle state",
            "file_path": "lib/hermes_daily_cycle_state.py",
            "purpose": "Stores latest daily cycle state, history, pending items, and plan comparisons.",
            "state": "active",
            "pattern": "State file:",
        },
        {
            "layer": "Approval queue",
            "file_path": "lib/hermes_approval_queue.py",
            "purpose": "Normalizes local approval items and supports local approve/reject/safety impact workflows.",
            "state": "active",
            "pattern": "Phase 6C",
        },
        {
            "layer": "Revenue asset packet",
            "file_path": "lib/hermes_revenue_asset_packet.py",
            "purpose": "Builds and scores revenue packet assets and approval candidates.",
            "state": "active",
            "pattern": "revenue",
        },
        {
            "layer": "Funnel packet / launch packet",
            "file_path": "docs/reports/funnel/",
            "purpose": "Internal report artifacts for launch/funnel approval packets; not a live routing module.",
            "state": "legacy",
            "pattern": "",
        },
        {
            "layer": "Learning loop",
            "file_path": "lib/hermes_learning_loop.py",
            "purpose": "Captures lesson proposals locally and, after explicit approval, can write to hermes_memory_v2.",
            "state": "active",
            "pattern": "Phase 5",
        },
        {
            "layer": "Memory v2 reader",
            "file_path": "lib/hermes_memory_v2_reader.py",
            "purpose": "Preview-only structured memory reader for active/live_answer rows.",
            "state": "preview",
            "pattern": "Preview-only reader",
        },
        {
            "layer": "Memory v2 primary mode",
            "file_path": "lib/hermes_memory_v2_shadow.py",
            "purpose": "Mode gates preview/shadow/primary behavior for memory v2 with strong approval guards.",
            "state": status["memory_primary_active"],
            "pattern": "Phase 4E/4F",
        },
        {
            "layer": "CFO brain Phase 7",
            "file_path": "lib/hermes_cfo_brain.py",
            "purpose": "Handles follow-up reasoning, option selection, explain/simplify, failure feedback, and selected strategy responses.",
            "state": "active",
            "pattern": "def classify_cfo_intent",
        },
        {
            "layer": "Conversation state manager",
            "file_path": "lib/hermes_conversation_state.py",
            "purpose": "Persists last options, selected option, recommendation, artifact path, and meaningful response context.",
            "state": "active",
            "pattern": "def update_conversation_state",
        },
        {
            "layer": "Plain-language rewriter",
            "file_path": "lib/hermes_plain_language_rewriter.py",
            "purpose": "Rewrites or compresses complex outputs into operator-friendly plain language.",
            "state": "active",
            "pattern": "def rewrite",
        },
        {
            "layer": "Failure learning",
            "file_path": "lib/hermes_failure_learning.py",
            "purpose": "Logs bad responses and generates learn/test artifacts from failures.",
            "state": "active",
            "pattern": "failed",
        },
        {
            "layer": "Custom GPT trainer package",
            "file_path": "docs/hermes/custom_gpt_trainer/",
            "purpose": "Documentation/training package for response rewrite, failure review, and alignment prompts.",
            "state": "legacy",
            "pattern": "",
        },
        {
            "layer": "Phase 8A CFO prototype",
            "file_path": "prototypes/hermes_agentic_cfo_loop.py",
            "purpose": "Prototype agentic CFO loop with intent/retrieval/reasoning/tool/plain-language stages.",
            "state": "prototype-only",
            "pattern": "class HermesCFOLoop",
        },
        {
            "layer": "Phase 8B shadow mode",
            "file_path": "lib/hermes_cfo_loop_shadow.py",
            "purpose": "Runs CFO loop in background and logs traces without changing live response.",
            "state": "shadow" if status["cfo_mode"] == "shadow" else "inactive",
            "pattern": "Phase 8B/8C",
        },
        {
            "layer": "Phase 8C limited primary mode",
            "file_path": "lib/hermes_cfo_loop_shadow.py",
            "purpose": "Allows grounded, allowlisted CFO responses to become live Telegram answers.",
            "state": "limited_primary" if status["cfo_mode"] == "limited_primary" else "inactive",
            "pattern": "LIMITED_PRIMARY_CONFIDENCE_THRESHOLD",
        },
        {
            "layer": "Phase 8C.1 grounded limited primary guard",
            "file_path": "lib/hermes_cfo_loop_shadow.py",
            "purpose": "Blocks mock/sample output and requires grounded evidence paths before primary use.",
            "state": "active",
            "pattern": "_MOCK_BLOCK_MARKERS",
        },
        {
            "layer": "Scout assignments",
            "file_path": "lib/hermes_scout_dispatcher.py",
            "purpose": "Creates scout dispatch handoffs and logs scout dispatch artifacts.",
            "state": "active",
            "pattern": "Scout Dispatch Handoff",
        },
        {
            "layer": "Research queue",
            "file_path": "hermes_command_router/router.py",
            "purpose": "Read-only queue review, dedupe, assignment visibility, and unresolved question surfacing.",
            "state": "active",
            "pattern": "show_research_queue",
        },
        {
            "layer": "Action queue",
            "file_path": "lib/hermes_action_queue.py",
            "purpose": "Append-only local action tracker for opportunities, approvals, scouts, and artifacts.",
            "state": "active",
            "pattern": "Hermes action tracker",
        },
        {
            "layer": "Decision log",
            "file_path": "lib/hermes_decision_log.py",
            "purpose": "Stores decision artifacts and feeds approval queue / recent decision views.",
            "state": "active",
            "pattern": "decision",
        },
        {
            "layer": "Evidence/artifact fallback",
            "file_path": "lib/hermes_internal_first.py",
            "purpose": "Builds internal evidence-based fallback answers from local artifacts and handoffs.",
            "state": "active",
            "pattern": "verified artifacts",
        },
        {
            "layer": "Old HERMES REPORT wrapper",
            "file_path": "hermes_command_router/report.py",
            "purpose": "Wraps non-plain router outputs into HERMES REPORT structure.",
            "state": "legacy",
            "pattern": "def build",
        },
        {
            "layer": "Quality fallback",
            "file_path": "lib/hermes_response_quality.py",
            "purpose": "Last-resort fallback text when response quality checks fail.",
            "state": "active",
            "pattern": "quality response",
        },
        {
            "layer": "Provider/gateway layer",
            "file_path": "lib/hermes_model_router.py",
            "purpose": "Chooses/synthesizes provider-backed model calls for non-plain command router paths.",
            "state": "active",
            "pattern": "synthesize",
        },
        {
            "layer": "TelegramRouter / LLM fallback",
            "file_path": "lib/telegram_router.py",
            "purpose": "Secondary Telegram routing for approvals, strategic regexes, commands, report requests, and generic conversational fallback.",
            "state": "active",
            "pattern": "def route_incoming_message",
        },
    ]

    for layer in layers:
        path = ROOT / layer["file_path"] if not layer["file_path"].startswith("docs/") else ROOT / layer["file_path"]
        info = extract_paths_and_tables(path) if path.is_file() else {"file_paths": [], "tables": [], "network_tokens": [], "write_tokens": []}
        layer["line_number"] = line_number(path, layer["pattern"]) if path.is_file() and layer["pattern"] else None
        layer["read_sources"] = info["file_paths"] + info["tables"]
        layer["write_targets"] = info["file_paths"] if info["write_tokens"] else []
        layer["safety_boundary"] = _safety_boundary(layer["layer"])
        layer["known_risks"] = _known_risks(layer["layer"])
        layer["can_affect_live_telegram_response"] = layer["layer"] not in {
            "Funnel packet / launch packet",
            "Custom GPT trainer package",
            "Scout assignments",
        }
        layer["uses_mock_data"] = layer["layer"] in {"Phase 8A CFO prototype", "Phase 8B shadow mode"} or "prototype" in layer["state"]
        layer["can_call_network_or_model_providers"] = bool(info["network_tokens"]) or layer["layer"] in {
            "Provider/gateway layer",
            "TelegramRouter / LLM fallback",
            "Command router",
        }
        layer["can_write_supabase"] = layer["layer"] in {"Learning loop"}
    return layers


def _safety_boundary(name: str) -> str:
    boundaries = {
        "Learning loop": "Pending proposals local only; approved lesson writes require Ray approval and target hermes_memory_v2 only.",
        "Approval queue": "Approve authorizes next step only; no publish/email/spend/deploy/trade execution.",
        "Phase 8C limited primary mode": "Allowlisted intents only; hard blocked/risky intents never become primary.",
        "Phase 8C.1 grounded limited primary guard": "Blocks mock/sample output and ungrounded primary answers.",
        "Memory v2 primary mode": "Primary mode requires explicit approval file and guard checks.",
        "TelegramRouter / LLM fallback": "Can still fall through to conversational/model layer when earlier layers do not intercept.",
    }
    return boundaries.get(name, "Internal-only boundary expected; no autonomous publish/email/payment/deploy/live-trade path allowed.")


def _known_risks(name: str) -> list[str]:
    risks = {
        "Telegram bot entrypoint": ["Routing collisions from multiple legacy layers.", "Memory pre-check can preempt newer layers."],
        "Command router": ["Non-plain intents can still use HERMES REPORT wrapper.", "Some handlers can touch network-backed providers."],
        "Memory v2 reader": ["Supabase credential dependence.", "Preview-only can diverge from live truth."],
        "Memory v2 primary mode": ["Guarded primary may be requested but not actually active.", "Shadow/preview drift can confuse operators."],
        "Phase 8A CFO prototype": ["Prototype mock markers exist in codebase.", "Not safe as full live primary without guards."],
        "Phase 8B shadow mode": ["Trace volume can obscure latest state.", "Prototype output still exists in shadow path."],
        "Phase 8C limited primary mode": ["Allowlisted intents only; anything outside falls to legacy routing.", "Grounding depends on local state quality."],
        "Evidence/artifact fallback": ["Can produce artifact dumps instead of operator answer.", "May surface stale handoff-heavy summaries."],
        "Quality fallback": ["Generic low-signal answer if upstream path fails."],
        "TelegramRouter / LLM fallback": ["Can trigger evidence dumps or model fallback if higher-order layers miss."],
        "Learning loop": ["Approved lessons can write Supabase.", "Proposal file may accumulate stale items."],
    }
    return risks.get(name, [])


def build_routing_audit() -> tuple[list[dict], list[dict]]:
    steps = [
        {
            "step": 1,
            "name": "Memory command pre-check",
            "function_name": "NexusTelegramBot._try_memory_command",
            "file_path": "telegram_bot.py",
            "line_number": line_number(ROOT / "telegram_bot.py", "def _try_memory_command"),
            "message_types": ["memory commands", "approval queue read commands", "daily plan read commands", "learning loop commands"],
            "can_override_later_layers": True,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "before",
        },
        {
            "step": 2,
            "name": "Inbound normalization",
            "function_name": "_normalize_telegram_command",
            "file_path": "telegram_bot.py",
            "line_number": line_number(ROOT / "telegram_bot.py", "def _normalize_telegram_command"),
            "message_types": ["all text"],
            "can_override_later_layers": False,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "before",
        },
        {
            "step": 3,
            "name": "CFO shadow command exact handler",
            "function_name": "handle_cfo_shadow_command",
            "file_path": "lib/hermes_cfo_loop_shadow.py",
            "line_number": line_number(ROOT / "lib/hermes_cfo_loop_shadow.py", "def handle_cfo_shadow_command"),
            "message_types": ["show cfo shadow status", "show cfo limited primary status", "rollback cfo loop to shadow"],
            "can_override_later_layers": True,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "before",
        },
        {
            "step": 4,
            "name": "Phase 8C limited primary intercept",
            "function_name": "run_cfo_limited_primary",
            "file_path": "lib/hermes_cfo_loop_shadow.py",
            "line_number": line_number(ROOT / "telegram_bot.py", "run_cfo_limited_primary"),
            "message_types": ["allowlisted grounded CFO intents"],
            "can_override_later_layers": True,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "self",
        },
        {
            "step": 5,
            "name": "Phase 7C forced intents",
            "function_name": "process_with_cfo_brain",
            "file_path": "telegram_bot.py",
            "line_number": line_number(ROOT / "telegram_bot.py", "_PHASE7C_FORCED_INTENTS"),
            "message_types": ["option selection", "task reference", "simplify/explain", "morning activity", "failure feedback"],
            "can_override_later_layers": True,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "after",
        },
        {
            "step": 6,
            "name": "Continuity exact command map",
            "function_name": "continuity[...] -> _dispatch_continuity",
            "file_path": "telegram_bot.py",
            "line_number": line_number(ROOT / "telegram_bot.py", "continuity = {"),
            "message_types": ["exact Telegram-only phrases and follow-ups"],
            "can_override_later_layers": True,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "after",
        },
        {
            "step": 7,
            "name": "CFO conversation intercept",
            "function_name": "build_cfo_response",
            "file_path": "telegram_bot.py",
            "line_number": line_number(ROOT / "telegram_bot.py", "detect_cfo_conversation_need"),
            "message_types": ["high-priority strategic conversation"],
            "can_override_later_layers": True,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "after",
        },
        {
            "step": 8,
            "name": "CFO brain general intercept",
            "function_name": "process_with_cfo_brain",
            "file_path": "telegram_bot.py",
            "line_number": line_number(ROOT / "telegram_bot.py", "should_use_cfo_brain"),
            "message_types": ["general CFO natural-language reasoning"],
            "can_override_later_layers": True,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "after",
        },
        {
            "step": 9,
            "name": "TelegramRouter",
            "function_name": "TelegramRouter.route_incoming_message",
            "file_path": "lib/telegram_router.py",
            "line_number": line_number(ROOT / "lib/telegram_router.py", "def route_incoming_message"),
            "message_types": ["approval replies", "risky action requests", "strategic regex routes", "command mode", "report requests", "daily plan", "generic chat"],
            "can_override_later_layers": True,
            "can_cause_evidence_dump": True,
            "can_cause_quality_fallback": True,
            "phase8c_position": "after",
        },
        {
            "step": 10,
            "name": "Command router",
            "function_name": "run_command",
            "file_path": "hermes_command_router/router.py",
            "line_number": line_number(ROOT / "hermes_command_router/router.py", "def run_command"),
            "message_types": ["normalized command intents"],
            "can_override_later_layers": True,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "after",
        },
        {
            "step": 11,
            "name": "Evidence/artifact fallback",
            "function_name": "try_internal_first / evidence-only chat fallback",
            "file_path": "lib/hermes_internal_first.py",
            "line_number": line_number(ROOT / "lib/hermes_internal_first.py", "source intake records"),
            "message_types": ["generic strategy/fallback questions"],
            "can_override_later_layers": False,
            "can_cause_evidence_dump": True,
            "can_cause_quality_fallback": False,
            "phase8c_position": "after",
        },
        {
            "step": 12,
            "name": "Quality fallback",
            "function_name": "hermes_response_quality fallback",
            "file_path": "lib/hermes_response_quality.py",
            "line_number": line_number(ROOT / "lib/hermes_response_quality.py", "I wasn't able to generate a quality response"),
            "message_types": ["failed/gated responses"],
            "can_override_later_layers": False,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": True,
            "phase8c_position": "after",
        },
        {
            "step": 13,
            "name": "Send response",
            "function_name": "handle_inbound_message return",
            "file_path": "telegram_bot.py",
            "line_number": line_number(ROOT / "telegram_bot.py", "return response"),
            "message_types": ["all finalized answers"],
            "can_override_later_layers": False,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "after",
        },
        {
            "step": 14,
            "name": "Shadow trace / memory shadow logging",
            "function_name": "trigger_shadow_comparison_async / run_cfo_shadow_async",
            "file_path": "telegram_bot.py",
            "line_number": line_number(ROOT / "telegram_bot.py", "trigger_shadow_comparison_async"),
            "message_types": ["all messages when shadow modes are enabled"],
            "can_override_later_layers": False,
            "can_cause_evidence_dump": False,
            "can_cause_quality_fallback": False,
            "phase8c_position": "after",
        },
    ]
    collisions = [
        {
            "collision": "what changed in the draft vs daily plan comparison",
            "where": "Memory command pre-check vs Phase 8C draft comparison",
            "current_status": "Phase 8C now wins in limited_primary because _try_memory_command explicitly yields to allowlisted Phase 8C intents.",
        },
        {
            "collision": "approve all approvals vs lesson bulk approval",
            "where": "Approval queue bulk approval vs learning-loop lesson bulk approval phrases",
            "current_status": "Potential overlap remains because 'approve all' style phrases exist in multiple approval systems; current mitigation relies on exact intent patterns.",
        },
        {
            "collision": "implementation prompt now vs evidence fallback",
            "where": "Phase 8C implementation_prompt_request vs generic evidence/chat fallback",
            "current_status": "Grounded limited_primary now handles the phrase in limited_primary mode; legacy fallback still exists when Phase 8C is off.",
        },
        {
            "collision": "scout status vs source intake dump",
            "where": "Phase 8C scout_status vs evidence/artifact fallback",
            "current_status": "Grounded limited_primary now wins in limited_primary mode; outside that mode, generic evidence fallback can still dump intake-heavy responses.",
        },
        {
            "collision": "approval safety vs approval queue",
            "where": "Phase 8C approval_bulk_request vs Phase 6C approval queue exact commands",
            "current_status": "Different phrases hit different paths; conversational 'i approve them all' resolves to Phase 8C in limited_primary.",
        },
        {
            "collision": "summary of day vs generic strategy",
            "where": "Phase 8C summary_of_day vs internal evidence fallback",
            "current_status": "Limited_primary path is grounded; without it, strategy/evidence fallback remains possible.",
        },
        {
            "collision": "launch packet review vs generic strategy",
            "where": "No dedicated Phase 8 intercept; likely falls to generic strategy or evidence fallback.",
            "current_status": "Unresolved overlap; should stay in audit recommendations.",
        },
        {
            "collision": "clarifying question vs evidence fallback",
            "where": "Phase 8C clarifying_question_request vs generic fallback",
            "current_status": "Resolved in limited_primary; older fallback still exists when Phase 8C is not active.",
        },
    ]
    return steps, collisions


def build_data_source_audit(layers: list[dict]) -> list[dict]:
    tracked = [
        "docs/reports/strategy/hermes_conversation_state.json",
        "docs/reports/operations/hermes_daily_cycle_state.json",
        "docs/reports/actions/hermes_action_queue.jsonl",
        "docs/reports/approvals/hermes_approval_queue_state.json",
        "docs/reports/research_queue/hermes_research_queue.jsonl",
        "docs/reports/research_queue/hermes_scout_assignments.jsonl",
        "docs/reports/decisions/hermes_decision_log.jsonl",
        "docs/reports/content/",
        "docs/reports/funnel/",
        "docs/reports/scouts/",
        "docs/reports/strategy/shadow/hermes_cfo_loop_shadow_traces.jsonl",
        "docs/reports/training/hermes_failed_response_examples.jsonl",
        "docs/reports/training/hermes_response_training_set.jsonl",
        "docs/hermes/",
        "docs/hermes/custom_gpt_trainer/",
        "hermes_memory_v2",
    ]
    layer_by_path: dict[str, dict[str, list[str]]] = {}
    for layer in layers:
        for src in layer["read_sources"]:
            layer_by_path.setdefault(src, {"read_by": [], "written_by": []})
            layer_by_path[src]["read_by"].append(layer["layer"])
        for dst in layer["write_targets"]:
            layer_by_path.setdefault(dst, {"read_by": [], "written_by": []})
            layer_by_path[dst]["written_by"].append(layer["layer"])
    results = []
    for item in tracked:
        usage = layer_by_path.get(item, {"read_by": [], "written_by": []})
        results.append({
            "source": item,
            "read_by_modules": sorted(set(usage["read_by"])),
            "written_by_modules": sorted(set(usage["written_by"])),
            "safe_or_unsafe": "unsafe" if item == "hermes_memory_v2" else "safe",
            "contains_secrets": "no",
            "contains_private_client_data": "unknown",
            "stale_risk": "high" if item in {"docs/reports/content/", "docs/reports/funnel/", "docs/reports/scouts/"} else "medium",
            "duplicate_risk": "high" if "reports/" in item and item.endswith("/") else "medium",
            "source_of_truth_status": "active" if usage["read_by"] or usage["written_by"] else "legacy/reference only",
        })
    extra_tables = [
        {
            "source": "old memory / task / agent / approval tables",
            "read_by_modules": [],
            "written_by_modules": [],
            "safe_or_unsafe": "unsafe",
            "contains_secrets": "no",
            "contains_private_client_data": "unknown",
            "stale_risk": "high",
            "duplicate_risk": "high",
            "source_of_truth_status": "legacy/reference only",
        }
    ]
    return results + extra_tables


def build_safety_audit() -> list[dict]:
    return [
        {
            "command_or_intent": "publish / client-facing content",
            "function": "_risky_action_requested / approval gating / approval queue category filters",
            "file": "telegram_bot.py / lib/hermes_approval_queue.py",
            "current_behavior": "Requires approval or stays internal only.",
            "approval_required": True,
            "approval_boundary_shown": True,
            "blocked_correctly": True,
            "risk_level": "high",
            "recommendation": "Keep blocked; do not let conversational fallbacks imply publication.",
        },
        {
            "command_or_intent": "subscriber email",
            "function": "TelegramRouter report/knowledge email paths; approval queue high-risk categories",
            "file": "lib/telegram_router.py / lib/hermes_approval_queue.py",
            "current_behavior": "Email-capable path still exists in router; approval queue treats subscriber email as high risk.",
            "approval_required": True,
            "approval_boundary_shown": True,
            "blocked_correctly": False,
            "risk_level": "high",
            "recommendation": "Audit/disable live email-send paths before future feature work.",
        },
        {
            "command_or_intent": "affiliate application / link activation",
            "function": "Approval queue high-risk categories and CFO hard-blocked intents",
            "file": "lib/hermes_approval_queue.py / lib/hermes_cfo_loop_shadow.py",
            "current_behavior": "Primary responses blocked; explicit activation should require approval.",
            "approval_required": True,
            "approval_boundary_shown": True,
            "blocked_correctly": True,
            "risk_level": "high",
            "recommendation": "Keep only placeholder/internal references.",
        },
        {
            "command_or_intent": "Stripe/payment activation",
            "function": "Approval queue high-risk categories and CFO hard-blocked intents",
            "file": "lib/hermes_approval_queue.py / lib/hermes_cfo_loop_shadow.py",
            "current_behavior": "Blocked from safe approval bulk flows and primary mode.",
            "approval_required": True,
            "approval_boundary_shown": True,
            "blocked_correctly": True,
            "risk_level": "high",
            "recommendation": "Keep separate from internal drafts and research.",
        },
        {
            "command_or_intent": "deploy production",
            "function": "Risky action approval gate and approval queue categories",
            "file": "telegram_bot.py / lib/hermes_approval_queue.py",
            "current_behavior": "Should require approval and not execute automatically from Hermes flows.",
            "approval_required": True,
            "approval_boundary_shown": True,
            "blocked_correctly": True,
            "risk_level": "high",
            "recommendation": "Keep deployment outside Hermes conversational surface.",
        },
        {
            "command_or_intent": "spend money",
            "function": "Approval queue and CFO hard-blocked intents",
            "file": "lib/hermes_approval_queue.py / lib/hermes_cfo_loop_shadow.py",
            "current_behavior": "Blocked from primary mode and high-risk approval categories.",
            "approval_required": True,
            "approval_boundary_shown": True,
            "blocked_correctly": True,
            "risk_level": "high",
            "recommendation": "No autonomous spend path should remain in generic router.",
        },
        {
            "command_or_intent": "live trading",
            "function": "Evidence gate plus approval/risk boundaries",
            "file": "lib/telegram_router.py / hermes_command_router/router.py / lib/hermes_approval_queue.py",
            "current_behavior": "Fake trading claims blocked; live trading remains explicit high risk.",
            "approval_required": True,
            "approval_boundary_shown": True,
            "blocked_correctly": True,
            "risk_level": "high",
            "recommendation": "Keep paper/demo separated from live trading policy.",
        },
        {
            "command_or_intent": "Supabase writes",
            "function": "Learning loop lesson approval; selected migration/backfill scripts outside live Telegram",
            "file": "lib/hermes_learning_loop.py",
            "current_behavior": "Possible only on approved lesson paths; audit scripts must not trigger.",
            "approval_required": True,
            "approval_boundary_shown": True,
            "blocked_correctly": True,
            "risk_level": "high",
            "recommendation": "Treat hermes_memory_v2 writes as separate maintenance operations.",
        },
        {
            "command_or_intent": "external network/model calls",
            "function": "TelegramRouter conversational fallback, command router model router, provider checks",
            "file": "lib/telegram_router.py / hermes_command_router/router.py / lib/hermes_provider_policy.py",
            "current_behavior": "Still possible in non-plain/router/model-backed paths.",
            "approval_required": False,
            "approval_boundary_shown": False,
            "blocked_correctly": False,
            "risk_level": "medium",
            "recommendation": "Prefer local deterministic paths for audits and safety-sensitive commands.",
        },
    ]


def build_layer_test_results(timestamp: str) -> list[dict]:
    messages = [
        "show memory v2 primary status",
        "Hermes, run daily operating cycle",
        "show approval queue",
        "i approve them all",
        "what happens if I approve item 1",
        "what are all the scouts doing right now",
        "show research queue",
        "what did we work on today",
        "create the implementation prompt now",
        "implement it",
        "what changed in the draft",
        "ask me a better clarifying question",
        "Review the Funding Readiness Launch Packet and give me the approval decision summary.",
        "what is the current revenue packet score",
        "which asset is closest to launch ready",
        "show cfo limited primary status",
        "show cfo shadow traces",
        "rollback cfo loop to shadow",
    ]
    results = []
    for message in messages:
        route = trace_route(message, limited_primary=True)
        response = route.get("response", "")
        header = first_header(response)
        lower = (response or "").lower()
        results.append({
            "message": message,
            "handled_by_layer": route["handled_by_layer"],
            "intent": route["intent"],
            "handler": route["handler"],
            "mode": route["mode"],
            "output_header": header,
            "evidence_dump_appeared": "artifact_inventory" in lower or "i can answer from verified artifacts" in lower,
            "quality_fallback_appeared": "i wasn't able to generate a quality response" in lower,
            "mock_output_appeared": "based on mock data" in lower or "research_scout_1" in lower,
            "safety_flags": [flag for flag in ["approval boundary", "requires approval", "blocked", "internal only"] if flag in lower],
            "recommended_fix_if_failed": "" if header else "Add deterministic exact handler or grounded limited-primary intercept.",
        })
    json_path = AUDIT_DIR / f"hermes_layer_test_results_{timestamp}.json"
    md_path = AUDIT_DIR / f"hermes_layer_test_results_{timestamp}.md"
    write_json(json_path, {"timestamp": timestamp, "results": results, "supabase_write_attempted": False})
    lines = [f"# Hermes Layer Test Results\n", f"Timestamp: {timestamp}\n"]
    for item in results:
        lines += [
            f"## {item['message']}",
            f"- handled by layer: {item['handled_by_layer']}",
            f"- intent: {item['intent']}",
            f"- handler: {item['handler']}",
            f"- mode: {item['mode']}",
            f"- output header: {item['output_header'] or '(none)'}",
            f"- evidence dump appeared: {item['evidence_dump_appeared']}",
            f"- quality fallback appeared: {item['quality_fallback_appeared']}",
            f"- mock output appeared: {item['mock_output_appeared']}",
            f"- safety flags: {', '.join(item['safety_flags']) or 'none'}",
            f"- recommended fix if failed: {item['recommended_fix_if_failed'] or 'none'}",
            "",
        ]
    write_md(md_path, "\n".join(lines))
    return results


def build_summary(timestamp: str, layers: list[dict], routing_steps: list[dict], command_count: int = 0) -> tuple[dict, str]:
    active_layers = [l["layer"] for l in layers if l["state"] in {"active", "limited_primary", "preview"}]
    mock_hits = find_mock_stale_occurrences()
    safety = build_safety_audit()
    collisions = build_routing_audit()[1]
    by_category: dict[str, int] = {}
    inv_path = latest_matching("hermes_command_inventory_*.json")
    if inv_path:
        try:
            inv_doc = json.loads(inv_path.read_text(encoding="utf-8"))
            command_count = len(inv_doc.get("commands", []))
            for item in inv_doc.get("commands", []):
                cat = item.get("category", "unknown")
                by_category[cat] = by_category.get(cat, 0) + 1
        except Exception:
            pass
    summary = {
        "timestamp": timestamp,
        "executive_summary": "Hermes currently runs a stacked routing architecture: Telegram pre-checks, command-router plain intents, CFO conversation/brain layers, Phase 8 limited-primary grounding, and TelegramRouter/model fallback. Multiple older fallback paths still exist and can collide when newer intercepts are off.",
        "current_active_architecture": active_layers,
        "live_telegram_routing_order": [step["name"] for step in routing_steps],
        "command_inventory_count": command_count,
        "active_commands_by_category": by_category,
        "data_sources_read_written": "See companion data source audit.",
        "supabase_writes_possible": True,
        "local_writes_possible": True,
        "mock_stale_data_risks": len(mock_hits),
        "safety_approval_gaps": [s for s in safety if not s["blocked_correctly"]],
        "duplicate_overlapping_systems": [c["collision"] for c in collisions],
        "top_10_broken_or_risky_paths": [
            "Memory command pre-check can still preempt newer layers.",
            "Legacy TelegramRouter conversational fallback can still hit evidence/model paths.",
            "Old HERMES REPORT wrapper still exists for non-plain command-router intents.",
            "Learning loop is the active Supabase-write path.",
            "Email/report router paths still exist in TelegramRouter.",
            "Revenue/funnel artifacts are spread across report folders and modules.",
            "Shadow/preview/primary terminology differs between memory v2 and CFO loop.",
            "Evidence fallback can still surface stale artifact-heavy summaries.",
            "Approval concepts exist in approval queue, learning loop, and conversational approvals.",
            "Prototype CFO loop code still contains mock/stale markers even though primary guard blocks them.",
        ],
        "top_10_cleanup_recommendations": [
            "Unify all live Telegram routing into one documented precedence chain.",
            "Keep _try_memory_command narrow and explicit.",
            "Deprecate or isolate old HERMES REPORT wrapper paths.",
            "Add a single command registry as source of truth.",
            "Separate read-only audit-safe handlers from write-capable handlers.",
            "Move funnel/launch packet logic from artifact-only reports into explicit modules or mark it archival.",
            "Reduce generic evidence fallback for operator-facing questions.",
            "Consolidate approval semantics across approval queue and learning loop.",
            "Mark prototype/mock files more aggressively as non-live.",
            "Keep Phase 8C grounding tests as required regression gates.",
        ],
        "what_to_keep": ["Phase 8C.1 grounded limited primary guard", "Approval queue local-only normalization", "Daily cycle plain-text outputs", "Memory v2 guardrails"],
        "what_to_deprecate": ["Old HERMES REPORT wrapper for operator-facing status commands", "Artifact dump fallback for strategic summaries"],
        "what_to_fix_next": ["routing collisions", "command registry duplication", "email/router safety gaps"],
        "what_not_to_touch": ["Supabase tables", "secrets/env handling", "live trading gates"],
        "recommended_phase_8d_or_cleanup_plan": "Prefer a cleanup phase over new features: unify registry, collapse fallback layers, and reduce live-path ambiguity before Phase 8D expansion.",
    }
    lines = [
        "# Hermes Full System Audit Summary",
        "",
        f"Timestamp: {timestamp}",
        "",
        "## Executive Summary",
        summary["executive_summary"],
        "",
        "## Current Active Architecture",
        *[f"- {item}" for item in active_layers],
        "",
        "## Live Telegram Routing Order",
        *[f"{step['step']}. {step['name']}" for step in routing_steps],
        "",
        "## Command Inventory Count",
        str(command_count),
        "",
        "## Active Commands By Category",
        *[f"- {k}: {v}" for k, v in sorted(by_category.items())],
        "",
        "## Top 10 Broken or Risky Paths",
        *[f"- {item}" for item in summary["top_10_broken_or_risky_paths"]],
        "",
        "## Top 10 Cleanup Recommendations",
        *[f"- {item}" for item in summary["top_10_cleanup_recommendations"]],
        "",
        "## Main Answer",
        "Each Hermes layer currently either intercepts live Telegram input, builds internal plan/approval context, or acts as a fallback/reporting path. The critical live-answer layers are telegram_bot pre-checks, Phase 8C limited primary, CFO conversation/brain, plain command-router handlers, and TelegramRouter fallback.",
    ]
    return summary, "\n".join(lines)


def main() -> int:
    ensure_audit_dir()
    timestamp = now_timestamp()
    layers = build_layers()
    routing_steps, collisions = build_routing_audit()
    data_sources = build_data_source_audit(layers)
    mock_hits = find_mock_stale_occurrences()
    safety = build_safety_audit()
    layer_tests = build_layer_test_results(timestamp)

    layer_json = {
        "timestamp": timestamp,
        "layers": layers,
        "supabase_write_attempted": False,
    }
    layer_md_lines = ["# Hermes System Layer Audit", "", f"Timestamp: {timestamp}", ""]
    for layer in layers:
        layer_md_lines += [
            f"## {layer['layer']}",
            f"- file path: {layer['file_path']}",
            f"- line: {layer['line_number']}",
            f"- purpose: {layer['purpose']}",
            f"- state: {layer['state']}",
            f"- read sources: {', '.join(layer['read_sources']) or 'none found'}",
            f"- write targets: {', '.join(layer['write_targets']) or 'none found'}",
            f"- safety boundary: {layer['safety_boundary']}",
            f"- known risks: {', '.join(layer['known_risks']) or 'none noted'}",
            f"- can affect live Telegram response: {layer['can_affect_live_telegram_response']}",
            f"- uses mock data: {layer['uses_mock_data']}",
            f"- can call network/model providers: {layer['can_call_network_or_model_providers']}",
            f"- can write Supabase: {layer['can_write_supabase']}",
            "",
        ]
    write_json(AUDIT_DIR / f"hermes_system_layer_audit_{timestamp}.json", layer_json)
    write_md(AUDIT_DIR / f"hermes_system_layer_audit_{timestamp}.md", "\n".join(layer_md_lines))

    routing_json = {"timestamp": timestamp, "steps": routing_steps, "collisions": collisions}
    routing_md = ["# Hermes Routing Order Audit", "", f"Timestamp: {timestamp}", ""]
    routing_md += ["## Actual Live Telegram Order"]
    for step in routing_steps:
        routing_md += [
            f"{step['step']}. {step['name']}",
            f"   function: {step['function_name']}",
            f"   file: {step['file_path']}:{step['line_number']}",
            f"   catches: {', '.join(step['message_types'])}",
            f"   overrides later layers: {step['can_override_later_layers']}",
            f"   evidence dump risk: {step['can_cause_evidence_dump']}",
            f"   quality fallback risk: {step['can_cause_quality_fallback']}",
            f"   Phase 8C position: {step['phase8c_position']}",
        ]
    routing_md += ["", "## Routing Collisions"]
    for item in collisions:
        routing_md += [f"- {item['collision']}: {item['current_status']}"]
    write_json(AUDIT_DIR / f"hermes_routing_order_audit_{timestamp}.json", routing_json)
    write_md(AUDIT_DIR / f"hermes_routing_order_audit_{timestamp}.md", "\n".join(routing_md))

    data_json = {"timestamp": timestamp, "sources": data_sources, "supabase_write_attempted": False}
    data_md = ["# Hermes Data Source Audit", "", f"Timestamp: {timestamp}", ""]
    for item in data_sources:
        data_md += [
            f"## {item['source']}",
            f"- read by: {', '.join(item['read_by_modules']) or 'none'}",
            f"- written by: {', '.join(item['written_by_modules']) or 'none'}",
            f"- safe/unsafe: {item['safe_or_unsafe']}",
            f"- contains secrets: {item['contains_secrets']}",
            f"- contains private client data: {item['contains_private_client_data']}",
            f"- stale risk: {item['stale_risk']}",
            f"- duplicate risk: {item['duplicate_risk']}",
            f"- source of truth: {item['source_of_truth_status']}",
            "",
        ]
    write_json(AUDIT_DIR / f"hermes_data_source_audit_{timestamp}.json", data_json)
    write_md(AUDIT_DIR / f"hermes_data_source_audit_{timestamp}.md", "\n".join(data_md))

    mock_json = {"timestamp": timestamp, "occurrences": mock_hits}
    mock_md = ["# Hermes Mock / Stale Data Audit", "", f"Timestamp: {timestamp}", ""]
    for hit in mock_hits:
        mock_md += [
            f"- {hit['file_path']}:{hit['line']} — {hit['marker']}",
            f"  context: {hit['context']}",
            f"  live path risk: {hit['live_path_risk']}",
            f"  test only: {hit['test_only']}",
            f"  prototype only: {hit['prototype_only']}",
            f"  should block from primary: {hit['should_block_from_primary']}",
            "  recommendation: keep blocked from primary if live-path reachable; otherwise isolate as test/prototype.",
            "",
        ]
    write_json(AUDIT_DIR / f"hermes_mock_stale_data_audit_{timestamp}.json", mock_json)
    write_md(AUDIT_DIR / f"hermes_mock_stale_data_audit_{timestamp}.md", "\n".join(mock_md))

    safety_json = {"timestamp": timestamp, "paths": safety, "supabase_write_attempted": False}
    safety_md = ["# Hermes Safety / Approval Audit", "", f"Timestamp: {timestamp}", ""]
    for item in safety:
        safety_md += [
            f"## {item['command_or_intent']}",
            f"- function: {item['function']}",
            f"- file: {item['file']}",
            f"- current behavior: {item['current_behavior']}",
            f"- approval required: {item['approval_required']}",
            f"- approval boundary shown: {item['approval_boundary_shown']}",
            f"- blocked correctly: {item['blocked_correctly']}",
            f"- risk level: {item['risk_level']}",
            f"- recommendation: {item['recommendation']}",
            "",
        ]
    write_json(AUDIT_DIR / f"hermes_safety_approval_audit_{timestamp}.json", safety_json)
    write_md(AUDIT_DIR / f"hermes_safety_approval_audit_{timestamp}.md", "\n".join(safety_md))

    summary_json, summary_md = build_summary(timestamp, layers, routing_steps)
    write_json(AUDIT_DIR / f"hermes_full_system_audit_summary_{timestamp}.json", summary_json)
    write_md(AUDIT_DIR / f"hermes_full_system_audit_summary_{timestamp}.md", summary_md)

    print(json.dumps({
        "timestamp": timestamp,
        "audit_dir": rel(AUDIT_DIR),
        "layer_count": len(layers),
        "routing_steps": len(routing_steps),
        "mock_occurrences": len(mock_hits),
        "layer_test_results": len(layer_tests),
        "supabase_write_attempted": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
