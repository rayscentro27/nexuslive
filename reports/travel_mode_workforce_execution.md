# Travel Mode Workforce Execution

## Status
- Phase B implemented with live operational state integration and stronger visual activity cues.

## Completed
- Updated `src/components/admin/workforce_state_adapter.ts`:
  - Added explicit departments for travel/demo operations:
    - Hermes Operations
    - Trading Intelligence
    - Funding Intelligence
    - Grant Research
    - Credit Intelligence
    - Business Opportunities
    - Marketing Intelligence
    - System Monitoring
  - Added queue pressure, scheduler failures, warning counts, grant counts, and demo-mode hints to state mapping.
- Updated `src/components/admin/WorkforceOffice.tsx`:
  - Reads centralized ops snapshot from `/api/admin/ai-ops/status`.
  - Uses snapshot-driven pressure/warning/health signals.
  - Added visible `Demo / Simulated` label when `VITE_NEXUS_DEMO_MODE` is enabled.
  - Added queue pressure and grants in top KPI row.

## Visual Behavior
- Department activity reflects ingestion pressure, provider health, tickets, and scheduler warning states.
- Existing motion primitives retained for low-overhead animation.

## Notes
- Mobile responsiveness follows current card/stack layout and existing controls.
- Further perf polish can be done after runtime profiling on target device.
