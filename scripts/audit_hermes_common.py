#!/usr/bin/env python3
from __future__ import annotations

import ast
import importlib
import inspect
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AUDIT_DIR = ROOT / "docs" / "reports" / "audits"
TARGET_LIVE_PATH_FILES = [
    ROOT / "telegram_bot.py",
    ROOT / "lib" / "hermes_cfo_loop_shadow.py",
    ROOT / "prototypes" / "hermes_agentic_cfo_loop.py",
    ROOT / "hermes_command_router" / "router.py",
    ROOT / "hermes_command_router" / "intake.py",
    ROOT / "lib" / "telegram_router.py",
    ROOT / "lib" / "hermes_response_quality.py",
    ROOT / "lib" / "hermes_internal_first.py",
    ROOT / "lib" / "hermes_supabase_first.py",
    ROOT / "lib" / "hermes_cfo_brain.py",
    ROOT / "lib" / "hermes_plain_language_rewriter.py",
]
MOCK_STALE_MARKERS = [
    "Based on mock data",
    "mock",
    "sample",
    "test message",
    "test async message",
    "research_scout_1",
    "content_scout",
    "draft v2 approved",
    "Mailchimp opt-in form",
    "Build and publish lead magnet landing page",
    "Connect affiliate offer link",
    "fake",
    "dummy",
    "TESTFAILURE",
    "artifact_inventory",
    "handoff dump",
    "I can answer from verified artifacts",
    "I wasn't able to generate a quality response",
    "old Executive Memory",
    "stale provider status",
]
SECRET_PATTERNS = [
    r"SUPABASE_SERVICE_ROLE",
    r"SUPABASE_KEY",
    r"OPENROUTER",
    r"OPENAI_API_KEY",
    r"ANTHROPIC",
    r"OANDA",
    r"HERMES_GATEWAY_KEY",
    r"ACCESS_TOKEN",
    r"PRIVATE_KEY",
    r"PASSWORD",
]


@dataclass
class CommandEntry:
    category: str
    phrase: str
    normalized_intent: str
    handler: str
    file_path: str
    output_header: str
    read_sources: list[str]
    write_targets: list[str]
    safety_risk_level: str
    approval_required: bool
    command_style: str
    active_in_live_telegram: bool
    shadow_only: bool
    duplicate_or_overlapping: bool
    old_report_wrapper: bool
    notes: str = ""


def now_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_audit_dir() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def line_number(path: Path, pattern: str) -> int | None:
    for idx, line in enumerate(read_text(path).splitlines(), start=1):
        if pattern in line:
            return idx
    return None


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return str(p.relative_to(ROOT))
    except Exception:
        return str(p)


def import_module(name: str):
    return importlib.import_module(name)


def source_segment(path: Path, node: ast.AST) -> str:
    try:
        return ast.get_source_segment(read_text(path), node) or ""
    except Exception:
        return ""


