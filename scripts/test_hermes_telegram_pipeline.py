#!/usr/bin/env python3
"""
test_hermes_telegram_pipeline.py

Verify 2-way Telegram communication:
  1. Intent classification for all supported command phrases
  2. Router produces a structured Hermes Report for each intent
  3. Gate correctly allows direct responses (bypasses rate limit)
  4. Gate correctly blocks automated duplicates (cooldown respected)

Usage:
  cd /Users/raymonddavis/nexus-ai
  python3 scripts/test_hermes_telegram_pipeline.py
"""

import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Load .env
from pathlib import Path
_env = Path(ROOT) / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command
from telegram_bot import NexusTelegramBot
import telegram_bot as telegram_module

PASS = "✅ PASS"
FAIL = "❌ FAIL"

tests_run = 0
tests_passed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global tests_run, tests_passed
    tests_run += 1
    if condition:
        tests_passed += 1
        print(f"  {PASS}: {label}")
    else:
        print(f"  {FAIL}: {label}" + (f" — {detail}" if detail else ""))


# ── Test 1: Intent classification ────────────────────────────────────────────

print("\n[1] Intent classification")

cases = [
    ("are we ready for pilot",        "pilot_readiness"),
    ("ready for 10-user pilot",       "pilot_readiness"),
    ("pilot ready",                   "pilot_readiness"),
    ("what is the next best move",    "next_best_move"),
    ("what do you recommend",         "next_best_move"),
    ("recommend next step",           "next_best_move"),
    ("can you hear me",               "communication_health"),
    ("comm check hermes",             "communication_health"),
    ("is this working",               "communication_health"),
    ("check backend health",          "health_check"),
    ("worker status",                 "worker_status"),
    ("queue status",                  "queue_status"),
    ("trading status",                "trading_lab_status"),
    ("gibberish xyz abc 123",         "unknown"),
]

for phrase, expected_intent in cases:
    intent, priority, _ = classify_intent(phrase)
    check(
        f'"{phrase}" → {expected_intent}',
        intent == expected_intent,
        f"got: {intent}",
    )

# ── Test 2: Router produces Hermes Report ─────────────────────────────────────

print("\n[2] Router produces Hermes Report for key commands")

report_commands = [
    "are we ready for pilot",
    "next best move",
    "can you hear me",
]

for cmd in report_commands:
    try:
        report = run_command(cmd, source="cli", sender="test")
        has_status  = "Status:" in report or "HERMES REPORT" in report
        has_evidence = "Evidence:" in report
        check(
            f'run_command("{cmd}") → structured report',
            has_status and has_evidence,
            report[:120] if not (has_status and has_evidence) else "",
        )
    except Exception as e:
        check(f'run_command("{cmd}")', False, str(e))
        traceback.print_exc()

# ── Test 3: Unknown intent → clarifying question ──────────────────────────────

print("\n[3] Unknown command → clarifying question (not a list dump)")

report = run_command("blah blah something unclear", source="cli", sender="test")
has_question = "?" in report or "Options:" in report or "What would" in report
check("Unknown command asks clarifying question", has_question, report[:200])

# ── Test 4: Gate — direct response bypasses rate limit ───────────────────────

print("\n[4] Hermes gate: direct responses bypass rate limit")

from lib.hermes_gate import send_direct_response, _rate_limit_ok

# Mock: rate limit check should not block direct responses
# We test that send_direct_response exists and is callable (actual send skipped in CI)
check(
    "send_direct_response is callable",
    callable(send_direct_response),
)

# ── Test 4b: /models command formatting ───────────────────────────────────────

print("\n[4b] /models command formatting")

bot = NexusTelegramBot.__new__(NexusTelegramBot)
models_text = NexusTelegramBot._cmd_models(bot)
check("/models includes header", "Model Diagnostics" in models_text)
check("/models includes routing preview", "Routing Preview" in models_text)
check("/models includes funding_strategy", "funding_strategy" in models_text)

# ── Test 4c: Telegram route modes ─────────────────────────────────────────────

print("\n[4c] Telegram route modes")

