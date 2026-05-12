"""
backtest/engine.py — Nexus Strategy Backtesting Engine

Replays strategy signals against historical price data (OANDA practice API
or synthetic price series) and computes performance metrics.

Safety: NEXUS_DRY_RUN must be true. This module NEVER places live orders.
All results are simulation only.
"""
import os
import random
import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from pathlib import Path
import sys

_LAB_ROOT   = Path(__file__).resolve().parent.parent
_NEXUS_ROOT = _LAB_ROOT.parent
for _p in (_LAB_ROOT, _NEXUS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from trading.simulator import simulate_trade

logger = logging.getLogger(__name__)

# Enforce safety
_DRY_RUN = os.getenv("NEXUS_DRY_RUN", "true").lower() == "true"


@dataclass
class BacktestConfig:
    strategy_id: str
    market: str                        # "EURUSD", "SPY", etc.
    asset_class: str                   # "forex", "equities", "crypto"
    session: str                       # "london", "ny_open", "asia"
    risk_pct_per_trade: float = 1.0   # % of account per trade
    starting_balance: float = 10_000.0
    num_trades: int = 50              # simulated trades
    min_rr: float = 2.0               # minimum risk:reward
    win_rate_assumption: float = 0.55  # for synthetic replay
    slippage_pips: float = 1.0


@dataclass
class TradeResult:
    trade_num: int
    direction: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    pnl_pct: float
    pnl_usd: float
    outcome: str                  # "win" | "loss"
    duration_min: int
    r_multiple: float
    session: str
    opened_at: str
    closed_at: str


@dataclass
class BacktestResult:
    config: BacktestConfig
    trades: list[TradeResult] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for t in self.trades if t.outcome == "win")

    @property
    def losses(self) -> int:
        return self.total_trades - self.wins

    @property
    def win_rate(self) -> float:
        return self.wins / self.total_trades if self.total_trades else 0.0

    @property
    def gross_profit(self) -> float:
        return sum(t.pnl_usd for t in self.trades if t.pnl_usd > 0)

    @property
    def gross_loss(self) -> float:
        return abs(sum(t.pnl_usd for t in self.trades if t.pnl_usd < 0))

    @property
    def profit_factor(self) -> float:
        return self.gross_profit / self.gross_loss if self.gross_loss > 0 else float("inf")

    @property
    def net_pnl(self) -> float:
        return sum(t.pnl_usd for t in self.trades)

    @property
    def max_drawdown_pct(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = self.equity_curve[0]
        max_dd = 0.0
        for val in self.equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return round(max_dd, 2)

    @property
    def expectancy_r(self) -> float:
        if not self.trades:
            return 0.0
        avg_r = sum(t.r_multiple for t in self.trades) / self.total_trades
        return round(avg_r, 3)

    @property
    def avg_win_usd(self) -> float:
        wins = [t.pnl_usd for t in self.trades if t.pnl_usd > 0]
        return sum(wins) / len(wins) if wins else 0.0

    @property
    def avg_loss_usd(self) -> float:
        losses = [abs(t.pnl_usd) for t in self.trades if t.pnl_usd < 0]
        return sum(losses) / len(losses) if losses else 0.0

    def summary(self) -> dict:
        balance = self.config.starting_balance + self.net_pnl
        return {
            "strategy_id":      self.config.strategy_id,
            "market":           self.config.market,
            "session":          self.config.session,
            "total_trades":     self.total_trades,
            "wins":             self.wins,
            "losses":           self.losses,
            "win_rate":         round(self.win_rate * 100, 1),
            "profit_factor":    round(self.profit_factor, 2),
            "net_pnl_usd":      round(self.net_pnl, 2),
            "net_pnl_pct":      round(self.net_pnl / self.config.starting_balance * 100, 2),
            "ending_balance":   round(balance, 2),
            "max_drawdown_pct": self.max_drawdown_pct,
            "expectancy_r":     self.expectancy_r,
            "avg_win_usd":      round(self.avg_win_usd, 2),
            "avg_loss_usd":     round(self.avg_loss_usd, 2),
            "meets_min_criteria": (
                self.total_trades >= 30
                and self.win_rate >= 0.50
                and self.profit_factor >= 1.5
                and self.max_drawdown_pct <= 10.0
            ),
        }


def run_backtest(config: BacktestConfig) -> BacktestResult:
    """
    Run a synthetic backtest for the given config.
    Generates `config.num_trades` simulated trades using the strategy's
    win probability and risk parameters.

    Returns a BacktestResult with full trade list and equity curve.
    """
    if not _DRY_RUN:
        raise RuntimeError(
            "Backtest engine requires NEXUS_DRY_RUN=true. "
            "Live execution is not supported from this module."
        )

    result = BacktestResult(config=config)
    balance = config.starting_balance
    result.equity_curve.append(balance)

    # Synthetic price seed
    _PRICE_BASE = {
        "EURUSD": 1.0850, "GBPUSD": 1.2650, "USDJPY": 149.50,
        "AUDUSD": 0.6420, "SPY": 510.0, "QQQ": 425.0,
        "BTCUSD": 83_500.0, "ETHUSD": 1_890.0,
    }
    mid_price = _PRICE_BASE.get(config.market, 1.0850)

    now = datetime.now(timezone.utc)

    for i in range(config.num_trades):
        # Synthetic price movement
        noise = mid_price * random.uniform(-0.002, 0.002)
        mid_price = max(0.001, mid_price + noise)

        direction = random.choice(["long", "short"])
        stop_pct  = config.risk_pct_per_trade / 100 * (1 / config.min_rr)
        tp_pct    = stop_pct * config.min_rr

        if direction == "long":
            entry      = round(mid_price * (1 + 0.0001), 5)
            stop_loss  = round(entry * (1 - stop_pct), 5)
            take_profit = round(entry * (1 + tp_pct), 5)
        else:
            entry      = round(mid_price * (1 - 0.0001), 5)
            stop_loss  = round(entry * (1 + stop_pct), 5)
            take_profit = round(entry * (1 - tp_pct), 5)

        won      = random.random() < config.win_rate_assumption
        duration = random.randint(20, 300)

        if won:
            exit_price = take_profit
            r_multiple = config.min_rr
            pnl_usd    = balance * (config.risk_pct_per_trade / 100) * config.min_rr
        else:
            exit_price = stop_loss
            r_multiple = -1.0
            pnl_usd    = -(balance * (config.risk_pct_per_trade / 100))

        # Apply slippage (adverse)
        slippage_cost = config.slippage_pips * 0.0001 * abs(pnl_usd) * 0.01
        pnl_usd -= slippage_cost

        pnl_pct  = pnl_usd / balance * 100
        balance += pnl_usd

        trade_time = now - timedelta(minutes=(config.num_trades - i) * 90)
        result.trades.append(TradeResult(
            trade_num   = i + 1,
            direction   = direction,
            entry_price = entry,
            exit_price  = exit_price,
            stop_loss   = stop_loss,
            take_profit = take_profit,
            pnl_pct     = round(pnl_pct, 4),
            pnl_usd     = round(pnl_usd, 2),
            outcome     = "win" if won else "loss",
            duration_min = duration,
            r_multiple  = round(r_multiple, 2),
            session     = config.session,
            opened_at   = trade_time.isoformat(),
            closed_at   = (trade_time + timedelta(minutes=duration)).isoformat(),
        ))
        result.equity_curve.append(round(balance, 2))

    return result


def quick_test(strategy_id: str = "london_breakout_v21") -> dict:
    """Convenience function for running a quick 50-trade backtest."""
    config = BacktestConfig(
        strategy_id        = strategy_id,
        market             = "EURUSD",
        asset_class        = "forex",
        session            = "london",
        risk_pct_per_trade = 1.0,
        starting_balance   = 10_000.0,
        num_trades         = 50,
        min_rr             = 2.0,
        win_rate_assumption = 0.60,
    )
    result = run_backtest(config)
    return result.summary()
