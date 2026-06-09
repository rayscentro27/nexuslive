#!/usr/bin/env python3
"""
Nexus AI Trading Engine
Orchestrates the complete AI trading pipeline:
Research Knowledge → Strategy Agent → Risk Manager → Broker API → Trade Execution
"""

import sys
import os
import json
import time
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass

# GLOBAL SAFETY FLAG
# Keep paper mode as the default until live execution is explicitly re-approved.
LIVE_EXECUTION_ENABLED = os.getenv('TRADING_LIVE_EXECUTION_ENABLED', 'false').lower() == 'true'
DRY_RUN = os.getenv('NEXUS_DRY_RUN', 'true').lower() == 'true' or not LIVE_EXECUTION_ENABLED
ROOT = Path(__file__).resolve().parent.parent
STATUS_FILE = ROOT / "logs" / "trading_engine_status.json"
HALT_FLAG   = ROOT / "logs" / "trading_engine_halt.flag"
STATUS_LOCK = threading.Lock()
STRATEGY_TIMEOUT = int(os.getenv("NEXUS_STRATEGY_TIMEOUT", "15"))
PAPER_FAST_MODE = os.getenv("NEXUS_PAPER_FAST_MODE", "true").lower() == "true"

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hermes.trade_reviewer  import review_signal as hermes_review_signal
from hermes.command_handler import HermesCommandHandler
from integrations.oanda_demo import OandaDemoAdapter
from integrations.oanda_demo.oanda_demo_adapter import OandaSafetyError
from lib.trading_fallback_logger import append_jsonl
from lib.trading_safety_gate import evaluate_trading_safety


# ── Telegram Notifier ─────────────────────────────────────────────────────────

class TelegramNotifier:
    """Digest-first notifier for trading engine events."""

    def __init__(self):
        self.token   = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.enabled = bool(self.token and self.chat_id)

    def _send(self, text: str, critical: bool = False):
        if not self.enabled:
            return
        try:
            from lib import hermes_gate

            if critical:
                hermes_gate.send_critical(text, event_type='trading_risk_violation')
            else:
                hermes_gate.record_digest_item('trading_digest', text)
        except Exception:
            pass

    def engine_started(self, mode: str, balance: float):
        self._send(
            f"*Nexus Trading Engine Started*\n"
            f"Mode: `{mode}` | Balance: `${balance:,.2f}`\n"
            f"Paper mode: `{DRY_RUN}`"
        )

    def signal_received(self, symbol: str, action: str, timeframe: str = ''):
        self._send(
            f"*Signal Received*\n"
            f"Symbol: `{symbol}` | Action: `{action.upper()}`"
            + (f" | TF: `{timeframe}`" if timeframe else '')
        )

    def signal_rejected(self, symbol: str, action: str, reasons: list):
        reason_str = ', '.join(str(r) for r in reasons) if reasons else 'risk gate'
        self._send(
            f"*Signal Rejected* — {symbol} {action.upper()}\n"
            f"Reason: {reason_str}"
        )

    def trade_executed(self, symbol: str, side: str, size: float,
                       entry: float, sl: float = None, tp: float = None):
        sl_str = f"\nSL: `{sl}`" if sl else ''
        tp_str = f" | TP: `{tp}`" if tp else ''
        self._send(
            f"*Trade Executed*\n"
            f"`{symbol}` {side.upper()} {size} lots @ `{entry}`"
            f"{sl_str}{tp_str}"
        )

    def trade_demo(self, symbol: str, action: str):
        self._send(
            f"*Demo Signal Approved* — `{symbol}` {action.upper()}\n"
            f"Paper mode — no real order placed"
        )

    def position_closed(self, symbol: str, reason: str, pnl: float):
        icon = '✅' if pnl >= 0 else '❌'
        self._send(
            f"{icon} *Position Closed* — `{symbol}`\n"
            f"Reason: `{reason}` | P&L: `${pnl:+.2f}`"
        )

    def risk_limit_hit(self, status: dict):
        self._send(
            f"⛔ *Risk Limit Hit — Trading Halted*\n"
            f"Daily P&L: `${status.get('daily_pnl', 0):+.2f}` | "
            f"Positions: `{status.get('positions', 0)}`",
            critical=True,
        )
from risk.risk_manager import NexusRiskManager
from execution.broker_api import BrokerAPI
from signals.signal_receiver import SignalReceiver