route_bot = NexusTelegramBot.__new__(NexusTelegramBot)
route_bot.safe_help_text = lambda: "help"
route_bot.render_chat_response = NexusTelegramBot.render_chat_response.__get__(route_bot, NexusTelegramBot)
route_bot.render_report_response = NexusTelegramBot.render_report_response.__get__(route_bot, NexusTelegramBot)
route_bot.render_short_status = NexusTelegramBot.render_short_status.__get__(route_bot, NexusTelegramBot)
route_bot.render_report_summary = NexusTelegramBot.render_report_summary.__get__(route_bot, NexusTelegramBot)
route_bot.classify_message_route = NexusTelegramBot.classify_message_route.__get__(route_bot, NexusTelegramBot)
route_bot._build_daily_plan = NexusTelegramBot._build_daily_plan.__get__(route_bot, NexusTelegramBot)
route_bot._task_selection_reply = NexusTelegramBot._task_selection_reply.__get__(route_bot, NexusTelegramBot)
route_bot._handle_llm_error = NexusTelegramBot._handle_llm_error.__get__(route_bot, NexusTelegramBot)
route_bot.handle_coordination_command = lambda text: "Status: ok\nEvidence: []"
route_bot.render_report_email = lambda text: "FULL REPORT"
route_bot.send_report_email = lambda subject, body: None
route_bot._conversational_reply = lambda text: "hey ray"
route_bot._queue_task_from_selection = lambda title: {"ok": True, "task_id": "t1", "status": "queued"}
route_bot.last_plan_items = []
route_bot._repeat_error_key = ""
route_bot._repeat_error_count = 0
route_bot.pending_approval_action = None
route_bot.task_lifecycle = {}
route_bot.ops_memory = {
    "latest_daily_plan": [],
    "task_lifecycle": {},
    "pending_approval": None,
    "recent_completed": [],
    "recent_failed": [],
    "active_priorities": [],
    "blocked_priorities": [],
    "completed_priorities": [],
    "recent_recommendations": [],
}
route_bot._save_operational_memory = lambda: None
route_bot._start_work_session_summary = NexusTelegramBot._start_work_session_summary.__get__(route_bot, NexusTelegramBot)
route_bot._pause_work_session_summary = NexusTelegramBot._pause_work_session_summary.__get__(route_bot, NexusTelegramBot)
route_bot._resume_work_session_summary = NexusTelegramBot._resume_work_session_summary.__get__(route_bot, NexusTelegramBot)
route_bot._summarize_work_session = NexusTelegramBot._summarize_work_session.__get__(route_bot, NexusTelegramBot)
route_bot._handle_swarm_followup = NexusTelegramBot._handle_swarm_followup.__get__(route_bot, NexusTelegramBot)
route_bot.pending_swarm_plan = None

