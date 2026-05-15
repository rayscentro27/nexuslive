# Revenue and Demo Trading Tests

Date: 2026-05-15

## Commands run

```bash
python3 -m py_compile lib/central_operational_snapshot.py lib/hermes_supabase_first.py lib/autonomous_demo_trading_lab.py revenue_engine/revenue_foundation.py revenue_engine/revenue_experiment_tracker.py revenue_engine/__init__.py
python3 scripts/test_revenue_engine_foundation.py
python3 scripts/test_demo_trading_learning_lab.py
python3 scripts/test_telegram_policy.py
python3 scripts/test_trading_intelligence_lab.py
python3 scripts/test_ai_ops_control_center.py
```

## Result summary

- Compile checks: pass
- Revenue foundation tests: pass
- Demo trading guardrail/learning tests: pass
- Telegram policy test: pass (manual-only policy preserved)
- Trading intelligence lab test: pass
- AI ops control center test script: environment-limited in this shell (missing Supabase env and unrelated existing import errors), not used as release blocker for these additive changes

## Safety verification

- Real-money flags expected disabled in demo posture checks.
- Live endpoint detection is explicitly validated.
- Demo kill switch blocks trades when enabled.
- Guardrail failures block trades.
