# Trading Task Executor

Consumes trading `implementation_tasks` and turns them into concrete local
artifacts under `generated_trading/`, while queueing a `paper_trade_runs` row
when a `TradingEngine` task has a linked `reviewed_signal_proposals` record.

Worker:

- `research_intelligence/trading_task_executor.py`

Usage:

```bash
python3 -m research_intelligence.trading_task_executor --limit 10
```

What it does:

1. Reads active trading `implementation_projects`
2. Loads related `implementation_tasks`
3. Processes tasks for:
   - `ResearchDesk`
   - `TradingEngine`
4. Writes local artifacts into:
   - `generated_trading/<slug>/`
5. Queues a deterministic `paper_trade_runs` row for replay-lab follow-up when possible
6. Marks those tasks `completed`
7. Leaves the project `in_progress` if it is waiting on a queued paper-trade run
