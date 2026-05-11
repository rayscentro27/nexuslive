#!/usr/bin/env python3
"""
test_nexus_model_routing.py — Validates the full Nexus model routing stack.

Tests:
  - Provider selection per task type
  - Auth-login providers (chatgpt_auth_openclaw, claude_auth_cli) in routing chains
  - API providers skipped when not configured / enabled
  - Cost tier and access_type on every provider
  - Rate limit guard skips over-limit provider
  - model_source shortcuts work (including legacy aliases)
  - nexus_model_caller returns correct structure
  - Netcup Ollama vs Oracle ARM routing paths
  - Caller error handling (dead URL)
  - provider_status_report separates auth-login from API providers
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
    "HERMES_FALLBACK_ENABLED":  "true",
    "OPENCLAW_ENABLED":         "true",
    "OPENCLAW_URL":             "http://localhost:18789",
    "OPENCLAW_AUTH_TOKEN":      "test-token",
    "OPENCLAW_MODEL":           "nousresearch/hermes-4-70b",
    "OPENROUTER_API_KEY":       "sk-or-test-key",
    "OPENROUTER_CTX":           "128000",
    "GROQ_CTX":                 "10000",
    "GROQ_API_KEY":             "test-groq-key",
    "OPENAI_API_KEY":           "",       # not configured
    "OPENAI_API_ENABLED":       "false",  # paid API disabled by default
    "ANTHROPIC_API_KEY":        "",       # not configured
    "ANTHROPIC_API_ENABLED":    "false",  # paid API disabled by default
    "HERMES_MIN_CONTEXT_MAIN":  "0",      # disable min-context enforcement for tests
})


def main() -> int:
    from lib.model_router import (
        get_provider, provider_summary, routing_preview,
        ModelRoutingError, _rate_limiter, _build_providers, _chains,
        provider_status_report,
    )
    from lib.nexus_model_caller import call as nexus_call

    # ── 1. Provider summary includes all expected providers ────────────────────
    names = {p["name"] for p in provider_summary()}
    _check("provider_summary includes hermes_local",          "hermes_local"          in names)
    _check("provider_summary includes netcup_ollama",         "netcup_ollama"         in names)
    _check("provider_summary includes oracle_ollama",         "oracle_ollama"         in names)
    _check("provider_summary includes chatgpt_auth_openclaw", "chatgpt_auth_openclaw" in names)
    _check("provider_summary includes groq_api",              "groq_api"              in names)
    _check("provider_summary includes openrouter_api",        "openrouter_api"        in names)
    _check("provider_summary includes gemini_api",            "gemini_api"            in names)
    _check("provider_summary includes openai_api",            "openai_api"            in names)
    _check("provider_summary includes anthropic_api",         "anthropic_api"         in names)
    _check("provider_summary includes claude_auth_cli",       "claude_auth_cli"       in names)
    _check("provider_summary includes nvidia_nim",            "nvidia_nim"            in names)

    # ── 2. Every provider has a cost_tier field ────────────────────────────────
    valid_tiers = {"free", "low", "medium", "high", "included"}
    for p in provider_summary():
        _check(
            f"provider {p['name']} has cost_tier",
            p.get("cost_tier") in valid_tiers,
            str(p.get("cost_tier")),
        )

    # ── 3. Local providers classified as free ────────────────────────────────
    for p in provider_summary():
        if p["name"] in ("hermes_local", "netcup_ollama", "oracle_ollama"):
            _check(f"{p['name']} is cost_tier=free", p["cost_tier"] == "free")

    # ── 4. Auth-login providers classified as included ───────────────────────
    for p in provider_summary():
        if p["name"] in ("chatgpt_auth_openclaw", "claude_auth_cli"):
            _check(f"{p['name']} is cost_tier=included",      p["cost_tier"]          == "included")
            _check(f"{p['name']} access_type=auth_login",     p.get("access_type")    == "auth_login")
            _check(f"{p['name']} requires_api_key=False",     p.get("requires_api_key") is False)

    # ── 5. OpenAI API and Anthropic API classified as high ───────────────────
    for expected_name in ("openai_api", "anthropic_api"):
        entry = next((p for p in provider_summary() if p["name"] == expected_name), None)
        _check(f"{expected_name} cost_tier=high",
               entry is not None and entry["cost_tier"] == "high")

    # ── 6. chatgpt_auth_openclaw is in the coding chain ─────────────────────
    providers = _build_providers()
    coding_names = [p["name"] for p in _chains(providers)["coding"]]
    _check("chatgpt_auth_openclaw appears in coding chain",  "chatgpt_auth_openclaw" in coding_names)
    _check("claude_auth_cli appears in coding chain",        "claude_auth_cli"       in coding_names)
    _check("openrouter_api appears in coding chain",         "openrouter_api"        in coding_names)

    # High-cost openai_api must come AFTER auth-login in coding chain
    if "openai_api" in coding_names and "chatgpt_auth_openclaw" in coding_names:
        _check("openai_api comes after chatgpt_auth_openclaw in coding chain",
               coding_names.index("openai_api") > coding_names.index("chatgpt_auth_openclaw"))

    # ── 7. Telegram reply chain uses chatgpt_auth_openclaw first ─────────────
    tg_names = [p["name"] for p in _chains(providers)["telegram_reply"]]
    _check("telegram_reply chain has chatgpt_auth_openclaw first",
           tg_names[0] == "chatgpt_auth_openclaw")

    # ── 8. model_source=chatgpt_auth_openclaw shortcut ───────────────────────
    p_oc = get_provider(model_source="chatgpt_auth_openclaw")
    _check("model_source=chatgpt_auth_openclaw name",     p_oc["name"]        == "chatgpt_auth_openclaw")
    _check("model_source=chatgpt_auth_openclaw format",   p_oc["format"]      == "openai")
    _check("model_source=chatgpt_auth_openclaw cost",     p_oc["cost_tier"]   == "included")
    _check("model_source=chatgpt_auth_openclaw access",   p_oc["access_type"] == "auth_login")

    # ── 9. model_source=openclaw legacy alias resolves correctly ─────────────
    p_oc2 = get_provider(model_source="openclaw")
    _check("model_source=openclaw alias → chatgpt_auth_openclaw",
           p_oc2["name"] == "chatgpt_auth_openclaw")

    # ── 10. model_source=hermes + hermes_local shortcuts ─────────────────────
    p_h = get_provider(model_source="hermes_local")
    _check("model_source=hermes_local name",  p_h["name"]      == "hermes_local")
    _check("model_source=hermes_local cost",  p_h["cost_tier"] == "free")

    p_h2 = get_provider(model_source="hermes")
    _check("model_source=hermes alias → hermes_local", p_h2["name"] == "hermes_local")

    # ── 11. model_source=netcup_ollama shortcut ───────────────────────────────
    p_nc = get_provider(model_source="netcup_ollama")
    _check("model_source=netcup_ollama name",   p_nc["name"]   == "netcup_ollama")
    _check("model_source=netcup_ollama format", p_nc["format"] == "ollama_generate")

    # ── 12. chatgpt alias falls to auto when OPENAI_API_ENABLED=false ────────
    os.environ["OPENAI_API_KEY"]    = ""
    os.environ["OPENAI_API_ENABLED"] = "false"
    p_fallback = get_provider(model_source="chatgpt", task_type="draft")
    _check(
        "chatgpt alias falls to auto when OPENAI_API_ENABLED=false",
        p_fallback["name"] != "openai_api",
        f"got {p_fallback['name']}",
    )

    # ── 13. Auth providers work without paid API keys ─────────────────────────
    # chatgpt_auth_openclaw: no OPENAI_API_KEY needed — uses OpenClaw session proxy
    p_auth = get_provider(model_source="chatgpt_auth_openclaw")
    _check("chatgpt_auth_openclaw works without OPENAI_API_KEY",
           p_auth["name"] == "chatgpt_auth_openclaw" and not p_auth["requires_api_key"])

    # claude_auth_cli: no ANTHROPIC_API_KEY needed — uses claude CLI subscription
    import shutil as _shutil
    if _shutil.which("claude"):
        p_ca = get_provider(model_source="claude_auth_cli")
        _check("claude_auth_cli works without ANTHROPIC_API_KEY",
               p_ca["name"] == "claude_auth_cli" and not p_ca["requires_api_key"])
    else:
        print("[SKIP] claude_auth_cli direct test — CLI not found in PATH")

    # ── 14. openai_api skipped when OPENAI_API_KEY unset ─────────────────────
    os.environ["OPENAI_API_KEY"]    = ""
    os.environ["OPENAI_API_ENABLED"] = "false"
    p_coding = get_provider(task_type="coding")
    _check("openai_api not selected for coding when key absent",
           p_coding["name"] != "openai_api",
           f"got {p_coding['name']}")

    # ── 15. anthropic_api skipped when ANTHROPIC_API_KEY unset ───────────────
    os.environ["ANTHROPIC_API_KEY"]    = ""
    os.environ["ANTHROPIC_API_ENABLED"] = "false"
    p_critical = get_provider(task_type="critical")
    _check("anthropic_api not selected for critical when key absent",
           p_critical["name"] != "anthropic_api",
           f"got {p_critical['name']}")

    # ── 16. Paid API not selected in auto mode without explicit config ─────────
    os.environ["OPENAI_API_KEY"]       = ""
    os.environ["OPENAI_API_ENABLED"]   = "false"
    os.environ["ANTHROPIC_API_KEY"]    = ""
    os.environ["ANTHROPIC_API_ENABLED"] = "false"
    for task in ("draft", "cheap", "telegram_reply"):
        p_t = get_provider(task_type=task)
        _check(
            f"no paid API selected for {task} without config",
            p_t["cost_tier"] in ("free", "low", "included"),
            f"got {p_t['name']} ({p_t['cost_tier']})",
        )

    # ── 17. Rate limiter skips over-limit provider ────────────────────────────
    for _ in range(26):
        _rate_limiter.record("groq_api")
    _check("groq_api is_limited after 26 calls", _rate_limiter.is_limited("groq_api"))

    p_after_limit = get_provider(task_type="cheap")
    _check(
        "get_provider skips rate-limited groq_api",
        p_after_limit["name"] != "groq_api",
        f"got {p_after_limit['name']}",
    )

    _rate_limiter._windows["groq_api"].clear()

    # ── 18. context constraint respected ──────────────────────────────────────
    os.environ["HERMES_MIN_CONTEXT_MAIN"] = "64000"
    try:
        get_provider(task_type="critical", min_context=9999999)
        _check("over-constrained critical raises ModelRoutingError", False, "expected error")
    except ModelRoutingError:
        _check("over-constrained critical raises ModelRoutingError", True)
    os.environ["HERMES_MIN_CONTEXT_MAIN"] = "0"

    # ── 19. provider_status_report separates auth-login from API providers ────
    report = provider_status_report()
    _check("status report includes auth-login section",
           "auth-login" in report.lower() or "auth_login" in report.lower())
    _check("status report includes chatgpt_auth_openclaw",
           "chatgpt_auth_openclaw" in report)
    _check("status report includes claude_auth_cli",
           "claude_auth_cli" in report)
    _check("status report notes paid API disabled by default",
           "OPENAI_API_ENABLED" in report or "openai_api" in report.lower())

    # ── 20. nexus_model_caller returns correct shape on real provider ─────────
    os.environ["OPENCLAW_URL"]       = "http://127.0.0.1:1"   # dead port
    os.environ["OPENROUTER_API_KEY"] = ""
    os.environ["GROQ_API_KEY"]       = ""
    os.environ["OPENAI_API_KEY"]     = ""
    os.environ["ANTHROPIC_API_KEY"]  = ""
    os.environ["GEMINI_API_KEY_1"]   = ""

    result = nexus_call("test", task_type="cheap", timeout=1)
    _check("caller returns dict",               isinstance(result, dict))
    _check("caller has success field",          "success"       in result)
    _check("caller has provider field",         "provider"      in result)
    _check("caller has model field",            "model"         in result)
    _check("caller has cost_tier field",        "cost_tier"     in result)
    _check("caller has duration_s field",       "duration_s"    in result)
    _check("caller has fallback_used field",    "fallback_used" in result)
    _check("caller has error field",            "error"         in result)
    _check("caller success=False on dead port", result["success"] is False)

    print()
    total = _pass + _fail
    print(f"Model routing: {_pass}/{total} tests passed")
    if _fail:
        print(f"  {_fail} FAILED")
    return 0 if _fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