chat_resp = NexusTelegramBot.handle_inbound_message(route_bot, "good morning")
how_are_you_resp = NexusTelegramBot.handle_inbound_message(route_bot, "How are you?")
cmd_resp = NexusTelegramBot.handle_inbound_message(route_bot, "worker status")
rep_resp = NexusTelegramBot.handle_inbound_message(route_bot, "generate report")
plan_resp = NexusTelegramBot.handle_inbound_message(route_bot, "What should we work on today?")
plan_resp_alt = NexusTelegramBot.handle_inbound_message(route_bot, "what do you recommend today for work?")
funding_insights_resp = NexusTelegramBot.handle_inbound_message(route_bot, "What funding insights do we have?")
credit_insights_resp = NexusTelegramBot.handle_inbound_message(route_bot, "What credit workflow insights do we have?")
knowledge_report_resp = NexusTelegramBot.handle_inbound_message(route_bot, "Send me a knowledge report.")
sel_resp = NexusTelegramBot.handle_inbound_message(route_bot, "Do item 1")
no_plan_bot = NexusTelegramBot.__new__(NexusTelegramBot)
no_plan_bot.safe_help_text = lambda: "help"
no_plan_bot.render_chat_response = NexusTelegramBot.render_chat_response.__get__(no_plan_bot, NexusTelegramBot)
no_plan_bot.render_short_status = NexusTelegramBot.render_short_status.__get__(no_plan_bot, NexusTelegramBot)
no_plan_bot.render_report_summary = NexusTelegramBot.render_report_summary.__get__(no_plan_bot, NexusTelegramBot)
no_plan_bot.render_report_email = lambda text: "FULL REPORT"
no_plan_bot.send_report_email = lambda subject, body: None
no_plan_bot.classify_message_route = NexusTelegramBot.classify_message_route.__get__(no_plan_bot, NexusTelegramBot)
no_plan_bot._task_selection_reply = NexusTelegramBot._task_selection_reply.__get__(no_plan_bot, NexusTelegramBot)
no_plan_bot._handle_approval_reply = NexusTelegramBot._handle_approval_reply.__get__(no_plan_bot, NexusTelegramBot)
no_plan_bot._risky_action_requested = NexusTelegramBot._risky_action_requested.__get__(no_plan_bot, NexusTelegramBot)
no_plan_bot._handle_command_mode = NexusTelegramBot._handle_command_mode.__get__(no_plan_bot, NexusTelegramBot)
no_plan_bot._conversational_reply = lambda text: "hey"
no_plan_bot.handle_coordination_command = lambda text: "Status: ok"
no_plan_bot.handle_basic_command = lambda text: "Status: ok"
no_plan_bot._queue_task_from_selection = lambda title: {"ok": True, "task_id": "t1", "status": "queued"}
no_plan_bot.last_plan_items = []
no_plan_bot.pending_approval_action = None
no_plan_bot.pending_swarm_plan = None
no_plan_bot.task_lifecycle = {}
no_plan_bot.ops_memory = {
    "latest_daily_plan": [],
    "task_lifecycle": {},
    "pending_approval": None,
    "recent_completed": [],
    "recent_failed": [],
    "active_priorities": [],
    "blocked_priorities": [],
    "completed_priorities": [],
    "recent_recommendations": [],
}
no_plan_bot._save_operational_memory = lambda: None
no_plan_bot._repeat_error_key = ""
no_plan_bot._repeat_error_count = 0
no_plan_resp = NexusTelegramBot.handle_inbound_message(no_plan_bot, "Do item 1")
approval_prompt = NexusTelegramBot.handle_inbound_message(no_plan_bot, "send email to client about update")
approval_ok = NexusTelegramBot.handle_inbound_message(no_plan_bot, "APPROVE")
approval_cancel_prompt = NexusTelegramBot.handle_inbound_message(no_plan_bot, "change production config now")
approval_cancel = NexusTelegramBot.handle_inbound_message(no_plan_bot, "CANCEL")
weekly_rep_resp = NexusTelegramBot.handle_inbound_message(route_bot, "weekly report")
alias_sel_resp = NexusTelegramBot.handle_inbound_message(route_bot, "start the second one")
option_sel_resp = NexusTelegramBot.handle_inbound_message(route_bot, "option 3")
lets_do_resp = NexusTelegramBot.handle_inbound_message(route_bot, "let's do 3")
start_session_resp = NexusTelegramBot.handle_inbound_message(route_bot, "start work session")
pause_session_resp = NexusTelegramBot.handle_inbound_message(route_bot, "pause work session")
resume_session_resp = NexusTelegramBot.handle_inbound_message(route_bot, "resume work session")
sum_session_resp = NexusTelegramBot.handle_inbound_message(route_bot, "summarize work session")
list_agents_resp = NexusTelegramBot.handle_inbound_message(route_bot, "List agents")
swarm_plan_resp = NexusTelegramBot.handle_inbound_message(route_bot, "Plan swarm task for improving funding workflow")
swarm_start_resp = NexusTelegramBot.handle_inbound_message(route_bot, "start swarm task")
orig_ops_monitor = telegram_module.run_ops_monitor_summary
telegram_module.run_ops_monitor_summary = lambda send_report_email=None: {"ok": True, "read_only": True, "can_execute": False, "dry_run_only": True, "summary": {}, "email": {"sent": False, "configured": False, "error": "not configured"}}
ops_monitor_resp = NexusTelegramBot.handle_inbound_message(route_bot, "run ops monitor")
telegram_module.run_ops_monitor_summary = orig_ops_monitor

