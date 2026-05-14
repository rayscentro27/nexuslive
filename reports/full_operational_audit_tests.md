# Full Operational Audit Tests

Generated: 2026-05-14

## Tests Run
- `python3 scripts/test_telegram_summary_removal.py` => **PASS** (8/8)
- `python3 scripts/test_telegram_policy.py` => **PARTIAL** (30/31)
  - failing assertion: some non-test modules still send Telegram directly, not via `hermes_gate`
- `python3 scripts/test_nexus_model_routing.py` => **PASS** (72/72)

## Interpretation
- Default-deny behavior for blocked summary categories is functioning.
- Known follow-up debt remains: migrate remaining direct sender modules to centralized gate wrapper.
