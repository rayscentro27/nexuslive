#!/usr/bin/env python3
"""
test_nexus_model_routing.py — Validates the full Nexus model routing stack.

Tests:
  - Provider selection per task type
  - OpenClaw is in the routing chain
  - ChatGPT/OpenAI is in the routing chain
  - Cost tier is present on every provider
  - Rate limit guard skips over-limit provider
  - model_source shortcuts work
  - nexus_model_caller returns correct structure
  - Netcup Ollama vs Oracle ARM routing paths
  - Caller error handling (malformed URL)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_pass = 0
_fail = 0


def _check(label: str, cond: bool, detail: str = "") -> bool:
    global _pass, _fail
    ok = "PASS" if cond else "FAIL"
    print(f"[{ok}] {label}" + (f" — {detail}" if detail else ""))
    if cond:
        _pass += 1
    else:
        _fail += 1
    return cond


# ── Set up safe test environment ───────────────────────────────────────────────

os.environ.update({
    "HERMES_FALLBACK_ENABLED": "true",
    "OPENCLAW_ENABLED":         "true",
    "OPENCLAW_URL":             "http://localhost:18789",
    "OPENCLAW_AUTH_TOKEN":      "test-token",
    "OPENCLAW_MODEL":           "nousresearch/hermes-4-70b",
    "OPENROUTER_API_KEY":       "sk-or-test-key",
    "OPENROUTER_CTX":           "128000",
    "GROQ_CTX":                 "10000",
    "GROQ_API_KEY":             "test-groq-key",
    "OPENAI_API_KEY":           "",          # not configured — ChatGPT should be skipped in auto mode
    "HERMES_MIN_CONTEXT_MAIN":  "0",         # disable min-context enforcement for tests
})


def main() -> int:
    from lib.model_router import (
        get_provider, provider_summary, routing_preview,
        ModelRoutingError, _rate_limiter,
    )
    from lib.nexus_model_caller import call as nexus_call

    # ── 1. Provider summary includes all expected providers ────────────────────
    names = {p["name"] for p in provider_summary()}
    _check("provider_summary includes hermes",        "hermes"        in names)
    _check("provider_summary includes netcup_ollama", "netcup_ollama" in names)
    _check("provider_summary includes oracle_ollama", "oracle_ollama" in names)
    _check("provider_summary includes openclaw",      "openclaw"      in names)
    _check("provider_summary includes groq",          "groq"          in names)
    _check("provider_summary includes openrouter",    "openrouter"    in names)
    _check("provider_summary includes gemini",        "gemini"        in names)
    _check("provider_summary includes chatgpt",       "chatgpt"       in names)
    _check("provider_summary includes claude",        "claude"        in names)

    # ── 2. Every provider has a cost_tier field ────────────────────────────────
    for p in provider_summary():
        _check(
            f"provider {p['name']} has cost_tier",
            p.get("cost_tier") in {"free", "low", "medium", "high"},
            str(p.get("cost_tier")),
        )

    # ── 3. Local providers classified as free ─────────────────────────────────
    for p in provider_summary():
        if p["name"] in ("hermes", "netcup_ollama", "oracle_ollama", "openclaw"):
            _check(f"{p['name']} is cost_tier=free", p["cost_tier"] == "free")

    # ── 4. ChatGPT classified as high ────────────────────────────────────────
    chatgpt_entry = next((p for p in provider_summary() if p["name"] == "chatgpt"), None)
    _check("chatgpt cost_tier=high", chatgpt_entry is not None and chatgpt_entry["cost_tier"] == "high")

    # ── 5. OpenClaw is in the coding chain ────────────────────────────────────
    preview_coding = routing_preview("coding")
    # OpenClaw should be in coding chain — if openrouter has key it wins, openclaw is next
    from lib.model_router import _chains
    coding_names = [p["name"] for p in _chains()["coding"]]
    _check("openclaw appears in coding chain",   "openclaw" in coding_names)
    _check("chatgpt appears in coding chain",    "chatgpt"  in coding_names)
    _check("openrouter appears in coding chain", "openrouter" in coding_names)

    # ── 6. Telegram reply chain uses openclaw first ────────────────────────────
    tg_names = [p["name"] for p in _chains()["telegram_reply"]]
    _check("telegram_reply chain has openclaw first", tg_names[0] == "openclaw")

    # ── 7. model_source=openclaw shortcut returns openclaw provider ───────────
    p_oc = get_provider(model_source="openclaw")
    _check("model_source=openclaw name",   p_oc["name"]      == "openclaw")
    _check("model_source=openclaw format", p_oc["format"]    == "openai")
    _check("model_source=openclaw cost",   p_oc["cost_tier"] == "free")

    # ── 8. model_source=hermes shortcut ───────────────────────────────────────
    p_h = get_provider(model_source="hermes")
    _check("model_source=hermes name",     p_h["name"]      == "hermes")
    _check("model_source=hermes cost",     p_h["cost_tier"] == "free")

    # ── 9. model_source=netcup_ollama shortcut ────────────────────────────────
    p_nc = get_provider(model_source="netcup_ollama")
    _check("model_source=netcup_ollama name",   p_nc["name"]   == "netcup_ollama")
    _check("model_source=netcup_ollama format", p_nc["format"] == "ollama_generate")

    # ── 10. model_source=chatgpt skipped when no OPENAI_API_KEY ───────────────
    os.environ["OPENAI_API_KEY"] = ""
    p_fallback = get_provider(model_source="chatgpt", task_type="draft")
    # When chatgpt key absent, shortcut falls through to auto — result is not chatgpt
    _check(
        "chatgpt shortcut falls to auto when no key",
        p_fallback["name"] != "chatgpt",
        f"got {p_fallback['name']}",
    )

    # ── 11. Rate limiter skips over-limit provider ────────────────────────────
    # Inject enough calls to hit groq limit (25 per 60s in test config)
    for _ in range(26):
        _rate_limiter.record("groq")
    _check("groq is_limited after 26 calls", _rate_limiter.is_limited("groq"))

    # cheap chain — groq should now be skipped
    p_after_limit = get_provider(task_type="cheap")
    _check(
        "get_provider skips rate-limited groq",
        p_after_limit["name"] != "groq",
        f"got {p_after_limit['name']}",
    )

    # Reset groq window
    _rate_limiter._windows["groq"].clear()

    # ── 12. context constraint respected ──────────────────────────────────────
    os.environ["HERMES_MIN_CONTEXT_MAIN"] = "64000"  # re-enable for this test
    try:
        get_provider(task_type="critical", min_context=9999999)
        _check("over-constrained critical raises ModelRoutingError", False, "expected error")
    except ModelRoutingError:
        _check("over-constrained critical raises ModelRoutingError", True)
    os.environ["HERMES_MIN_CONTEXT_MAIN"] = "0"

    # ── 13. nexus_model_caller returns correct shape on real provider ─────────
    # We can't make a live call in tests, but we can test the failure path shape
    # by pointing at a dead endpoint
    os.environ["OPENCLAW_URL"] = "http://127.0.0.1:1"   # dead port
    os.environ["OPENROUTER_API_KEY"] = ""
    os.environ["GROQ_API_KEY"] = ""
    os.environ["OPENAI_API_KEY"] = ""
    os.environ["ANTHROPIC_API_KEY"] = ""
    os.environ["GEMINI_API_KEY_1"] = ""

    result = nexus_call("test", task_type="cheap", timeout=1)
    _check("caller returns dict",               isinstance(result, dict))
    _check("caller has success field",          "success"    in result)
    _check("caller has provider field",         "provider"   in result)
    _check("caller has model field",            "model"      in result)
    _check("caller has cost_tier field",        "cost_tier"  in result)
    _check("caller has duration_s field",       "duration_s" in result)
    _check("caller has fallback_used field",    "fallback_used" in result)
    _check("caller has error field",            "error"      in result)
    _check("caller success=False on dead port", result["success"] is False)

    print()
    total = _pass + _fail
    print(f"Model routing: {_pass}/{total} tests passed")
    if _fail:
        print(f"  {_fail} FAILED")
    return 0 if _fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
