#!/usr/bin/env python3
"""
Nexus TradingView Signal Router
Receives TradingView webhooks, parses signals, and sends Telegram alerts.

Architecture:
TradingView Alert → Webhook → Signal Parser → Telegram Alert → OpenClaw (reads it)
"""

import os
import json
import requests
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('signal-router.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SignalRouter')

class TradingViewSignalRouter:
    """Receives TradingView webhooks and sends Telegram alerts"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.trading_engine_url = os.getenv("TRADING_ENGINE_URL", "http://127.0.0.1:5000")
        self.app = Flask(__name__)
        self.signal_history = []
        self.setup_routes()

        if self.bot_token and self.chat_id:
            logger.info("🦞 TradingView Signal Router initialized (Telegram ready)")
        else:
            logger.warning("🦞 Signal Router started — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")

    def setup_routes(self):
        """Set up Flask routes for signal processing"""

        @self.app.route('/webhook/tradingview', methods=['POST'])
        def tradingview_webhook():
            """Main TradingView webhook endpoint"""
            try:
                data = request.get_json()
                if not data:
                    logger.warning("No JSON data received")
                    return jsonify({'error': 'No data received'}), 400

                logger.info(f"📈 Received TradingView signal: {data}")

                # Parse and validate signal
                signal = self.parse_tradingview_signal(data)
                if not signal:
                    return jsonify({'error': 'Invalid signal format'}), 400

                # Send Telegram alert
                result = self.notify_telegram(signal)

                # Forward to trading engine
                engine_result = self.forward_to_trading_engine(data)

                # Store signal history
                self.signal_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'raw_signal': data,
                    'parsed_signal': signal,
                    'routing_result': result,
                    'engine_result': engine_result,
                })

                logger.info(f"✅ Signal processed: {signal.get('action')} {signal.get('symbol')}")
                return jsonify({
                    'status': 'processed',
                    'signal': signal,
                    'result': result,
                    'engine': engine_result,
                }), 200

            except Exception as e:
                logger.error(f"Error processing TradingView signal: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/signals/history', methods=['GET'])
        def get_signal_history():
            """Get recent signal processing history"""
            limit = int(request.args.get('limit', 10))
            return jsonify({
                'signals': self.signal_history[-limit:],
                'total_processed': len(self.signal_history)
            })

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'signals_processed': len(self.signal_history),
                'telegram_configured': bool(self.bot_token and self.chat_id)
            })

        @self.app.route('/test', methods=['POST'])
        def test_signal():
            """Test endpoint for manual signal injection"""
            try:
                data = request.get_json()
                logger.info(f"🧪 Test signal received: {data}")

                signal = {
                    'source': 'test',
                    'timestamp': datetime.now().isoformat(),
                    'symbol': data.get('symbol', 'EURUSD'),
                    'action': data.get('action', 'BUY'),
                    'entry_price': data.get('entry_price'),
                    'stop_loss': data.get('stop_loss'),
                    'take_profit': data.get('take_profit'),
                    'timeframe': data.get('timeframe', 'H1'),
                    'strategy': data.get('strategy', 'test'),
                    'confidence': data.get('confidence', 100)
                }

                result = self.notify_telegram(signal)

                return jsonify({
                    'status': 'test_processed',
                    'signal': signal,
                    'result': result
                }), 200

            except Exception as e:
                logger.error(f"Test signal error: {e}")
                return jsonify({'error': str(e)}), 500

    def parse_tradingview_signal(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse TradingView webhook data into standardized signal format"""

        # TradingView alert formats can vary, handle common patterns
        signal = {
            'source': 'tradingview',
            'timestamp': datetime.now().isoformat(),
            'raw_data': data
        }

        # Extract symbol
        signal['symbol'] = (
            data.get('symbol') or
            data.get('ticker') or
            data.get('instrument') or
            'EURUSD'  # Default
        )

        # Parse message for action and details
        message = data.get('message', '').upper()

        # Determine action
        if any(keyword in message for keyword in ['BUY', 'LONG', 'ENTER LONG']):
            signal['action'] = 'BUY'
        elif any(keyword in message for keyword in ['SELL', 'SHORT', 'ENTER SHORT']):
            signal['action'] = 'SELL'
        elif 'CLOSE' in message or 'EXIT' in message:
            signal['action'] = 'CLOSE'
        else:
            # Try to extract from other fields
            action = data.get('action', '').upper()
            if action in ['BUY', 'SELL', 'CLOSE']:
                signal['action'] = action
            else:
                logger.warning(f"Could not determine action from: {message}")
                return None

        # Extract prices using TradingView placeholders
        signal['entry_price'] = self.extract_price(data, ['entry', 'price', 'open'])
        signal['stop_loss'] = self.extract_price(data, ['stop', 'sl', 'stop_loss'])
        signal['take_profit'] = self.extract_price(data, ['target', 'tp', 'take_profit', 'limit'])

        # Additional metadata
        signal['timeframe'] = data.get('timeframe', data.get('interval', 'H1'))
        signal['strategy'] = data.get('strategy', 'tradingview')
        signal['alert_name'] = data.get('alert_name', 'Unknown Alert')
        signal['confidence'] = data.get('confidence', 75)

        # Validate required fields
        if not signal.get('symbol'):
            logger.error("No symbol found in signal")
            return None

        logger.info(f"📊 Parsed signal: {signal['action']} {signal['symbol']} @ {signal.get('entry_price', 'MKT')}")
        return signal

    def extract_price(self, data: Dict, keys: list) -> Optional[float]:
        """Extract price from various possible TradingView field names"""
        for key in keys:
            if key in data:
                try:
                    return float(data[key])
                except (ValueError, TypeError):
                    continue

        # Try to extract from message using common patterns
        message = data.get('message', '')
        import re

        # Look for patterns like "SL: 1.2345" or "Stop: 1.2345"
        for key in keys:
            pattern = rf'{key}[:\s]+(\d+\.?\d*)'
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        return None

    def forward_to_trading_engine(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Forward the raw signal payload to the trading engine's webhook."""
        try:
            url = f"{self.trading_engine_url}/webhook/tradingview"
            resp = requests.post(url, json=raw_data, timeout=5)
            if resp.status_code == 200:
                logger.info(f"✅ Signal forwarded to trading engine")
                return {'status': 'forwarded', 'code': resp.status_code}
            else:
                logger.warning(f"Trading engine returned {resp.status_code}: {resp.text[:200]}")
                return {'status': 'error', 'code': resp.status_code}
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not reach trading engine: {e}")
            return {'status': 'unreachable', 'error': str(e)}

    def notify_telegram(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Send signal alert to Telegram (OpenClaw reads it as the AI agent)"""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram not configured — skipping notification")
            return {'status': 'skipped', 'reason': 'telegram not configured'}

        action = signal.get('action', 'N/A')
        symbol = signal.get('symbol', 'N/A')
        action_emoji = '📈' if action == 'BUY' else '📉' if action == 'SELL' else '🔄'

        if action == 'CLOSE':
            text = (
                f"<b>{action_emoji} CLOSE SIGNAL</b>\n\n"
                f"<b>Symbol:</b> {symbol}\n"
                f"<b>Strategy:</b> {signal.get('strategy', 'N/A')}\n"
                f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            )
        else:
            text = (
                f"<b>{action_emoji} TRADING SIGNAL</b>\n\n"
                f"<b>Symbol:</b> {symbol}\n"
                f"<b>Action:</b> {action}\n"
                f"<b>Entry:</b> {signal.get('entry_price', 'Market')}\n"
                f"<b>Stop Loss:</b> {signal.get('stop_loss', 'N/A')}\n"
                f"<b>Take Profit:</b> {signal.get('take_profit', 'N/A')}\n"
                f"<b>Timeframe:</b> {signal.get('timeframe', 'H1')}\n"
                f"<b>Confidence:</b> {signal.get('confidence', 'N/A')}%\n"
                f"<b>Strategy:</b> {signal.get('strategy', 'N/A')}\n"
                f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>"
            )

        try:
            from lib import hermes_gate

            hermes_gate.record_digest_item('trading_digest', text)
            logger.info(f"✅ Trading signal recorded for digest: {action} {symbol}")
            return {'status': 'digest_recorded', 'timestamp': datetime.now().isoformat()}
        except Exception as e:
            logger.error(f"Digest record failed: {e}")
            return {'status': 'error', 'error': str(e)}

    def start_router(self, host: str = '127.0.0.1', port: int = 8000, debug: bool = False):
        """Start the signal router server"""
        logger.info(f"🚀 Starting Signal Router on {host}:{port}")
        logger.info(f"📡 TradingView webhook URL: http://{host}:{port}/webhook/tradingview")
        logger.info(f"🧪 Test endpoint: http://{host}:{port}/test")
        logger.info(f"💊 Health check: http://{host}:{port}/health")

        self.app.run(host=host, port=port, debug=debug)

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Nexus TradingView Signal Router')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to (default: localhost only)')
    parser.add_argument('--port', type=int, default=8000, help='Port to listen on')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    router = TradingViewSignalRouter()

    router.start_router(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    main()
