# Central Operational Snapshot API Integration

## Scope
- Endpoint: `GET /api/admin/ai-ops/status`
- Change type: additive, read-only diagnostics payload extension

## What was integrated
- Wired `build_central_operational_snapshot(...)` into `api_admin_ai_ops_status`.
- Snapshot builder now executes from server route using existing `rest_select` read function.
- Added top-level response field:
  - `central_operational_snapshot`

## Data included in snapshot
- `generated_at`, `read_only`
- `ingestion` (queue totals, status counts, source breakdown, pressure)
- `knowledge` (totals, status counts, recent learned items)
- `tickets` (total, status, department counts)
- `providers` (status rollup + latest rows)
- `opportunities` and `grants` (recent/top rows)
- `semantic_retrieval` (retrieval metrics + routing preview)
- `warnings` (lightweight diagnostics)

## Safety posture
- No writes introduced.
- No workflow triggers introduced.
- Uses existing admin auth guard for the parent endpoint.
- Snapshot generation is exception-safe via helper-level protected reads.

## Modified file
- `control_center/control_center_server.py`

## Verification guidance
- Call `GET /api/admin/ai-ops/status` and confirm `central_operational_snapshot` exists.
- Confirm existing fields (`model_config`, `telegram_mode`, `routing_preview`, etc.) remain unchanged.
