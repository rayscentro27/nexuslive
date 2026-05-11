#!/usr/bin/env python3
"""
test_ollama_model_router.py

Health check for Hermes Ollama model router:
  1. OLLAMA_BASE_URL is reachable
  2. llama3.2:3b responds correctly
  3. qwen3:8b responds correctly (or fallback triggers gracefully)
  4. Model router selects correct model for each intent
  5. Fallback to llama3.2:3b when qwen3:8b is unavailable

Usage:
  cd /Users/raymonddavis/nexus-ai
  python3 scripts/test_ollama_model_router.py

Requirements:
  - SSH tunnel open: ssh -N -L 11555:localhost:11434 root@YOUR_NETCUP_IP
  - qwen3:8b pulled on Netcup: ollama pull qwen3:8b
"""

import os
import sys
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pathlib import Path
_env = Path(ROOT) / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

from lib.hermes_ollama_client import (
    is_reachable, list_models, call, call_with_fallback,
    OLLAMA_BASE_URL, HERMES_DEFAULT_MODEL, HERMES_REASONING_MODEL,
)
from lib.hermes_model_router import model_class_for, model_name_for, synthesize

PASS = "✅ PASS"
FAIL = "❌ FAIL"
WARN = "⚠️  WARN"

tests_run = 0
tests_passed = 0
tests_warned = 0


def check(label: str, condition: bool, detail: str = "", warn_only: bool = False) -> None:
    global tests_run, tests_passed, tests_warned
    tests_run += 1
    if condition:
        tests_passed += 1
        print(f"  {PASS}: {label}")
    elif warn_only:
        tests_warned += 1
        print(f"  {WARN}: {label}" + (f" — {detail}" if detail else ""))
    else:
        print(f"  {FAIL}: {label}" + (f" — {detail}" if detail else ""))


# ── Config display ─────────────────────────────────────────────────────────────

print(f"\nOllama config:")
print(f"  OLLAMA_BASE_URL        = {OLLAMA_BASE_URL}")
print(f"  HERMES_DEFAULT_MODEL   = {HERMES_DEFAULT_MODEL}")
print(f"  HERMES_REASONING_MODEL = {HERMES_REASONING_MODEL}")

# ── Test 1: Reachability ───────────────────────────────────────────────────────

print("\n[1] Reachability")
reachable = is_reachable(timeout=5)
check("Ollama endpoint reachable", reachable,
      f"Is SSH tunnel open? ssh -N -L 11555:localhost:11434 root@YOUR_NETCUP_IP")

if not reachable:
    print(f"\n  ⛔ Cannot reach {OLLAMA_BASE_URL} — skipping model tests.")
    print(f"     Start the SSH tunnel and retry.\n")
    sys.exit(1)

# ── Test 2: Model inventory ────────────────────────────────────────────────────

print("\n[2] Available models on Netcup Ollama")
models = list_models()
print(f"  Loaded models: {models or '(none yet)'}")

default_loaded   = any(HERMES_DEFAULT_MODEL   in m for m in models)
reasoning_loaded = any(HERMES_REASONING_MODEL in m for m in models)

check(f"{HERMES_DEFAULT_MODEL} is loaded", default_loaded,
      f"Run on Netcup: ollama pull {HERMES_DEFAULT_MODEL}")
check(f"{HERMES_REASONING_MODEL} is loaded", reasoning_loaded,
      f"Run on Netcup: ollama pull {HERMES_REASONING_MODEL}", warn_only=True)

# ── Test 3: Default model responds ────────────────────────────────────────────

print(f"\n[3] {HERMES_DEFAULT_MODEL} response")
if default_loaded:
    result = call("Reply with exactly: DEFAULT_OK", model=HERMES_DEFAULT_MODEL, timeout=45)
    check(
        f"{HERMES_DEFAULT_MODEL} responds",
        result["success"],
        result.get("error", ""),
    )
    if result["success"]:
        print(f"       Response: {result['response'][:80]}")
        print(f"       Duration: {result['duration_s']}s")
else:
    check(f"{HERMES_DEFAULT_MODEL} responds", False,
          f"Model not loaded — pull it first: ollama pull {HERMES_DEFAULT_MODEL}")

# ── Test 4: Reasoning model responds ─────────────────────────────────────────

