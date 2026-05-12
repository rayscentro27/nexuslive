# AI Provider Dashboard
**Date:** 2026-05-12  
**Mode:** Operational reference — live status derived from env config and known topology

---

## Provider Route Map

```
┌─────────────────────────────────────────────────────────┐
│                  NEXUS AI PROVIDER ROUTES                │
├─────────────────┬──────────────────┬────────────────────┤
│ PROVIDER        │ ENDPOINT         │ STATUS             │
├─────────────────┼──────────────────┼────────────────────┤
│ OpenRouter      │ openrouter.ai    │ ✅ Primary (conf.)  │
│ deepseek-chat   │ REST API         │ Telegram replies   │
├─────────────────┼──────────────────┼────────────────────┤
│ Hermes/Ollama   │ 127.0.0.1:8642   │ ⚠️ Tunnel req.     │
│ qwen3:8b        │ Local Mac Mini   │ Down if no tunnel  │
├─────────────────┼──────────────────┼────────────────────┤
│ Oracle Ollama   │ 161.153.40.41    │ ⚠️ Unreliable      │
│ qwen2.5:14b     │ Oracle VM        │ 100% pkt loss when │
│                 │                  │ unreachable        │
├─────────────────┼──────────────────┼────────────────────┤
│ Claude Code CLI │ Local CLI        │ ✅ Code tasks only  │
│ claude-sonnet   │ Anthropic API    │ Not conversational │
├─────────────────┼──────────────────┼────────────────────┤
│ OpenClaw        │ ChatGPT routing  │ 🔵 When enabled    │
│                 │ OPENCLAW_ENABLED │ Flag-controlled    │
└─────────────────┴──────────────────┴────────────────────┘
```

---

## Current Config (from env)

| Variable | Value | Effect |
|---|---|---|
| `OPENROUTER_API_KEY` | Set ✅ | OpenRouter active |
| `OPENROUTER_MODEL` | `deepseek/deepseek-chat` | Default conversational model |
| `HERMES_GATEWAY_URL` | `http://127.0.0.1:8642` | Local Ollama via tunnel |
| `HERMES_REASONING_MODEL` | `qwen3:8b` | Ollama primary model |
| `OPENCLAW_ENABLED` | Not set / false | ChatGPT routing inactive |

---

## Fallback Order

```
User query → try_internal_first() [<100ms, no API call]
    ↓ no match
OpenRouter (deepseek-chat) [2-4s, most reliable]
    ↓ fail / rate limit
Hermes local Ollama (qwen3:8b) [requires tunnel]
    ↓ fail / unreachable
Oracle VM Ollama (qwen2.5:14b) [unreliable]
    ↓ all fail
[No graceful fallback message — gap]
```

---

## Operational Notes

### OpenRouter (Primary)
- Most reliable path for Telegram conversational replies
- Rate limits: check openrouter.ai/activity for daily usage
- Model quality: deepseek-chat is strong for operational Q&A
- Latency: 2-4s typical, up to 10s under load
- **Best for:** All Telegram conversations, operator queries, report summaries

### Hermes Local Ollama
- Requires SSH tunnel to Mac Mini to be active
- If tunnel is down, this path is unreachable
- Start tunnel: `ssh -L 8642:localhost:11434 mac-mini`
- Check status: `curl http://127.0.0.1:8642/api/tags`
- **Best for:** Long reasoning tasks, code explanation, strategy analysis

### Oracle VM Ollama
- IP: 161.153.40.41 (fixed)
- SSH key: `~/.ssh/oracle_vm`
- Known issue: periodic 100% packet loss — "frequently unreachable"
- Model: qwen2.5:14b (larger, better for complex tasks)
- **Best for:** When Mac Mini tunnel not available and Oracle is up

### Claude Code CLI
- Available as `claude` in terminal
- Fastest path for code review, edits, and implementation tasks
- Not wired to Telegram (intentional — code tasks should be human-initiated)
- **Best for:** All implementation work in this project

---

## Status Check Commands

```bash
# Check OpenRouter balance/usage
curl -s https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" | jq '.data.usage'

# Check local Ollama
curl -s http://127.0.0.1:8642/api/tags | jq '.models[].name'

# Check Oracle Ollama
curl -s --connect-timeout 5 http://161.153.40.41:11434/api/tags | jq '.models[].name'

# Check hermes gateway
curl -s http://127.0.0.1:8642/health
```

---

## Telegram Query: "which ai providers are available"

Hermes response (from `hermes_internal_first.py → ai_providers` topic):
- Lists all known routes with configured/missing status
- Reports best current fallback
- Directs to `/models` for live Ollama check

This response is generated from env config + known topology — it reflects config state, not live network reachability. For live check, run `/models` in Telegram or the status commands above.

---

## Incident Response: All Providers Down

If all AI providers are unreachable:
1. Verify OpenRouter API key is set: `echo $OPENROUTER_API_KEY | head -c 10`
2. Check OpenRouter status at openrouter.ai
3. Start local Ollama tunnel if Mac Mini is available
4. Use Claude Code CLI directly for urgent code tasks
5. For Telegram: manually respond via Telegram app while Hermes is offline
6. Check hermes gateway service: `launchctl list | grep hermes`
