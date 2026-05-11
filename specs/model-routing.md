# Model Routing Spec

## Purpose
Define safe, capability-based routing across multiple model providers with strict minimum-context checks and graceful fallback behavior.

## Target Model Classes
- `premium_reasoning`
- `funding_strategy`
- `credit_analysis`
- `cheap_summary`
- `telegram_reply`
- `coding_assistant`
- `research_worker`

## Capability Expectations
- `premium_reasoning`: high-reliability synthesis, long context, executive decisions.
- `funding_strategy`: deeper scoring/recommendation analysis; avoid low-context models.
- `credit_analysis`: credit-readiness reasoning; explainable outputs preferred.
- `cheap_summary`: low-cost summarization and formatting.
- `telegram_reply`: concise conversational response with bounded context.
- `coding_assistant`: route out to coding tools (Codex/Claude Code), not Hermes freeform codegen.
- `research_worker`: long-context extraction and multi-document synthesis.

## Provider Lanes (Vision)
- **OpenRouter**: premium remote lane and primary long-context fallback.
- **Gemini**: large-context planning/research lane.
- **Netcup/Ollama**: cheap local lane for summaries/background tasks.
- **Groq/NVIDIA/etc.**: latency-oriented lane for selective classes.

## Safety Rules
- Enforce minimum context for classes handling strategic/operator-critical work.
- Do not allow infinite retries.
- Fail fast for invalid credentials/configuration errors.
- On repeated provider failures, trip suppression/circuit behavior and avoid alert spam.

## Example Task Mappings
- `funding_strategy` -> `premium_reasoning`
- `telegram_reply` -> `cheap_summary` (or premium fallback when needed)
- `credit_analysis` -> `premium_reasoning`
- `coding_assistant` -> external coding tools
- `research_worker` -> long-context lane

## Logging Requirements
- Log provider selected, model, context budget, and fallback path.
- Do not log raw secrets or full sensitive prompts.

## Integration Scope (Current Phase)
- Additive improvements to router module only.
- No broad rewiring of all workflows in one step.