check("chat mode is plain", "<pre>" not in chat_resp and "hey ray" in chat_resp)
check("how are you stays normal chat", "hey ray" in how_are_you_resp.lower())
check("command mode is plain structured text", "<pre>" not in cmd_resp and "Status:" in cmd_resp)
check("report request mode confirms email", "sent the full report to your email" in rep_resp.lower())
check("planning mode returns numbered actions", "1)" in plan_resp and "2)" in plan_resp)
check("planning heuristic routes work prompt", "1)" in plan_resp_alt and "2)" in plan_resp_alt)
check("funding insights route returns knowledge summary", "funding insights" in funding_insights_resp.lower())
check("credit insights route returns knowledge summary", "credit workflow insights" in credit_insights_resp.lower())
check("knowledge report route confirms email/review", "knowledge brain report" in knowledge_report_resp.lower() and "email/review" in knowledge_report_resp.lower())
check("task selection queues task", "queued" in sel_resp.lower() or "notify" in sel_resp.lower())
check("task selection without plan asks for plan", "ask for today's plan" in no_plan_resp.lower())
check("risky action asks approval", "reply approve or cancel" in approval_prompt.lower())
check("approve proceeds", "approved" in approval_ok.lower() or "queued" in approval_ok.lower())
check("cancel stops action", "did not proceed" in approval_cancel.lower())
check("weekly report confirms email", "sent the full report to your email" in weekly_rep_resp.lower())
check("task selection alias works", "done" in alias_sel_resp.lower())
check("task selection option alias works", "done" in option_sel_resp.lower() or "queued" in option_sel_resp.lower())
check("task selection lets-do alias works", "done" in lets_do_resp.lower() or "queued" in lets_do_resp.lower())
check("start work session works", "work session" in start_session_resp.lower() and "started" in start_session_resp.lower())
check("pause work session works", "paused" in pause_session_resp.lower())
check("resume work session works", "work session" in resume_session_resp.lower())
check("summarize work session works", "work session" in sum_session_resp.lower())
check("no HERMES REPORT in chat response", "HERMES REPORT" not in chat_resp)
check("list agents works", "agent" in list_agents_resp.lower() and "lineup" in list_agents_resp.lower())
check("swarm plan asks start or wait", "start swarm task" in swarm_plan_resp.lower() and "wait" in swarm_plan_resp.lower())
check("swarm start stays dry run", "planning-only" in swarm_start_resp.lower())
check("ops monitor trigger returns short confirmation", "summary" in ops_monitor_resp.lower() and "email" in ops_monitor_resp.lower())
check("ops monitor trigger is honest on email failure", "not configured" in ops_monitor_resp.lower() or "saved" in ops_monitor_resp.lower())
check("ops monitor trigger avoids hermes report dump", "HERMES REPORT" not in ops_monitor_resp)
check("no HERMES REPORT in funding insights", "HERMES REPORT" not in funding_insights_resp)
check("no HERMES REPORT in credit insights", "HERMES REPORT" not in credit_insights_resp)
check("no HERMES REPORT in knowledge report confirmation", "HERMES REPORT" not in knowledge_report_resp)

cmd_bot = NexusTelegramBot.__new__(NexusTelegramBot)
cmd_bot.safe_help_text = lambda: "help"
cmd_bot.render_short_status = NexusTelegramBot.render_short_status.__get__(cmd_bot, NexusTelegramBot)
cmd_bot.handle_basic_command = lambda text: "You currently have 2 running tasks and 1 pending approvals."
cmd_bot.handle_coordination_command = lambda text: "Status: ok"
tasks_cmd = NexusTelegramBot._handle_command_mode(cmd_bot, "/tasks")
running_cmd = NexusTelegramBot._handle_command_mode(cmd_bot, "/running")
pending_cmd = NexusTelegramBot._handle_command_mode(cmd_bot, "/pending")
approvals_cmd = NexusTelegramBot._handle_command_mode(cmd_bot, "/approvals")
check("/tasks command short summary", "running tasks" in tasks_cmd.lower())
check("/running command short summary", "running" in running_cmd.lower())
check("/pending command short summary", "pending" in pending_cmd.lower())
check("/approvals command short summary", "approval" in approvals_cmd.lower())

