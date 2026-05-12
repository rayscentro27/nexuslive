# Nexus Trading Risk Engine Architecture
**Date:** 2026-05-12  
**Mode:** Architecture design — paper trading only, TRADING_LIVE_EXECUTION_ENABLED=false

---

## Core Principle

The risk engine is the most important component of the platform. It is not a suggestion system. It is an enforcer. Every trade decision — paper or live — must pass through the risk engine. The engine never trusts the strategy; it only trusts its own rules.

---

## Risk Engine Layers (Defense in Depth)

```
Trade Signal
    ↓
[1] Market Filter     — Is this market approved? Is liquidity sufficient?
    ↓
[2] Session Filter    — Is this the approved trading session?
    ↓
[3] News Filter       — Is there a high-impact news event in the next 30 min?
    ↓
[4] Volatility Filter — Is volatility within acceptable range?
    ↓
[5] Position Check    — How many open positions? Correlated exposure?
    ↓
[6] Daily P&L Check   — Are we within daily loss limit?
    ↓
[7] Weekly Drawdown   — Are we within weekly drawdown limit?
    ↓
[8] Streak Check      — Consecutive losses exceeded threshold?
    ↓
[9] Slippage Check    — Is execution quality acceptable? (live only)
    ↓
[10] Circuit Breaker  — Is any emergency halt active?
    ↓
APPROVED → Execute (paper or live)
```

Any layer can block the trade. Blocked trades are logged with reason.

---

## Risk Parameters (Configurable, Human-Approved)

### Account-Level
| Parameter | Default | Description |
|---|---|---|
| `max_daily_loss_pct` | 2.0% | Halt trading if daily loss exceeds this |
| `max_weekly_drawdown_pct` | 5.0% | Halt trading for week if exceeded |
| `max_monthly_drawdown_pct` | 10.0% | Halt all automation for month |
| `account_risk_per_trade_pct` | 1.0% | Max risk per individual trade |
| `max_concurrent_positions` | 4 | Maximum open positions at once |
| `max_correlated_exposure_pct` | 4.0% | Max exposure in correlated pairs |

### Session-Level
| Parameter | Default | Description |
|---|---|---|
| `approved_sessions` | ["london", "ny_open"] | Only trade during these sessions |
| `session_trade_limit` | 3 | Max trades per session |
| `news_blackout_minutes` | 30 | No trades X minutes before high-impact news |
| `session_loss_limit_pct` | 1.0% | Stop for session if exceeded |

### Strategy-Level
| Parameter | Default | Description |
|---|---|---|
| `max_consecutive_losses` | 3 | Pause strategy after N consecutive losses |
| `min_rr_ratio` | 2.0 | Minimum risk:reward required |
| `min_confidence_score` | 0.65 | AI confidence threshold |
| `edge_deterioration_threshold` | -15% | Win rate drop that triggers review |
| `volatility_multiplier_max` | 2.5 | Max ATR expansion factor to trade |

---

## Circuit Breakers

Circuit breakers are unconditional. They override strategy logic, AI signals, and operator input until manually reset or auto-reset timer expires.

| Trigger | Action | Reset |
|---|---|---|
| Daily loss > `max_daily_loss_pct` | Halt all trading, 24h | Next trading day |
| Consecutive losses > threshold | Pause strategy | 4h cooldown |
| Volatility spike > 3x normal | Halt until normalized | Auto (30min check) |
| API failure / latency > 2s | Halt until confirmed stable | Manual reset |
| Slippage > 3x expected | Halt, flag for review | Manual review |
| Market gap > 1% | Skip trade, log event | Auto |
| Weekly drawdown exceeded | Halt week | Next Monday |
| Abnormal P&L swing | Freeze positions, alert Hermes | Manual |

---

## Position Sizing Engine

### Kelly Fraction (conservative, half-Kelly)
```python
def kelly_fraction(win_rate: float, rr_ratio: float) -> float:
    edge = (win_rate * rr_ratio) - (1 - win_rate)
    return max(0, edge / rr_ratio) * 0.5  # half-Kelly for safety

# Example: 60% win rate, 2:1 R:R
# Full Kelly: (0.6*2 - 0.4) / 2 = 0.4
# Half-Kelly: 0.2 → risk 20% of max allowed per trade
```

### Position Size Calculation
```python
def position_size(
    account_balance: float,
    risk_pct: float,      # from account_risk_per_trade_pct
    stop_loss_pips: float,
    pip_value: float,
) -> float:
    risk_amount = account_balance * (risk_pct / 100)
    return risk_amount / (stop_loss_pips * pip_value)
```

### Volatility-Adjusted Sizing
- When ATR is elevated: reduce position size proportionally
- Formula: `adjusted_size = base_size * (normal_atr / current_atr)`
- Cap: never more than 1.5x base size regardless

---

## Risk Score Engine

Each proposed trade receives a composite risk score (0-100):

```
Risk Score = weighted_average([
    daily_drawdown_proximity    × 30,
    weekly_drawdown_proximity   × 20,
    volatility_factor           × 20,
    correlation_exposure        × 15,
    consecutive_loss_streak     × 10,
    session_loss_proximity      × 5,
])
```

| Score | Label | Action |
|---|---|---|
| 0-30 | LOW | Trade approved |
| 31-60 | MODERATE | Trade approved with reduced size |
| 61-80 | HIGH | Requires AI confirmation |
| 81-100 | CRITICAL | Trade blocked, circuit breaker |

---

## Data Schema

### `risk_checks` table
```sql
CREATE TABLE risk_checks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id     TEXT NOT NULL,
    signal_id       TEXT,
    checked_at      TIMESTAMPTZ DEFAULT NOW(),
    passed          BOOLEAN NOT NULL,
    blocked_by      TEXT,           -- which layer blocked it
    risk_score      INTEGER,        -- 0-100
    daily_loss_pct  DECIMAL(5,2),
    weekly_dd_pct   DECIMAL(5,2),
    open_positions  INTEGER,
    volatility_ok   BOOLEAN,
    session_ok      BOOLEAN,
    news_ok         BOOLEAN,
    circuit_breaker TEXT,           -- null if none active
    details         JSONB
);
```

### `circuit_breaker_events` table
```sql
CREATE TABLE circuit_breaker_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    triggered_at    TIMESTAMPTZ DEFAULT NOW(),
    trigger_type    TEXT NOT NULL,  -- daily_loss | volatility | api | etc
    trigger_value   DECIMAL(10,4),
    resolved_at     TIMESTAMPTZ,
    resolved_by     TEXT,           -- auto | ray | hermes
    notes           TEXT
);
```

---

## Hermes Risk Integration

Hermes monitors the risk engine and reports:
- "Risk engine: nominal / elevated / critical" in daily CEO summary
- Alerts on any circuit breaker trigger
- Weekly risk review: drawdown trend, strategy health, parameter review needed?
- Flags parameter drift: "Win rate dropped 12% — recommend parameter review"

Risk engine is NOT under Hermes control. Hermes reads from it and reports. Only the operator can modify risk parameters (with confirmation).

---

## Paper Trading Safety

During paper trading phase:
- All risk engine logic is active (same code path)
- Circuit breakers still fire (pauses paper trades)
- This validates the risk engine before any live capital
- Paper trading "losses" counted toward drawdown limits (to calibrate thresholds)
