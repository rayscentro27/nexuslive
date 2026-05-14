# Final Direct Telegram Sender Inventory

Generated: 2026-05-14

## Failing modules from `scripts/test_telegram_policy.py` (final pass)
- `sales_agent/sales_agent.py` — `_send_response` fallback direct Telegram send; trigger: output service failure; class: conversational fallback; action: **wrapped to `send_direct_response`**.
- `source_health/health_worker.py` — `_send_telegram`; trigger: critical low source health; class: critical alert; action: **wrapped to `hermes_gate.send(...critical_alert...)`**.
- `support_agent/support_agent.py` — escalation Telegram notify; trigger: support escalation; class: critical alert; action: **wrapped to `hermes_gate.send(...critical_alert...)`**.

## Additional direct sender removals/refactors completed this pass
- `browser_worker/worker.py`
- `ceo_agent/comms_reliability.py`
- `content_employee/nova_media.py`
- `decision_engine/decision_worker.py`
- `empire/empire_worker.py`
- `improvement_engine/improvement_worker.py`
- `instance_engine/kill_scale_worker.py`
- `nexus-strategy-lab/review/hermes_reviewer.py`
- `optimization_engine/optimization_worker.py`
- `optimization_engine/optimization_summary_job.py`
- `portfolio/portfolio_worker.py`
- `readiness/readiness_worker.py`
- `revenue_engine/revenue_worker.py`
- `nexus_one/nexus_one_worker.py`
- `nexus-strategy-lab/run_pipeline.py`
- `nexus-strategy-lab/trading/metrics.py`
