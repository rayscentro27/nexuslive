# Workforce Demo Trading Integration

Date: 2026-05-15

Workforce Office integration is provided through the centralized operational snapshot.

New visibility available to workforce surfaces:
- Sage/trading demo autonomy active state
- active demo trade count
- strategy learning state (confidence map)
- risk warning and guardrail states
- cooldown and kill-switch state
- demo trade journal activity
- learning-from-failure indicators (recent lessons)

Data source:
- `lib/central_operational_snapshot.py`
- `lib/autonomous_demo_trading_lab.py`