print(f"\n[4] {HERMES_REASONING_MODEL} response")
if reasoning_loaded:
    result = call("Reply with exactly: REASONING_OK", model=HERMES_REASONING_MODEL, timeout=90)
    check(
        f"{HERMES_REASONING_MODEL} responds",
        result["success"],
        result.get("error", ""),
    )
    if result["success"]:
        print(f"       Response: {result['response'][:80]}")
        print(f"       Duration: {result['duration_s']}s")
else:
    print(f"  {WARN}: {HERMES_REASONING_MODEL} not loaded — skipping live test")
    print(f"          Pull it on Netcup: ollama pull {HERMES_REASONING_MODEL}")
    tests_warned += 1

# ── Test 5: Fallback behavior ─────────────────────────────────────────────────

print("\n[5] Fallback: qwen3:8b unavailable → llama3.2:3b")
result = call_with_fallback(
    prompt="Reply with exactly: FALLBACK_OK",
    primary_model="qwen3:nonexistent-model",     # guaranteed to fail
    fallback_model=HERMES_DEFAULT_MODEL,
    timeout=45,
)
check(
    "Fallback to default model when primary fails",
    result["success"] and result.get("fallback_used", False),
    result.get("error") or "fallback_used not set",
)
if result["success"]:
    print(f"       Fallback model used: {result['model']}")
    print(f"       Fallback reason: {result.get('fallback_reason', 'n/a')[:80]}")

# ── Test 6: Model router intent mapping ───────────────────────────────────────

print("\n[6] Model router intent → model class mapping")

routing_cases = [
    ("health_check",              "deterministic"),
    ("worker_status",             "deterministic"),
    ("queue_status",              "deterministic"),
    ("trading_lab_status",        "deterministic"),
    ("communication_health",      "deterministic"),
    ("summarize_recent_activity", "reasoning"),
    ("next_best_move",            "reasoning"),
    ("pilot_readiness",           "reasoning"),
    ("task_brief_generation",     "reasoning"),
    ("code_task",                 "codex_cli"),
    ("code_review",               "codex_cli"),
]

for intent, expected_class in routing_cases:
    got = model_class_for(intent)
    check(f"{intent} → {expected_class}", got == expected_class, f"got: {got}")

# ── Test 7: AI synthesis for reasoning intent ─────────────────────────────────

print("\n[7] AI synthesis: next_best_move")
if default_loaded:
    synth = synthesize(
        intent="next_best_move",
        evidence=[
            "3 leads overdue for followup",
            "1 approval pending >6h",
            "Queue depth: 4 signals pending",
        ],
        context="Operator asking: what is the next best move?",
        timeout=90,
    )
    check(
        "synthesize() returns a recommendation",
        bool(synth.get("recommendation")),
        synth.get("error") or "no recommendation returned",
    )
    if synth.get("recommendation"):
        print(f"       Model used: {synth['model']}")
        print(f"       Fallback:   {synth['fallback_used']}")
        print(f"       Duration:   {synth['duration_s']}s")
        print(f"       Preview:    {synth['recommendation'][:200]}")
else:
    print(f"  {WARN}: Skipping AI synthesis test — no model loaded")
    tests_warned += 1

# ── Test 8: CLI command routing (end-to-end) ──────────────────────────────────

print("\n[8] End-to-end: CLI command routed through model router")
try:
    from hermes_command_router.router import run_command
    report = run_command(
        "use qwen to review this system status: backend health is green, "
        "queue depth is 3, one worker is delayed. Give recommendation.",
        source="cli",
        sender="test",
    )
    has_report_header = "HERMES REPORT" in report or "Status:" in report
    has_model_note    = "Model:" in report or "deterministic" in report or "qwen" in report.lower()
    check("CLI command produces Hermes Report", has_report_header, report[:150])
    check("Report includes model attribution", has_model_note, report[:150])
    if has_report_header:
        print(f"\n       --- Report preview ---")
        for line in report.splitlines()[:12]:
            print(f"       {line}")
        print(f"       ...")
except Exception as e:
    check("CLI command end-to-end", False, str(e))

# ── Summary ────────────────────────────────────────────────────────────────────

print(f"\n{'='*56}")
print(f"  Ollama model router: {tests_passed}/{tests_run} passed, {tests_warned} warnings")
if tests_passed == tests_run:
    print("  All tests passed.")
elif tests_passed + tests_warned == tests_run:
    print("  Tests passed with warnings (non-critical).")
else:
    failed = tests_run - tests_passed - tests_warned
    print(f"  {failed} test(s) FAILED — see above.")
print(f"{'='*56}\n")

sys.exit(0 if (tests_run - tests_passed - tests_warned) == 0 else 1)
