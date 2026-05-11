# Model Router Auth-Login Provider Correction

**Date:** 2026-05-11  
**Pass:** NEXUS MODEL ROUTER AUTH-LOGIN PROVIDER CORRECTION PASS  
**Status:** Complete ✅

---

## What Changed

The model router was refactored to explicitly separate **auth-login providers**
(subscription tools Raymond already pays a flat fee for) from **paid API providers**
(metered per-call billing that requires explicit enablement).

### Before

All providers were treated as "API key" providers. `openclaw` and `claude` existed
but were treated as standard API callers. There was no `access_type` distinction.
ChatGPT and Claude were gated only on API key presence.

### After

Eleven named providers across four access types:

| Provider ID | Display Name | Access Type | Cost Tier | Key Required |
|---|---|---|---|---|
| `chatgpt_auth_openclaw` | ChatGPT auth-login via OpenClaw | auth_login | included | No |
| `claude_auth_cli` | Claude Code auth-login (claude CLI) | auth_login | included | No |
| `hermes_local` | Hermes local gateway | local | free | No |
| `netcup_ollama` | Netcup Ollama (SSH tunnel) | remote_local | free | No |
| `oracle_ollama` | Oracle ARM Ollama (direct) | remote_local | free | No |
| `groq_api` | Groq API | api_key | low | Yes |
| `nvidia_nim` | Nvidia NIM API | api_key | low | Yes |
| `openrouter_api` | OpenRouter API | api_key | medium | Yes |
| `gemini_api` | Gemini API | api_key | medium | Yes |
| `openai_api` | OpenAI API (paid) | api_key | high | Yes + `OPENAI_API_ENABLED=true` |
| `anthropic_api` | Anthropic API (paid) | api_key | high | Yes + `ANTHROPIC_API_ENABLED=true` |

---

## Key Safety Rules Now Enforced

- `openai_api` — skipped unless `OPENAI_API_KEY` is set **AND** `OPENAI_API_ENABLED=true`
  (defaults to false — never accidentally bills OpenAI account)
- `anthropic_api` — skipped unless `ANTHROPIC_API_KEY` is set **AND** `ANTHROPIC_API_ENABLED=true`
  (defaults to false — never accidentally bills Anthropic account)
- `chatgpt_auth_openclaw` — selected freely, no `OPENAI_API_KEY` needed, uses OpenClaw session proxy
- `claude_auth_cli` — selected freely, no `ANTHROPIC_API_KEY` needed, detected via `shutil.which("claude")`

---

## Files Modified

| File | Change |
|---|---|
| `lib/model_router.py` | Complete rewrite with new provider registry, `_build_providers()`, `_chains(providers)`, `provider_status_report()` |
| `lib/nexus_model_caller.py` | Added `_call_cli_subprocess()` for `claude_auth_cli` format; added `import subprocess, shutil` |
| `scripts/test_nexus_model_routing.py` | Updated all provider name refs; added 24 new tests (72 total, 72 pass) |
| `scripts/test_hermes_model_router.py` | Fixed `"groq"` → `"groq_api"` reference |

---

## New Provider Metadata Fields

Every provider dict now carries:

```python
{
    "provider_id":             str,   # e.g. "chatgpt_auth_openclaw"
    "display_name":            str,   # human-readable
    "access_type":             str,   # "auth_login" | "local" | "remote_local" | "api_key"
    "cost_tier":               str,   # "included" | "free" | "low" | "medium" | "high"
    "requires_api_key":        bool,
    "requires_login_session":  bool,
    "requires_local_service":  bool,
    "preferred_for":           list[str],
    "fallback_rank":           int,
    "rate_limit_type":         str,   # "subscription" | "local_capacity" | "api_quota"
}
```

---

## Test Results

```
Model routing: 72/72 tests passed
```

New test coverage added:
- Auth-login providers present with `access_type=auth_login`, `cost_tier=included`, `requires_api_key=False`
- `chatgpt_auth_openclaw` works without `OPENAI_API_KEY`
- `claude_auth_cli` works without `ANTHROPIC_API_KEY`
- `openai_api` not selected when key absent
- `anthropic_api` not selected when key absent
- No paid API selected in auto mode for `draft`, `cheap`, `telegram_reply` without config
- `provider_status_report()` separates auth-login from API providers
- Coding chain: `openai_api` position is after `chatgpt_auth_openclaw`
- Rate limiter keys updated to `groq_api` (not `groq`)

---

## Routing Priority Order (Auth-Login First)

```
telegram_reply:   chatgpt_auth_openclaw → netcup_ollama → oracle_ollama → groq_api → openrouter_api
coding:           claude_auth_cli → openrouter_api → chatgpt_auth_openclaw → openai_api (if enabled)
cheap/summary:    netcup_ollama → oracle_ollama → chatgpt_auth_openclaw → groq_api
reason/planning:  hermes_local → chatgpt_auth_openclaw → claude_auth_cli → openrouter_api
critical:         claude_auth_cli → openrouter_api → hermes_local → anthropic_api (if enabled)
```

Paid APIs (`openai_api`, `anthropic_api`) appear last in all chains and are skipped by default.
