# system-design-101 — Nexus Reference Notes (summary, not raw ingestion)

Reference repo (ByteByteGo, known) for architecture literacy. Summary only — do NOT
inject the full repo into prompts. Key ideas relevant to Nexus:

- **Idempotency & retries**: every writer (research runner, intake, scanner) should be
  safe to re-run — Nexus already applies this (upsert + dedupe).
- **Queue + worker**: decouple producers (research/intake) from consumers (review/bridge)
  via tables (`source_extractions`, `worker_recommendations`, `owner_approval_queue`).
- **Approval gates / human-in-the-loop**: external/irreversible actions go through an
  approval queue before an executor — Nexus enforces this (executor disabled by default).
- **Caching & cost tiers**: route cheap-first (local Ollama) and cache results — see
  `nexus_headroom_status.py`.
- **Observability**: status files + audit events (`status.json`, `nexus_os_approval_events`).
- **Least privilege / RLS**: admin-only policies on every nexus_os_* table.

Usage for Hermes: cite these principles when reasoning about architecture; summarize, never dump.