def extract_continuity_entries() -> list[dict[str, str]]:
    path = ROOT / "telegram_bot.py"
    tree = ast.parse(read_text(path))
    entries: list[dict[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "handle_inbound_message":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "continuity" and isinstance(stmt.value, ast.Dict):
                            for key_node, value_node in zip(stmt.value.keys, stmt.value.values):
                                if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                                    entries.append({
                                        "phrase": key_node.value,
                                        "handler_expr": source_segment(path, value_node).strip(),
                                    })
                            return entries
    return entries


def extract_shadow_command_entries() -> list[dict[str, str]]:
    path = ROOT / "lib" / "hermes_cfo_loop_shadow.py"
    tree = ast.parse(read_text(path))
    entries: list[dict[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "handle_cfo_shadow_command":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "cmd_map" and isinstance(stmt.value, ast.Dict):
                            for key_node, value_node in zip(stmt.value.keys, stmt.value.values):
                                if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                                    entries.append({
                                        "phrase": key_node.value,
                                        "handler_expr": source_segment(path, value_node).strip(),
                                    })
                            return entries
    return entries


def extract_intent_entries() -> list[dict[str, Any]]:
    intake = import_module("hermes_command_router.intake")
    rows = []
    for phrases, intent, priority, requires_approval in getattr(intake, "_INTENT_MAP"):
        for phrase in phrases:
            rows.append({
                "phrase": phrase,
                "intent": intent,
                "priority": priority,
                "requires_approval": bool(requires_approval),
            })
    return rows


def extract_plain_intent_handlers() -> dict[str, str]:
    router = import_module("hermes_command_router.router")
    mapping = getattr(router, "_PLAIN_INTENTS")
    result: dict[str, str] = {}
    for intent, fn in mapping.items():
        result[intent] = getattr(fn, "__name__", repr(fn))
    return result


def extract_plain_intents_with_cmd() -> set[str]:
    router = import_module("hermes_command_router.router")
    return set(getattr(router, "_PLAIN_INTENTS_WITH_CMD"))


def extract_safe_repeatable_memory_intents() -> list[str]:
    path = ROOT / "telegram_bot.py"
    tree = ast.parse(read_text(path))
    results: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "NexusTelegramBot":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Name) and target.id == "SAFE_REPEATABLE_MEMORY_INTENTS":
                            call = stmt.value
                            if isinstance(call, ast.Call) and call.args:
                                arg = call.args[0]
                                if isinstance(arg, (ast.Set, ast.Tuple, ast.List)):
                                    for elt in arg.elts:
                                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                            results.append(elt.value)
                            return sorted(results)
    return sorted(results)


def first_header(text: str) -> str:
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def extract_paths_and_tables(path: Path) -> dict[str, list[str]]:
    text = read_text(path)
    file_paths = sorted(set(re.findall(r"docs/reports/[A-Za-z0-9_./-]+", text)))
    tables = sorted(set(re.findall(r'table\("([A-Za-z0-9_]+)"\)', text)))
    networks = []
    for token in ("urlopen(", "requests.", "create_client(", "synthesize(", "ai_synthesize(", "urllib.request"):
        if token in text:
            networks.append(token.rstrip("("))
    writes = []
    for token in ("write_text(", ".open(\"a", "open(", ".insert(", ".update(", ".upsert(", ".execute()", "json.dump("):
        if token in text:
            writes.append(token.strip())
    return {
        "file_paths": file_paths,
        "tables": tables,
        "network_tokens": sorted(set(networks)),
        "write_tokens": sorted(set(writes)),
    }


def normalize_category(intent_or_phrase: str) -> str:
    value = intent_or_phrase.lower()
    if "memory" in value:
        return "memory"
    if "lesson" in value or "learn" in value or "failed_response" in value:
        return "learning"
    if "daily" in value or "plan" in value or "revenue_plan" in value:
        return "daily plan"
    if "approval" in value or "approve" in value or "reject" in value:
        return "approval"
    if "revenue" in value or "launch" in value or "cta" in value or "packet" in value or "funnel" in value:
        return "revenue/funnel"
    if "draft" in value or "content" in value or "newsletter" in value or "lead magnet" in value:
        return "content draft"
    if "scout" in value or "research" in value or "question" in value:
        return "scouts/research"
    if "cfo" in value or "shadow" in value or "primary" in value:
        return "CFO loop status"
    if "status" in value or "health" in value or "monitor" in value:
        return "system health"
    if "provider" in value or "gateway" in value or "model" in value:
        return "provider/gateway"
    if "small_talk" in value or "tomorrow" in value or "unknown" in value or "help" in value:
        return "fallback/help/small talk"
    return "summaries"


def risk_level(phrase: str, requires_approval: bool = False) -> str:
    lower = phrase.lower()
    if requires_approval:
        return "high"
    if any(word in lower for word in ["deploy", "publish", "email", "payment", "stripe", "affiliate", "trade", "spend"]):
        return "high"
    if any(word in lower for word in ["approve", "reject", "record", "save", "mark ", "clear ", "fix ", "improve ", "create ", "build "]):
        return "medium"
    return "low"


def likely_duplicate(phrase: str, all_phrases: set[str]) -> bool:
    normalized = phrase.lower().strip().rstrip(".?!")
    bare = normalized.replace("hermes, ", "").replace("hermes ", "")
    return bare in all_phrases and bare != normalized


def uses_old_report_wrapper(intent: str) -> bool:
    router = import_module("hermes_command_router.router")
    return intent not in getattr(router, "_PLAIN_INTENTS")


def find_mock_stale_occurrences() -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for path in TARGET_LIVE_PATH_FILES:
        lines = read_text(path).splitlines()
        for idx, line in enumerate(lines, start=1):
            lower = line.lower()
            for marker in MOCK_STALE_MARKERS:
                if marker.lower() in lower:
                    hits.append({
                        "file_path": rel(path),
                        "line": idx,
                        "marker": marker,
                        "context": line.strip()[:220],
                        "live_path_risk": rel(path) not in {
                            "prototypes/hermes_agentic_cfo_loop.py",
                            "scripts/test_phase8c_grounding_blocks_mock_primary.py",
                        },
                        "test_only": "/scripts/" in str(path),
                        "prototype_only": "prototypes/" in str(path),
                        "should_block_from_primary": marker.lower() in {
                            "based on mock data",
                            "artifact_inventory",
                            "i can answer from verified artifacts",
                            "i wasn't able to generate a quality response",
                            "research_scout_1",
                            "mailchimp opt-in form",
                            "build and publish lead magnet landing page",
                            "connect affiliate offer link",
                        },
                    })
    return hits


def no_secrets_in_text(text: str) -> bool:
    return not any(re.search(pattern, text, flags=re.I) for pattern in SECRET_PATTERNS)


def latest_matching(pattern: str) -> Path | None:
    matches = sorted(AUDIT_DIR.glob(pattern))
    return matches[-1] if matches else None


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False), encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def safe_bot():
    import telegram_bot
    telegram_bot.NexusTelegramBot.test_connection = lambda self: None
    return telegram_bot.NexusTelegramBot()


def trace_route(message: str, limited_primary: bool = True) -> dict[str, Any]:
    os.environ.setdefault("HERMES_CFO_LOOP_PROVIDER", "mock")
    if limited_primary:
        os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
    from lib.hermes_cfo_loop_shadow import handle_cfo_shadow_command, should_run_cfo_limited_primary, run_cfo_limited_primary
    from lib.hermes_cfo_brain import classify_cfo_intent, should_use_cfo_brain
    from lib.hermes_cfo_conversation_layer import detect_cfo_conversation_need, is_high_priority_cfo_phrase
    from hermes_command_router.intake import classify_intent
    from lib.telegram_router import TelegramRouter
    import telegram_bot

    bot = safe_bot()
    raw = message
    memory_reply = bot._try_memory_command(raw)
    if memory_reply is not None:
        intent, _, _ = classify_intent(raw)
        return {
            "handled_by_layer": "memory_command_precheck",
            "intent": intent,
            "handler": "_try_memory_command -> run_command",
            "mode": "exact",
            "response": memory_reply,
        }

    if handle_cfo_shadow_command(raw.lower().strip()):
        return {
            "handled_by_layer": "cfo_shadow_command",
            "intent": "cfo_shadow_command",
            "handler": "handle_cfo_shadow_command",
            "mode": "exact",
            "response": handle_cfo_shadow_command(raw.lower().strip()) or "",
        }

    normalized = telegram_bot._normalize_telegram_command(raw) if raw else raw
    normalized_lower = (normalized or "").strip().lower()
    normalized_strip = normalized_lower.lstrip("hermes").lstrip(",").lstrip().rstrip(".?!")

    if should_run_cfo_limited_primary(raw):
        response, used = run_cfo_limited_primary(message=raw)
        if used and response:
            return {
                "handled_by_layer": "phase8c_limited_primary",
                "intent": "limited_primary",
                "handler": "run_cfo_limited_primary",
                "mode": "primary",
                "response": response,
            }

    forced_intents = {
        "option_selection",
        "task_reference",
        "simplify_previous_response",
        "explain_previous_response",
        "morning_activity_question",
        "failure_feedback",
    }
    p7c_intent = classify_cfo_intent(normalized_lower)
    if p7c_intent in forced_intents:
        response = bot.handle_inbound_message(raw)
        return {
            "handled_by_layer": "phase7c_forced_intent",
            "intent": p7c_intent,
            "handler": "process_with_cfo_brain",
            "mode": "legacy",
            "response": response,
        }

    continuity = {entry["phrase"] for entry in extract_continuity_entries()}
    if normalized_lower in continuity or normalized_lower.rstrip(".?!") in continuity or normalized_strip in continuity:
        response = bot.handle_inbound_message(raw)
        return {
            "handled_by_layer": "telegram_continuity_exact",
            "intent": "continuity_exact",
            "handler": "continuity[...]",
            "mode": "exact",
            "response": response,
        }

    if detect_cfo_conversation_need(normalized_lower) or is_high_priority_cfo_phrase(normalized_lower):
        response = bot.handle_inbound_message(raw)
        return {
            "handled_by_layer": "phase7a_cfo_conversation",
            "intent": "cfo_conversation",
            "handler": "build_cfo_response",
            "mode": "legacy",
            "response": response,
        }

    if should_use_cfo_brain(normalized_lower):
        response = bot.handle_inbound_message(raw)
        return {
            "handled_by_layer": "phase7b_cfo_brain",
            "intent": classify_cfo_intent(normalized_lower),
            "handler": "process_with_cfo_brain",
            "mode": "legacy",
            "response": response,
        }

    route = bot.classify_message_route(raw)
    if route == "command":
        response = bot._handle_command_mode(raw)
        return {
            "handled_by_layer": "telegram_router_command",
            "intent": classify_intent(raw)[0],
            "handler": "_handle_command_mode -> run_command",
            "mode": "exact",
            "response": response,
        }
    if route == "daily_plan":
        response = bot._build_daily_plan()
        return {
            "handled_by_layer": "telegram_router_daily_plan",
            "intent": "daily_plan",
            "handler": "_build_daily_plan",
            "mode": "legacy",
            "response": response,
        }
    if route == "task_selection":
        response = bot._task_selection_reply(raw)
        return {
            "handled_by_layer": "telegram_router_task_selection",
            "intent": "task_selection",
            "handler": "_task_selection_reply",
            "mode": "legacy",
            "response": response or "",
        }
    return {
        "handled_by_layer": "telegram_router_chat_or_fallback",
        "intent": route,
        "handler": "TelegramRouter.route_incoming_message",
        "mode": "legacy",
        "response": "",
    }


def render_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    widths = [max(len(str(cell)) for cell in col) for col in zip(*rows)]
    out = []
    for idx, row in enumerate(rows):
        out.append(" | ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)))
        if idx == 0:
            out.append(" | ".join("-" * widths[i] for i in range(len(widths))))
    return "\n".join(out)
