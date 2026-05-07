# Hermes Ollama + Qwen3 Setup

Hermes uses two models on the Netcup server via SSH tunnel:

| Role | Model | Used for |
|------|-------|----------|
| Default / routing | `llama3.2:3b` | Status checks, routing decisions |
| Reasoning | `qwen3:8b` | Summaries, recommendations, pilot readiness |
| Code | `codex_cli` | Task briefs only — Hermes never writes code |

---

## Netcup server setup

SSH in:
```bash
ssh root@YOUR_NETCUP_IP
```

Pull both models:
```bash
ollama pull llama3.2:3b
ollama pull qwen3:8b
ollama list
```

Verify each responds:
```bash
curl http://localhost:11434/api/generate \
  -d '{"model":"llama3.2:3b","prompt":"Say DEFAULT_OK","stream":false}'

curl http://localhost:11434/api/generate \
  -d '{"model":"qwen3:8b","prompt":"Say REASONING_OK","stream":false}'
```

Expected: `"response":"DEFAULT_OK"` and `"response":"REASONING_OK"` (or similar).

---

## Mac mini SSH tunnel

Open the tunnel (keep this running in a tmux pane or add to launchd):
```bash
ssh -N -L 11555:localhost:11434 root@YOUR_NETCUP_IP
```

Verify the tunnel works:
```bash
curl http://localhost:11555/api/generate \
  -d '{"model":"llama3.2:3b","prompt":"Say TUNNEL_OK","stream":false}'

curl http://localhost:11555/api/generate \
  -d '{"model":"qwen3:8b","prompt":"Say QWEN_OK","stream":false}'
```

---

## Environment variables

Add to `/Users/raymonddavis/nexus-ai/.env`:

```bash
# Base URL (no trailing path) — points to SSH tunnel on Mac mini
OLLAMA_BASE_URL=http://localhost:11555

# Lightweight model for status checks and routing
HERMES_DEFAULT_MODEL=llama3.2:3b
HERMES_ROUTING_MODEL=llama3.2:3b

# Hard-reasoning model for summaries and recommendations
HERMES_REASONING_MODEL=qwen3:8b

# Code agent — Hermes generates briefs for Codex, never writes code itself
HERMES_CODE_AGENT=codex_cli
```

---

## How Hermes decides which model to use

`lib/hermes_model_router.py` maps every intent to a model class:

| Intent | Model class | Model |
|--------|-------------|-------|
| `health_check` | deterministic | (no AI) |
| `worker_status` | deterministic | (no AI) |
| `queue_status` | deterministic | (no AI) |
| `trading_lab_status` | deterministic | (no AI) |
| `communication_health` | deterministic | (no AI) |
| `summarize_recent_activity` | reasoning | `qwen3:8b` |
| `next_best_move` | reasoning | `qwen3:8b` |
| `pilot_readiness` | reasoning | `qwen3:8b` |
| `task_brief_generation` | reasoning | `qwen3:8b` |
| `code_task` | codex_cli | task brief only |
| `code_review` | codex_cli | task brief only |

**Fallback chain:** If `qwen3:8b` is unreachable or returns empty, Hermes retries with `llama3.2:3b` and marks the report with `⚠️` and a warning note.

---

## Testing

Run the full model router health check:
```bash
cd /Users/raymonddavis/nexus-ai
python3 scripts/test_ollama_model_router.py
```

Test a specific model directly:
```bash
python3 -m lib.hermes_ollama_client llama3.2:3b
python3 -m lib.hermes_ollama_client qwen3:8b
```

Test the CLI command routing:
```bash
python3 -m hermes_command_router \
  "use qwen to review this system status: backend health is green, queue depth is 3, one worker is delayed. Give recommendation."
```

---

## Fallback behavior

If `qwen3:8b` is unavailable:
- Hermes retries with `llama3.2:3b`
- Report status is set to `warning`
- Evidence includes: `"Model: llama3.2:3b (fallback — primary model qwen3:8b unavailable: ...)"`
- Hermes does **not** crash

If both models are unavailable (tunnel down):
- Report includes: `"[AI synthesis unavailable — Connection failed. Deterministic data shown above.]"`
- Deterministic evidence (from Supabase) is still returned
- Hermes does **not** crash

---

## Security notes

- Ollama is **not** exposed publicly — only accessible through the SSH tunnel
- No API keys or tokens are logged
- Model names are logged, not prompts or responses (prompts may contain business context)
- The Netcup server IP is never hardcoded — stored in SSH config or passed at tunnel open time

---

## Risks / limitations

| Risk | Mitigation |
|------|-----------|
| SSH tunnel drops | Restart tunnel; Hermes falls back to deterministic reports |
| qwen3:8b cold start is slow (~10–30s) | `call_with_fallback()` has 90s timeout |
| qwen3:8b may include `<think>` tags in output | Strip with post-processing if needed |
| Netcup server reboots | Ollama auto-starts if configured; tunnel needs manual restart |

---

## Recommended next steps

1. Pull `qwen3:8b` on Netcup: `ollama pull qwen3:8b`
2. Open SSH tunnel on Mac mini
3. Run `python3 scripts/test_ollama_model_router.py`
4. Add tunnel to launchd for auto-reconnect on Mac mini reboot
5. Test via Telegram: send "what is the next best move?" to Hermes
