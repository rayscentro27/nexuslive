# Trading Demo Account & Strategy Flow — Architecture Report
**Date:** 2026-05-12 | **Pass:** Trading Demo Platform | **Safety:** NEXUS_DRY_RUN=true

## Overview
This report documents the end-to-end demo account connection and strategy approval flow built in Pass 3 of the Nexus Trading Intelligence Platform.

## Components Built

### DemoAccountConnect.tsx
Five paper trading providers, one currently active:

| Provider | Status | Balance |
|---|---|---|
| Nexus Simulated Account | Available | $10,000 |
| OANDA Demo | Coming Soon | — |
| TradingView Paper | Coming Soon | — |
| NinjaTrader Sim | Coming Soon | — |
| Webull Paper | Coming Soon | — |

Connection flow: provider selection → simulated 1.2s handshake → ConnectedBadge display. Balance, equity, and buying power (30:1 forex leverage) displayed. "Demo Mode Only — No Real Money Trades" badge always visible.

### StrategyApproval.tsx
Three-step approval flow:
1. **Select** — 6 strategy cards (London Breakout, SPY Trend, BTC Structure, Purple Cloud, Futures Morning Reversal, High-IV Options)
2. **Configure Risk Guardrails** — range sliders for: maxRiskPctPerTrade (0.25–3%), maxDailyLossPct (0.5–5%), maxWeeklyDrawdownPct (1–10%), maxOpenTrades (1–6)
3. **Confirm** — produces `StrategyApprovalRecord` with approvedBy/approvedAt, status: 'active'

Default guardrails enforce: 1% per-trade risk, 2% daily loss cap, 5% weekly drawdown, 3 max open trades, London+NY sessions only, auto-pause after 3 consecutive losses, volatility protection enabled.

## Safety Architecture
- `StrategyApprovalRecord.status` is always 'active' (paper only) — live status requires separate flag
- NEXUS_DRY_RUN=true enforced in paper_trade_executor.py at module load
- LIVE_TRADING=false maintained throughout
- No real broker order submission at any point in this flow

## Data Flow
```
User selects strategy → risk guardrails configured → approval record created
      ↓
paper_trade_executor.open_paper_position(strategy_id, signal, approval_record)
      ↓ (DRY_RUN check → CB check → risk check → OANDA practice price → position opened)
PaperPosition journaled → Supabase paper_trading_journal_entries
```
