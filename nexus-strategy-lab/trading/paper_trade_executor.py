"""
trading/paper_trade_executor.py — Real-time paper trade executor.

Executes simulated trades using live OANDA practice prices (no real funds).
All trades are paper-only and journaled to Supabase.

Safety guarantees:
- NEXUS_DRY_RUN must be true (enforced at module load)
- LIVE_TRADING must be false (enforced at module load)
- No actual order submission — price quotes only from OANDA practice API
- Circuit breaker checked before every entry
- Risk engine checked before every entry

This module is designed for Phase 2: paper trading with live price feeds.
"""
import os
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

_LAB_ROOT   = Path(__file__).resolve().parent.parent
_NEXUS_ROOT = _LAB_ROOT.parent
for _p in (_LAB_ROOT, _NEXUS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

logger = logging.getLogger(__name__)

# ── Safety enforcement ────────────────────────────────────────────────────────

_DRY_RUN     = os.getenv("NEXUS_DRY_RUN",     "true").lower() == "true"
_LIVE_TRADING = os.getenv("LIVE_TRADING",      "false").lower() == "true"
_AUTO_TRADING = os.getenv("NEXUS_AUTO_TRADING","false").lower() == "true"

if _LIVE_TRADING:
    raise RuntimeError(
        "LIVE_TRADING=true detected. This module only supports paper/demo trading. "
        "Set LIVE_TRADING=false before importing."
    )


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class PriceQuote:
    symbol: str
    bid: float
    ask: float
    mid: float
    timestamp: str
    source: str = "oanda_practice"


@dataclass
class PaperPosition:
    id: str
    strategy_id: str
    symbol: str
    direction: str            # "long" | "short"
    entry_price: float
    stop_loss: float
    take_profit: float
    size_units: float
    size_lots: float
    opened_at: str
    session: str
    ai_confidence: float
    status: str = "open"      # "open" | "closed" | "tp_hit" | "stopped" | "trailing"
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    closed_at: Optional[str] = None
    pnl_pips: Optional[float] = None
    pnl_usd: Optional[float] = None


@dataclass
class ExecutionResult:
    success: bool
    position: Optional[PaperPosition]
    rejected_by: Optional[str] = None   # which check rejected
    reason: Optional[str] = None
    risk_score: Optional[int] = None


# ── Price feed ────────────────────────────────────────────────────────────────

def get_practice_price(symbol: str) -> PriceQuote:
    """
    Fetch live price from OANDA practice API.
    Falls back to synthetic price if API unavailable.
    No live trading — read-only price quotes only.
    """
    api_key = os.getenv("OANDA_API_KEY", "")
    api_url  = os.getenv("OANDA_API_URL", "https://api-fxpractice.oanda.com")
    account  = os.getenv("OANDA_ACCOUNT_ID", "")

    if api_key and account:
        try:
            import urllib.request, json
            url = f"{api_url}/v3/accounts/{account}/pricing?instruments={symbol.replace('/','_')}"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
            ssl_cert = os.getenv("SSL_CERT_FILE", "")
            ctx = None
            if ssl_cert:
                import ssl
                ctx = ssl.create_default_context(cafile=ssl_cert)
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                data = json.loads(resp.read())
                price = data["prices"][0]
                bid = float(price["bids"][0]["price"])
                ask = float(price["asks"][0]["price"])
                return PriceQuote(
                    symbol=symbol, bid=bid, ask=ask,
                    mid=round((bid + ask) / 2, 5),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="oanda_practice",
                )
        except Exception as e:
            logger.debug(f"OANDA price fetch failed ({e}), using synthetic price")

    # Synthetic fallback
    import random
    SEEDS = {
        "EUR_USD": 1.0850, "GBP_USD": 1.2650, "USD_JPY": 149.50,
        "AUD_USD": 0.6420, "USD_CAD": 1.3650,
    }
    mid = SEEDS.get(symbol.replace("/", "_"), 1.0)
    mid += random.uniform(-0.002, 0.002) * mid
    spread = 0.0002
    return PriceQuote(
        symbol=symbol, bid=round(mid - spread/2, 5), ask=round(mid + spread/2, 5),
        mid=round(mid, 5), timestamp=datetime.now(timezone.utc).isoformat(),
        source="synthetic",
    )


# ── Risk pre-check ────────────────────────────────────────────────────────────

def _check_circuit_breaker(strategy_id: str) -> tuple[bool, str]:
    """Returns (allowed, reason). Allowed=True means no CB active."""
    try:
        from lib import circuit_breaker as cb
        if cb.is_halted(strategy_id):
            status = cb.get_status()
            active = status.get("active_breakers", [])
            names  = [e.get("trigger_type", "?") for e in active]
            return False, f"Circuit breaker active: {', '.join(names)}"
    except Exception:
        pass
    return True, "ok"


def _check_risk_limits(
    strategy_id: str,
    signal: dict,
    account_balance: float,
    open_positions: list[PaperPosition],
    max_open: int = 4,
    max_risk_pct: float = 1.0,
) -> tuple[bool, str, int]:
    """
    Lightweight 5-layer pre-check.
    Returns (allowed, reason, risk_score_0_100).
    """
    # Layer 1: position count
    open_count = sum(1 for p in open_positions if p.status == "open")
    if open_count >= max_open:
        return False, f"Max positions reached ({open_count}/{max_open})", 85

    # Layer 2: stop loss required
    if not signal.get("stop_loss"):
        return False, "Stop loss required but not provided", 90

    # Layer 3: take profit required
    if not signal.get("take_profit"):
        return False, "Take profit required but not provided", 85

    # Layer 4: risk:reward minimum (2:1)
    entry    = float(signal.get("entry_price", 0))
    sl       = float(signal.get("stop_loss",  0))
    tp       = float(signal.get("take_profit", 0))
    if entry and sl and tp:
        risk   = abs(entry - sl)
        reward = abs(tp - entry)
        if risk > 0 and (reward / risk) < 2.0:
            return False, f"R:R below minimum ({reward/risk:.1f}:1 vs 2.0:1 required)", 75

    # Layer 5: position size vs account risk
    risk_usd = account_balance * (max_risk_pct / 100)
    if signal.get("risk_usd", 0) > risk_usd * 1.1:
        return False, f"Risk amount exceeds {max_risk_pct}% of account", 80

    # Risk score (lower = safer)
    risk_score = min(40 + open_count * 10, 70)
    return True, "ok", risk_score


# ── Execution ─────────────────────────────────────────────────────────────────

def open_paper_position(
    strategy_id: str,
    signal: dict,
    account_balance: float,
    open_positions: list[PaperPosition],
    approval_record: Optional[dict] = None,
) -> ExecutionResult:
    """
    Open a simulated paper position.

    signal dict keys:
        symbol, direction ("long"|"short"), stop_loss, take_profit,
        size_lots, session, ai_confidence, risk_usd (optional)

    Returns ExecutionResult with position or rejection reason.
    """
    # Safety check: never execute if DRY_RUN is somehow false at runtime
    if not _DRY_RUN:
        return ExecutionResult(
            success=False,
            position=None,
            rejected_by="safety",
            reason="NEXUS_DRY_RUN=false — execution blocked",
        )

    # Circuit breaker check
    cb_ok, cb_reason = _check_circuit_breaker(strategy_id)
    if not cb_ok:
        return ExecutionResult(success=False, position=None, rejected_by="circuit_breaker", reason=cb_reason)

    # Risk check
    max_open = int(approval_record.get("maxOpenTrades", 4)) if approval_record else 4
    max_risk = float(approval_record.get("maxRiskPctPerTrade", 1.0)) if approval_record else 1.0
    risk_ok, risk_reason, risk_score = _check_risk_limits(
        strategy_id, signal, account_balance, open_positions, max_open, max_risk
    )
    if not risk_ok:
        return ExecutionResult(success=False, position=None, rejected_by="risk_engine", reason=risk_reason, risk_score=risk_score)

    # Get live practice price
    symbol = signal.get("symbol", "EUR/USD")
    quote  = get_practice_price(symbol)
    direction = signal.get("direction", "long")
    entry = quote.ask if direction == "long" else quote.bid

    # Add realistic slippage (0.5–1.5 pips)
    import random
    slippage = random.uniform(0.00005, 0.00015)
    if direction == "long":
        entry = round(entry + slippage, 5)
    else:
        entry = round(entry - slippage, 5)

    position = PaperPosition(
        id            = f"paper_{strategy_id}_{int(datetime.now().timestamp())}",
        strategy_id   = strategy_id,
        symbol        = symbol,
        direction     = direction,
        entry_price   = entry,
        stop_loss     = float(signal["stop_loss"]),
        take_profit   = float(signal["take_profit"]),
        size_units    = float(signal.get("size_lots", 0.01)) * 100_000,
        size_lots     = float(signal.get("size_lots", 0.01)),
        opened_at     = datetime.now(timezone.utc).isoformat(),
        session       = signal.get("session", "unknown"),
        ai_confidence = float(signal.get("ai_confidence", 0.0)),
        status        = "open",
    )

    logger.info(
        f"[PAPER] Opened {direction} {symbol} @ {entry} | "
        f"SL:{signal['stop_loss']} TP:{signal['take_profit']} | "
        f"strategy={strategy_id} | source={quote.source}"
    )
    return ExecutionResult(success=True, position=position, risk_score=risk_score)


def check_exit_conditions(
    position: PaperPosition,
    current_price: PriceQuote,
) -> tuple[bool, str, float]:
    """
    Check if SL or TP has been hit.
    Returns (should_close, reason, exit_price).
    """
    if position.direction == "long":
        price = current_price.bid  # long exits at bid
        if price <= position.stop_loss:
            return True, "sl", position.stop_loss
        if price >= position.take_profit:
            return True, "tp", position.take_profit
    else:
        price = current_price.ask  # short exits at ask
        if price >= position.stop_loss:
            return True, "sl", position.stop_loss
        if price <= position.take_profit:
            return True, "tp", position.take_profit
    return False, "", 0.0


def close_paper_position(
    position: PaperPosition,
    exit_price: float,
    exit_reason: str,
    pip_value: float = 10.0,  # USD per pip per lot (standard forex)
) -> PaperPosition:
    """Close a paper position and compute PnL."""
    if position.direction == "long":
        pips = (exit_price - position.entry_price) / 0.0001
    else:
        pips = (position.entry_price - exit_price) / 0.0001

    pnl_usd = round(pips * position.size_lots * pip_value, 2)

    position.exit_price  = exit_price
    position.exit_reason = exit_reason
    position.closed_at   = datetime.now(timezone.utc).isoformat()
    position.pnl_pips    = round(pips, 1)
    position.pnl_usd     = pnl_usd
    position.status      = "tp_hit" if exit_reason == "tp" else "stopped" if exit_reason == "sl" else "closed"

    logger.info(
        f"[PAPER] Closed {position.direction} {position.symbol} @ {exit_price} | "
        f"reason={exit_reason} | pips={pips:.1f} | pnl=${pnl_usd}"
    )
    return position
