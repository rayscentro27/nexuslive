# Hermes Capabilities (truthful)

- Read Ray profile: YES
- Read Operator Core (reports/operator/nexus_operator_status.json): YES (if generated)
- Read local Nexus reports: YES
- Search the web directly: **NO** (not connected from Hermes Mobile)
- Analyze a YouTube URL directly: **NO**
- Ingest YouTube transcript via Nexus pipeline: via TheChosenOne handoff (not direct)
- Create a TheChosenOne handoff: YES
- Execute commands directly: **NO** (unless explicitly wired)
- Send customer messages: **NO**
- Publish: **NO**  ·  Charge payments: **NO**  ·  Trade live: **NO**
- Read Oanda demo status (through Operator Core): YES
- Update local advisor notes/profile: YES (safe, local only)

If a capability is unknown at runtime, Hermes says "unknown" and names the missing data source.

## Local Ollama reasoning (v1 blend)
- Local Ollama blended into advisor path: **YES (wired)** — grounded with Ray profile + Operator Core + capability truth + recent conversation.
- Model: local non-cloud (`gemma3:1b` preferred, else `qwen2.5:0.5b`; `*-cloud` always skipped). Override via `HERMES_ADVISOR_MODEL`.
- Used for: casual, advisory, money advisory, operator interpretation, reflective/strategy. Kept deterministic for: capability_truth, research_request, execution_handoff (honesty/structure-critical).
- ⚠️ **Current performance blocker:** on this loaded CPU box, Ollama generation exceeds the interactive timeout (>15–70s), so the advisor **falls back to deterministic** and a 30-min circuit breaker skips Ollama to stay snappy. It will use Ollama automatically once the model responds within timeout (less-loaded box / warm model).
- Honesty guard: LLM output claiming web search / YouTube watch / execution is discarded → deterministic fallback. "paste to TheChosenOne" phrasing rewritten to a handoff offer.
- Web search: still **NO**. YouTube direct: still **NO** (handoff only). Execution routing: still **NO** (handoff only). No paid APIs (cloud models skipped).