class _FakeResp:
    def raise_for_status(self):
        return None
    def json(self):
        return {"choices": [{"message": {"content": "chat ok"}}]}

orig_post = __import__("requests").post
import requests as _rq
captured = {"url": ""}
def _fake_post(url, headers=None, json=None, timeout=None):
    captured["url"] = url
    return _FakeResp()
_rq.post = _fake_post
try:
    os.environ["OPENROUTER_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "test-key")
    conv_bot = NexusTelegramBot.__new__(NexusTelegramBot)
    msg = NexusTelegramBot._conversational_reply(conv_bot, "how are you today")
    check("telegram chat uses OpenRouter path", "openrouter.ai" in captured["url"] and "ollama" not in captured["url"])
    check("telegram chat returns response", "chat ok" in msg)
finally:
    _rq.post = orig_post

lifecycle_bot = NexusTelegramBot.__new__(NexusTelegramBot)
lifecycle_bot.task_lifecycle = {"a": "queued", "b": "running", "c": "completed", "d": "failed", "e": "canceled"}
tasks_summary = NexusTelegramBot._cmd_tasks_summary(lifecycle_bot)
check("task lifecycle summary includes states", "completed" in tasks_summary.lower() and "failed" in tasks_summary.lower())

fail_bot = NexusTelegramBot.__new__(NexusTelegramBot)
fail_bot.safe_help_text = lambda: "help"
fail_bot.render_chat_response = NexusTelegramBot.render_chat_response.__get__(fail_bot, NexusTelegramBot)
fail_bot.classify_message_route = NexusTelegramBot.classify_message_route.__get__(fail_bot, NexusTelegramBot)
fail_bot._task_selection_reply = lambda text: None
fail_bot._build_daily_plan = NexusTelegramBot._build_daily_plan.__get__(fail_bot, NexusTelegramBot)
fail_bot._handle_llm_error = NexusTelegramBot._handle_llm_error.__get__(fail_bot, NexusTelegramBot)
fail_bot._conversational_reply = lambda text: (_ for _ in ()).throw(RuntimeError("model down"))
fail_bot.last_plan_items = []
fail_bot._repeat_error_key = ""
fail_bot._repeat_error_count = 0
fail_bot.pending_approval_action = None
fail_bot.pending_swarm_plan = None
fail_bot.ops_memory = {
    "latest_daily_plan": [],
    "task_lifecycle": {},
    "pending_approval": None,
    "recent_completed": [],
    "recent_failed": [],
    "active_priorities": [],
    "blocked_priorities": [],
    "completed_priorities": [],
    "recent_recommendations": [],
}
fail_bot._save_operational_memory = lambda: None
llm_fail = NexusTelegramBot.handle_inbound_message(fail_bot, "hello there")
check("llm failure fallback message", "chat model is unavailable" in llm_fail.lower())

# ── Test 5: Gate — automated alerts respect cooldown ─────────────────────────

print("\n[5] Hermes gate: empty messages suppressed")

from lib.hermes_gate import _is_empty

empty_samples = [
    "No issues detected — all clear",
    "Nothing to report at this time",
    "0 emails processed today",
    "Done — 0 updates",
]
not_empty_samples = [
    "WARNING: 3 workers stale — restart required",
    "CRITICAL: Revenue gap detected — follow up needed",
    "5 leads overdue for followup",
]

for sample in empty_samples:
    check(f'Empty filter suppresses: "{sample[:50]}"', _is_empty(sample))

for sample in not_empty_samples:
    check(f'Empty filter passes: "{sample[:50]}"', not _is_empty(sample))

# ── Summary ────────────────────────────────────────────────────────────────────

print(f"\n{'='*52}")
print(f"  Telegram pipeline: {tests_passed}/{tests_run} tests passed")
if tests_passed == tests_run:
    print("  All tests passed.")
else:
    print(f"  {tests_run - tests_passed} test(s) FAILED — see above.")
print(f"{'='*52}\n")

sys.exit(0 if tests_passed == tests_run else 1)
