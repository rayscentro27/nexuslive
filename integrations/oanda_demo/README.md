# OANDA Demo / Practice Adapter

**Practice environment only. No live trading. No bank account.**

## Safety Constraints (hardcoded — cannot be overridden)

| Constraint | Value |
|---|---|
| `OANDA_DEMO_ENABLED` default | `false` — must be explicitly set to `true` |
| `OANDA_ENVIRONMENT` | always `practice` |
| `OANDA_ALLOW_LIVE` | always `false` — adapter rejects if set to `true` |
| `OANDA_MAX_UNITS` | `1` unit per order max |
| `OANDA_MAX_DAILY_ORDERS` | `3` orders per day max |
| Live endpoint | never used — blocked at code level |
| Access token logging | never logged |
| `.env` | gitignored — never committed |

## Setup

1. Get a free OANDA practice account at practice.oanda.com
2. Copy `.env.example` → `.env` and fill in your practice credentials
3. Set `OANDA_DEMO_ENABLED=true` in `.env` (Ray approval required)
4. Run `python test_oanda_connection.py` to verify practice connectivity

## Usage

```python
from integrations.oanda_demo import OandaDemoAdapter

adapter = OandaDemoAdapter()
status = adapter.connection_status()
result = adapter.place_demo_order("EUR_USD", "buy", units=1, reason="RSI oversold test")
```

## Files

- `oanda_demo_adapter.py` — core adapter (practice only, safety guards)
- `test_oanda_connection.py` — verify practice account connectivity
- `test_oanda_demo_order.py` — place 1-unit test order and verify fill
- `.env.example` — credential template (safe to commit)
- `.env` — gitignored, never committed
- `reports/` — all demo trade logs saved here

## Policy

This adapter exists for **strategy back-testing and demo execution only**.
- Ray must approve `OANDA_DEMO_ENABLED=true`
- Max 1 unit per order
- Max 3 orders per day
- All orders logged to `reports/demo_orders_<date>.jsonl`
- No live account. No real money.