class NexusTradingEngine:
    """Main AI Trading Engine - Orchestrates all trading components"""

    def __init__(self, config_file="trading_config.json"):
        self.config_file = config_file
        self.config = self.load_config()

        # enforce dry-run regardless of user config
        if DRY_RUN:
            print("⚠️ DRY_RUN is active - forcing demo mode and disabling live trading")
            self.config['live_trading'] = False
            self.config['broker_type'] = 'demo'
            self.config['auto_trading'] = os.getenv('NEXUS_PAPER_AUTO_TRADING', 'false').lower() == 'true'

        # Initialize only the components required for startup.
        # Strategy analysis is loaded lazily on first signal so the receiver can
        # still boot even if research/Supabase dependencies are slow.
        self.strategy_agent = None
        self.risk_manager = NexusRiskManager()
        self.broker_api = BrokerAPI(
            broker_type=self.config.get('broker_type', 'demo'),
            config=self.config.get('broker_config')
        )
        self.signal_receiver = SignalReceiver(
            port=self.config.get('signal_port', 5000),
            signal_handler=self.process_signal,
            status_provider=self.get_runtime_status,
            recent_trades_provider=self.get_recent_trades,
        )

        # Trading state
        self.is_running = False
        self.active_positions = []
        self.trading_log = []
        self.last_signal = None
        self.last_result = None
        self.receiver_started = False
        self.last_execution_mode = None
        self.last_oanda_practice_order_at = None
        self.last_local_paper_trade_at = None
        self.last_oanda_order_id = None
        self.last_trade_record = None
        self.oanda_practice_default_enabled = os.getenv('OANDA_PRACTICE_DEFAULT_ENABLED', 'true').lower() == 'true'
        self.local_paper_fallback_enabled = True
        self.max_oanda_units = int(os.getenv("OANDA_MAX_UNITS", "1"))
        self.max_oanda_trades_per_run = int(os.getenv("OANDA_MAX_DAILY_ORDERS", "3"))
        self.signal_cooldown_seconds = int(os.getenv("NEXUS_SIGNAL_COOLDOWN_SECONDS", "300"))
        self.signal_dedupe_window = int(os.getenv("NEXUS_SIGNAL_DEDUPE_WINDOW", "50"))
        self.signal_timestamps = {}
        self.signal_keys = []
        self.oanda_practice_trades_this_run = 0
        self.oanda_practice_available = False
        self.execution_blockers = []

        # Hermes integration
        self.halted          = False   # set True via /halt command
        self.pending_signal  = None    # last signal awaiting manual override
        self.hermes_override = None    # 'approve' triggers execution bypass

        self.notifier        = TelegramNotifier()
        self.hermes_commands = HermesCommandHandler(self)

        print("🦞 Nexus AI Trading Engine Initialized")
        print(f"📊 Broker: {self.broker_api.broker_type}")
        print(f"🎯 Risk Mode: {'Live' if self.config.get('live_trading', False) else 'Demo'}")
        self.write_status("initialized")

    def ensure_strategy_agent(self):
        """Load the strategy agent only when the first signal arrives."""
        if self.strategy_agent is None:
            from agents.strategy_agent import NexusStrategyAgent
            self.strategy_agent = NexusStrategyAgent()
        return self.strategy_agent

    def generate_strategy_signal(self, market_data):
        """Import and run the strategy agent inside the worker path."""
        self.write_status("loading_strategy_agent")
        strategy_agent = self.ensure_strategy_agent()
        self.write_status("strategy_agent_ready")
        return strategy_agent.generate_trading_signal(market_data)

    def build_paper_strategy_signal(self, signal, market_data):
        """Fast local strategy placeholder for paper autonomy."""
        return {
            'timestamp': datetime.now().isoformat(),
            'analysis': (
                "FAST_PAPER_MODE fallback. "
                "Paper autonomy uses the incoming signal directly while strategy dependencies warm up."
            ),
            'market_data': market_data,
            'source_signal': signal,
            'generated_by': 'paper_fast_mode',
        }

    def load_config(self):
        """Load trading engine configuration"""
        default_config = {
            'broker_type': os.getenv('BROKER_TYPE', 'oanda'),
            'live_trading': os.getenv('LIVE_TRADING', 'true').lower() == 'true',
            'signal_port': 5000,
            'auto_trading': os.getenv('NEXUS_AUTO_TRADING', 'false').lower() == 'true',
            'max_trades_per_day': 5,
            'trading_pairs': ['EURUSD', 'GBPUSD', 'USDJPY'],
            'timeframes': ['H1', 'H4'],
            'check_interval': 60,  # seconds
            'broker_config': {
                'balance': 10000.0,
                'leverage': 100
            }
        }

        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)

        return default_config

    def write_status(self, stage: str, extra: dict | None = None):
        """Persist a lightweight runtime snapshot for operator tooling."""
        try:
            with STATUS_LOCK:
                STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    'updated_at': datetime.now().isoformat(),
                    'stage': stage,
                    'dry_run': DRY_RUN,
                    'paper_only': DRY_RUN and not self.config.get('live_trading', False),
                    'live_execution_enabled': LIVE_EXECUTION_ENABLED,
                    'auto_trading': self.config.get('auto_trading', False),
                    'broker_type': self.broker_api.broker_type if hasattr(self, 'broker_api') else self.config.get('broker_type'),
                    'live_trading': self.config.get('live_trading', False),
                    'broker_connected': self.broker_api.connected if hasattr(self, 'broker_api') else False,
                    'receiver_started': self.receiver_started,
                    'signal_port': self.config.get('signal_port', 5000),
                    'receiver_health_url': f"http://127.0.0.1:{self.config.get('signal_port', 5000)}/health",
                    'is_running': self.is_running,
                    'active_positions': len(self.active_positions),
                    'signals_processed': len(self.trading_log),
                    'last_signal': self.last_signal,
                    'last_result': self.last_result,
                }
                if extra:
                    payload.update(extra)
                tmp = STATUS_FILE.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(payload, indent=2, default=str))
                tmp.replace(STATUS_FILE)
        except Exception:
            pass

    def save_config(self):
        """Save current configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def connect_broker(self):
        """Connect to broker API"""
        print("🔌 Connecting to broker...")
        connected = self.broker_api.connect()
        if connected:
            account_info = self.broker_api.get_account_info()
            balance = account_info.get('balance', 0)
            mode = 'LIVE' if self.config.get('live_trading', False) else 'DEMO'
            print(f"✅ Broker connected - Balance: ${balance:.2f}")
            self.notifier.engine_started(mode, balance)
            self.hermes_commands.start()
            self.write_status("broker_connected", {"account_info": account_info})
            return True
        else:
            print("❌ Failed to connect to broker")
            self.write_status("broker_connect_failed", {
                "broker_error": getattr(self.broker_api, "last_error", None),
                "signal_port": self.config.get('signal_port', 5000),
            })
            return False

    def _signal_asset_class(self, signal: dict) -> str:
        asset_class = str(signal.get("asset_class") or "").strip().lower()
        if asset_class:
            return asset_class
        symbol = str(signal.get("symbol") or "").upper()
        if any(token in symbol for token in ("BTC", "ETH", "SOL", "XRP", "DOGE", "ADA")):
            return "crypto"
        if any(token in symbol for token in ("SPY", "QQQ", "AAPL", "TSLA", "NVDA")):
            return "equity"
        return "forex"

    def _signal_key(self, signal: dict) -> str:
        base = {
            "symbol": signal.get("symbol"),
            "action": signal.get("action"),
            "timeframe": signal.get("timeframe"),
            "strategy_id": signal.get("strategy_id") or signal.get("strategy"),
            "entry_price": signal.get("entry_price"),
            "stop_loss": signal.get("stop_loss"),
            "take_profit": signal.get("take_profit"),
        }
        raw = json.dumps(base, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _receiver_trade_limits(self) -> dict:
        return {
            "max_units": self.max_oanda_units,
            "max_trades_per_run": self.max_oanda_trades_per_run,
            "cooldown_seconds": self.signal_cooldown_seconds,
        }

    def _mark_signal_seen(self, signal_key: str, strategy_symbol_key: str, now_ts: float) -> None:
        self.signal_timestamps[signal_key] = now_ts
        self.signal_timestamps[strategy_symbol_key] = now_ts
        self.signal_keys.append(signal_key)
        if len(self.signal_keys) > self.signal_dedupe_window:
            stale = self.signal_keys.pop(0)
            self.signal_timestamps.pop(stale, None)

    def _signal_block_reason(self, signal: dict) -> str | None:
        now_ts = time.time()
        signal_key = self._signal_key(signal)
        strategy_symbol_key = f"{signal.get('symbol')}::{signal.get('strategy_id') or signal.get('strategy')}"
        if signal_key in self.signal_timestamps:
            return "duplicate_signal"
        last_ts = self.signal_timestamps.get(strategy_symbol_key)
        if last_ts and (now_ts - last_ts) < self.signal_cooldown_seconds:
            return f"cooldown_active_{int(self.signal_cooldown_seconds - (now_ts - last_ts))}s"
        self._mark_signal_seen(signal_key, strategy_symbol_key, now_ts)
        return None

    def _normalize_instrument(self, symbol: str) -> str:
        if "_" in symbol:
            return symbol.upper()
        if len(symbol) == 6:
            return f"{symbol[:3].upper()}_{symbol[3:].upper()}"
        return symbol.upper()

    def _oanda_practice_safety(self) -> dict:
        api_url = os.getenv("OANDA_API_URL", "")
        safety = evaluate_trading_safety(broker_mode="oanda_practice", api_url=api_url)
        blockers = list(safety.get("blockers") or [])
        if not self.oanda_practice_default_enabled:
            blockers.append("OANDA_PRACTICE_DEFAULT_ENABLED=false")
        if self.oanda_practice_trades_this_run >= self.max_oanda_trades_per_run:
            blockers.append("max_oanda_practice_trades_per_run_reached")
        return {**safety, "blockers": blockers, "safe": len(blockers) == 0 and safety.get("effective_dry_run", False)}

    def _try_oanda_practice_execution(self, signal: dict) -> tuple[dict | None, str | None]:
        units = min(abs(int(signal.get("units") or 1)), self.max_oanda_units)
        if self._signal_asset_class(signal) != "forex":
            return None, "non_forex_signal"
        if units < 1:
            units = 1

        safety = self._oanda_practice_safety()
        if not safety["safe"]:
            return None, "; ".join(safety["blockers"]) or "oanda_practice_blocked"

        try:
            os.environ["OANDA_DEMO_ENABLED"] = "true"
            adapter = OandaDemoAdapter()
            conn = adapter.connection_status()
            if not conn.get("ok"):
                return None, conn.get("error") or "oanda_connection_failed"
            order = adapter.place_demo_order(
                instrument=self._normalize_instrument(str(signal.get("symbol") or "EURUSD")),
                side=str(signal.get("action") or "BUY").lower(),
                units=units,
                reason=f"receiver_signal:{signal.get('strategy_id') or signal.get('strategy') or 'manual'}",
            )
            if not order.get("ok"):
                return None, order.get("error") or "oanda_practice_order_failed"
            self.oanda_practice_available = True
            self.oanda_practice_trades_this_run += 1
            self.last_oanda_practice_order_at = order.get("placed_at") or datetime.now().isoformat()
            fill = order.get("order_fill") or {}
            order_id = fill.get("id") or fill.get("orderID")
            self.last_oanda_order_id = order_id
            return {
                "status": "executed_oanda_practice",
                "message": "Oanda practice order placed",
                "execution_mode": "oanda_practice",
                "broker_mode": "oanda_practice",
                "safety_status": "safe",
                "trade_id": order_id,
                "order_id": order_id,
                "fallback_used": False,
                "order_summary": {
                    "instrument": order.get("instrument"),
                    "side": order.get("side"),
                    "units": order.get("units"),
                    "placed_at": order.get("placed_at"),
                },
            }, None
        except OandaSafetyError as exc:
            return None, str(exc)
        except Exception as exc:
            return None, str(exc)

    def start_signal_receiver(self, background: bool = True):
        """Start the signal receiver.

        In manual mode we run the receiver in the main thread so the webhook
        server remains the primary long-lived process under launchd.
        """
        print("📡 Starting signal receiver...")
        self.receiver_started = True
        self.write_status("starting_signal_receiver", {"receiver_background": background})
        if background:
            signal_thread = threading.Thread(target=self.signal_receiver.start_server, daemon=True)
            signal_thread.start()
            time.sleep(1)  # Give server time to start
            self.write_status("signal_receiver_started", {"receiver_background": background})
            return

        self.signal_receiver.start_server()

    def process_signal(self, signal):
        """Process a trading signal through the complete pipeline"""
        print(f"🎯 Processing signal: {signal.get('symbol')} {signal.get('action')}")
        self.last_signal = signal
        self.write_status("processing_signal")
        self.notifier.signal_received(
            signal.get('symbol', '?'),
            signal.get('action', '?'),
            signal.get('timeframe', ''),
        )

        # Step 1: Strategy Agent Analysis
        market_data = {
            'symbol': signal.get('symbol', 'EURUSD'),
            'timeframe': signal.get('timeframe', 'H1'),
            'indicators': 'RSI, MACD, Moving Averages'  # Would be dynamic
        }

        if DRY_RUN and PAPER_FAST_MODE:
            strategy_signal = self.build_paper_strategy_signal(signal, market_data)
            self.write_status("paper_fast_strategy")
            print("🤖 Paper fast strategy generated")
        else:
            try:
                pool = ThreadPoolExecutor(max_workers=1)
                future = pool.submit(self.generate_strategy_signal, market_data)
                strategy_signal = future.result(timeout=STRATEGY_TIMEOUT)
                pool.shutdown(wait=False, cancel_futures=True)
                print("🤖 Strategy analysis complete")
            except FutureTimeout:
                try:
                    future.cancel()
                    pool.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
                strategy_signal = {
                    'timestamp': datetime.now().isoformat(),
                    'analysis': f'Fallback strategy: timed out after {STRATEGY_TIMEOUT}s',
                    'market_data': market_data,
                    'generated_by': 'fallback_timeout',
                }
                self.write_status("strategy_timeout")
                print(f"⚠️ Strategy analysis timed out after {STRATEGY_TIMEOUT}s - using fallback")
            except Exception as e:
                try:
                    pool.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
                strategy_signal = {
                    'timestamp': datetime.now().isoformat(),
                    'analysis': f'Fallback strategy due to error: {e}',
                    'market_data': market_data,
                    'generated_by': 'fallback_error',
                }
                self.write_status("strategy_error", {"strategy_error": str(e)})
                print(f"⚠️ Strategy analysis failed - using fallback: {e}")

        # Step 2: Risk Manager Validation
        risk_input = dict(signal)
        risk_input.setdefault('position_size', 0.01)
        risk_assessment = self.risk_manager.validate_signal(risk_input)
        print(f"⚠️ Risk assessment: {'Approved' if risk_assessment['approved'] else 'Rejected'}")

        dedupe_reason = self._signal_block_reason(signal)
        if dedupe_reason:
            result = {
                'status': 'rejected',
                'issues': [dedupe_reason],
                'execution_mode': 'blocked',
                'broker_mode': self.broker_api.broker_type,
                'safety_status': 'blocked',
                'fallback_used': False,
                'rejection_reason': dedupe_reason,
            }
            self.log_trade({
                'signal': signal,
                'status': 'rejected',
                'reason': [dedupe_reason],
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
            self.last_result = result
            self.last_execution_mode = 'blocked'
            self.write_status("signal_rejected", {"execution_blockers": [dedupe_reason]})
            return result

        if not risk_assessment['approved']:
            self.notifier.signal_rejected(
                signal.get('symbol', '?'),
                signal.get('action', '?'),
                risk_assessment['issues'],
            )
            self.log_trade({
                'signal': signal,
                'status': 'rejected',
                'reason': risk_assessment['issues'],
                'timestamp': datetime.now().isoformat()
            })
            self.last_result = {'status': 'rejected', 'issues': risk_assessment['issues']}
            self.write_status("signal_rejected")
            return {'status': 'rejected', 'issues': risk_assessment['issues']}

        # Step 3: Hermes AI signal review
        self.pending_signal  = signal
        self.hermes_override = None
        if DRY_RUN and PAPER_FAST_MODE:
            hermes_result = {
                'approved': True,
                'confidence': 100,
                'reason': 'Paper fast mode bypass',
                'risk_notes': '',
                'recommendation': 'execute',
            }
            approved_by_hermes = True
            self.write_status("paper_fast_hermes_bypass")
        else:
            hermes_result = hermes_review_signal(signal)
            approved_by_hermes = hermes_result.get('approved', True)

        # Allow manual /approve to override Hermes rejection
        if not approved_by_hermes and self.hermes_override == 'approve':
            approved_by_hermes = True
            logger.info("Hermes rejection overridden by manual /approve")

        if not approved_by_hermes:
            reason = hermes_result.get('reason', 'Hermes rejected signal')
            conf   = hermes_result.get('confidence', 0)
            logger.info(f"Hermes blocked signal: {signal.get('symbol')} — {reason} (conf={conf})")
            self.notifier.signal_rejected(
                signal.get('symbol', '?'),
                signal.get('action', '?'),
                [f"Hermes: {reason} (conf={conf})"],
            )
            self.log_trade({
                'signal': signal, 'status': 'hermes_blocked',
                'hermes_result': hermes_result,
                'timestamp': datetime.now().isoformat(),
            })
            self.pending_signal = None
            self.last_result = {'status': 'hermes_blocked', 'hermes': hermes_result}
            self.write_status("signal_blocked_by_hermes")
            return {'status': 'hermes_blocked', 'hermes': hermes_result}

        self.pending_signal = None

        # Step 4: Execute Trade (Oanda practice preferred, local paper fallback)
        execution_blockers: list[str] = []
        result = None
        oanda_result, oanda_blocker = self._try_oanda_practice_execution(signal)
        if oanda_result:
            result = oanda_result
            self.notifier.trade_executed(
                signal['symbol'],
                signal['action'],
                int(signal.get('units') or 1),
                signal.get('entry_price') or 0,
                signal.get('stop_loss'),
                signal.get('take_profit'),
            )
            if result.get("order_id"):
                self.active_positions.append({
                    'order_id': result['order_id'],
                    'symbol': signal['symbol'],
                    'entry_price': signal.get('entry_price'),
                    'position_size': int(signal.get('units') or 1),
                })
        else:
            if oanda_blocker:
                execution_blockers.append(oanda_blocker)
            self.notifier.trade_demo(signal.get('symbol', '?'), signal.get('action', '?'))
            self.last_local_paper_trade_at = datetime.now().isoformat()
            result = {
                'status': 'approved_demo',
                'message': 'Local paper fallback - no broker execution',
                'execution_mode': 'local_paper',
                'broker_mode': 'demo',
                'safety_status': 'safe',
                'fallback_used': True,
                'rejection_reason': oanda_blocker,
            }

        # Log the trade
        trade_record = {
            'signal': signal,
            'strategy_analysis': strategy_signal,
            'risk_assessment': risk_assessment,
            'result': result,
            'execution_blockers': execution_blockers,
            'timestamp': datetime.now().isoformat()
        }
        self.log_trade(trade_record)
        self.last_trade_record = trade_record
        self.last_result = result
        self.last_execution_mode = result.get('execution_mode')
        self.execution_blockers = execution_blockers
        self.write_status("signal_processed", {
            "last_execution_mode": self.last_execution_mode,
            "last_oanda_practice_order_at": self.last_oanda_practice_order_at,
            "last_local_paper_trade_at": self.last_local_paper_trade_at,
            "execution_blockers": execution_blockers,
            "oanda_practice_available": self.oanda_practice_available,
            "oanda_practice_default_enabled": self.oanda_practice_default_enabled,
            "local_paper_fallback_enabled": self.local_paper_fallback_enabled,
        })

        return result

    def monitor_positions(self):
        """Monitor open positions and manage risk"""
        for position in self.active_positions[:]:  # Copy to avoid modification issues
            market_data = self.broker_api.get_market_data(position['symbol'])

            if 'bid' in market_data and 'ask' in market_data:
                current_price = (market_data['bid'] + market_data['ask']) / 2

                # Check stop loss
                if position.get('stop_loss') and current_price <= position['stop_loss']:
                    print(f"🛑 Stop loss hit for {position['symbol']}")
                    self.close_position(position, current_price, 'stop_loss')

                # Check take profit
                elif position.get('take_profit') and current_price >= position['take_profit']:
                    print(f"💰 Take profit hit for {position['symbol']}")
                    self.close_position(position, current_price, 'take_profit')

    def close_position(self, position, exit_price, reason):
        """Close a position"""
        if self.config.get('live_trading', False):
            result = self.broker_api.close_position(position['order_id'], position['symbol'])
        else:
            result = {'status': 'closed_demo', 'pnl': (exit_price - position['entry_price']) * position['position_size'] * 100000}

        # Update risk manager
        pnl = result.get('pnl', 0)
        self.risk_manager.update_pnl(pnl)

        # Remove from active positions
        self.active_positions.remove(position)

        # Log closure
        self.log_trade({
            'action': 'close_position',
            'position': position,
            'exit_price': exit_price,
            'reason': reason,
            'pnl': pnl,
            'timestamp': datetime.now().isoformat()
        })

        self.notifier.position_closed(position['symbol'], reason, pnl)
        print(f"📊 Position closed: {position['symbol']} - P&L: ${pnl:.2f}")
        self.last_result = {'status': 'position_closed', 'symbol': position['symbol'], 'reason': reason, 'pnl': pnl}
        self.write_status("position_closed")

    def _supabase_log_paper_trade(self, trade_data: dict):
        """Write a paper trade record to Supabase (non-fatal)."""
        import urllib.request as _req
        sb_url = os.getenv('SUPABASE_URL', '')
        sb_key = os.getenv('SUPABASE_KEY', '')
        if not sb_url or not sb_key:
            return
        signal = trade_data.get('signal', {}) or {}
        result = trade_data.get('result', {}) or {}
        strategy_signal = trade_data.get('strategy_analysis', {}) or {}
        if not signal.get('symbol'):
            return
        symbol = signal.get('symbol', 'UNKNOWN')
        crypto_tickers = ('BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'ADA')
        asset_class = 'crypto' if any(t in symbol.upper() for t in crypto_tickers) else 'forex'
        entry_status = 'open' if result.get('status') in ('approved_demo', 'executed') else 'rejected'
        payload = {
            'symbol': symbol,
            'asset_class': asset_class,
            'timeframe': signal.get('timeframe'),
            'thesis': (
                f"{'DRY_RUN' if DRY_RUN else 'PRACTICE'} | "
                f"{(signal.get('action') or '?').upper()} @ {signal.get('entry_price', '?')} | "
                f"Strategy: {signal.get('strategy', 'nexus_engine')} | "
                f"Confidence: {signal.get('confidence', '?')}%"
            ),
            'entry_idea': json.dumps({
                'action': signal.get('action'),
                'entry_price': signal.get('entry_price'),
                'result_status': result.get('status'),
                'generated_by': strategy_signal.get('generated_by', 'nexus_engine'),
            }),
            'stop_loss': signal.get('stop_loss'),
            'target_price': signal.get('take_profit'),
            'risk_percent': 1.0,
            'tags': ['paper', 'nexus_auto', 'dry_run' if DRY_RUN else 'practice'],
            'entry_status': entry_status,
            'opened_at': datetime.now().isoformat(),
        }
        try:
            url = f"{sb_url}/rest/v1/paper_trading_journal_entries"
            body = json.dumps(payload).encode()
            request = _req.Request(
                url, data=body, method='POST',
                headers={
                    'apikey': sb_key,
                    'Authorization': f'Bearer {sb_key}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=minimal',
                },
            )
            with _req.urlopen(request, timeout=10) as r:
                r.read()
        except Exception as e:
            print(f"⚠️ Paper trade Supabase log failed (non-fatal): {e}")

    def log_trade(self, trade_data):
        """Log trading activity"""
        self.trading_log.append(trade_data)

        # Save to file
        log_file = f"logs/trading_{datetime.now().strftime('%Y%m%d')}.json"
        os.makedirs('logs', exist_ok=True)

        with open(log_file, 'a') as f:
            json.dump(trade_data, f)
            f.write('\n')

        # Persist to Supabase so paper trades appear in the dashboard
        if 'signal' in trade_data:
            self._supabase_log_paper_trade(trade_data)
            signal = trade_data.get("signal") or {}
            result = trade_data.get("result") or {}
            append_jsonl("trades", {
                "created_at": trade_data.get("timestamp") or datetime.now().isoformat(),
                "trade_id": result.get("trade_id") or result.get("order_id"),
                "strategy_id": signal.get("strategy_id") or signal.get("strategy"),
                "symbol": signal.get("symbol"),
                "asset_class": self._signal_asset_class(signal),
                "direction": signal.get("action"),
                "entry_price": signal.get("entry_price"),
                "stop_loss": signal.get("stop_loss"),
                "take_profit": signal.get("take_profit"),
                "position_size": signal.get("position_size"),
                "units": signal.get("units", 1),
                "broker_mode": result.get("broker_mode", self.broker_api.broker_type),
                "execution_mode": result.get("execution_mode", "local_paper"),
                "status": result.get("status"),
                "failure_reason": result.get("rejection_reason"),
                "metadata": {
                    "fallback_used": result.get("fallback_used"),
                    "safety_status": result.get("safety_status"),
                    "execution_blockers": trade_data.get("execution_blockers") or [],
                },
            })

    def start_automated_trading(self):
        """Start automated trading loop"""
        print("🚀 Starting automated trading...")
        self.is_running = True
        self.write_status("automated_trading_started")

        while self.is_running:
            try:
                # Respect halt flag — set by /halt command or by writing logs/trading_engine_halt.flag
                if HALT_FLAG.exists() and not self.halted:
                    self.halted = True
                    self.write_status("halted_by_flag")
                elif not HALT_FLAG.exists() and self.halted:
                    self.halted = False
                    self.write_status("resumed_by_flag")
                if self.halted:
                    time.sleep(self.config.get('check_interval', 60))
                    continue

                # Check for new signals
                signals = self.signal_receiver.get_latest_signals(limit=1)
                for signal in signals:
                    if signal.get('processed_immediately'):
                        continue
                    if signal not in [log.get('signal') for log in self.trading_log[-10:]]:  # Avoid duplicates
                        self.process_signal(signal)

                # Monitor positions
                self.monitor_positions()

                # Risk status check
                risk_status = self.risk_manager.get_risk_status()
                if risk_status.get('risk_limit_hit'):
                    print("⚠️ Risk limit hit - stopping trading")
                    self.notifier.risk_limit_hit(risk_status)
                    self.write_status("risk_limit_hit", {"risk_status": risk_status})
                    self.stop_trading()

                time.sleep(self.config.get('check_interval', 60))

            except KeyboardInterrupt:
                print("🛑 Trading stopped by user")
                break
            except Exception as e:
                print(f"❌ Trading error: {e}")
                self.last_result = {'status': 'error', 'error': str(e)}
                self.write_status("trading_error")
                time.sleep(30)  # Wait before retrying

    def stop_trading(self):
        """Stop automated trading"""
        print("🛑 Stopping trading engine...")
        self.is_running = False
        self.hermes_commands.stop()
        self.write_status("stopped")

    def get_status(self):
        """Get current trading engine status"""
        return {
            'is_running': self.is_running,
            'active_positions': len(self.active_positions),
            'total_signals_processed': len(self.trading_log),
            'risk_status': self.risk_manager.get_risk_status(),
            'broker_connected': self.broker_api.connected,
            'account_info': self.broker_api.get_account_info() if self.broker_api.connected else None
        }

    def get_recent_trades(self, limit: int = 10):
        """Return recent trade log entries for operator endpoints."""
        return self.trading_log[-limit:]

    def get_runtime_status(self):
        """Build verified status for health/status reporting."""
        last_trade_time = None
        if self.trading_log:
            last_trade_time = self.trading_log[-1].get('timestamp')
        safety = evaluate_trading_safety(
            broker_mode='oanda_practice' if self.oanda_practice_default_enabled else self.broker_api.broker_type,
            api_url=os.getenv("OANDA_API_URL", ""),
        )
        return {
            'receiver_status': 'healthy' if self.receiver_started else 'starting',
            'port': self.config.get('signal_port', 5000),
            'service_name': 'com.nexus.trading-engine',
            'safe_mode_active': DRY_RUN and not self.config.get('live_trading', False),
            'safety_status': 'safe' if safety.get('safe') else 'blocked',
            'live_trading': self.config.get('live_trading', False),
            'live_trading_enabled': self.config.get('live_trading', False),
            'auto_trading': self.config.get('auto_trading', False),
            'broker_mode': self.broker_api.broker_type,
            'execution_mode': self.last_execution_mode or 'idle',
            'oanda_practice_available': self.oanda_practice_available,
            'oanda_practice_default_enabled': self.oanda_practice_default_enabled,
            'local_paper_fallback_enabled': self.local_paper_fallback_enabled,
            'broker_connected': self.broker_api.connected,
            'broker_error': getattr(self.broker_api, 'last_error', None),
            'strategy_runner_status': 'paper_fast_mode' if DRY_RUN and PAPER_FAST_MODE else 'lazy_load',
            'supabase_logging_status': 'enabled' if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_KEY') else 'disabled',
            'telegram_status_path': str(ROOT / "logs" / "trading_engine_status.json"),
            'logger_available': True,
            'receiver_port': self.config.get('signal_port', 5000),
            'paper_only': True,
            'dry_run': DRY_RUN,
            'last_signal_time': (self.last_signal or {}).get('timestamp') if self.last_signal else None,
            'last_execution_mode': self.last_execution_mode,
            'last_oanda_practice_order_at': self.last_oanda_practice_order_at,
            'last_local_paper_trade_at': self.last_local_paper_trade_at,
            'last_trade_time': last_trade_time,
            'signals_processed': len(self.trading_log),
            'blockers': list((safety.get('blockers') or [])) + list(self.execution_blockers or []),
        }

def main():
    """Main entry point"""
    engine = NexusTradingEngine()

    # Connect to broker
    if not engine.connect_broker():
        print("❌ Cannot start without broker connection")
        return

    # Start automated trading if enabled
    if engine.config.get('auto_trading', False):
        trading_thread = threading.Thread(
            target=engine.start_automated_trading,
            daemon=True,
            name="TradingLoop",
        )
        trading_thread.start()
        try:
            engine.start_signal_receiver(background=False)
        except KeyboardInterrupt:
            engine.stop_trading()
    else:
        print("📊 Manual mode - send signals to http://localhost:5000/signal/manual")
        print("📈 TradingView webhooks to http://localhost:5000/webhook/tradingview")
        engine.write_status("manual_mode_ready")
        try:
            engine.start_signal_receiver(background=False)
        except KeyboardInterrupt:
            engine.stop_trading()

if __name__ == "__main__":
    main()
