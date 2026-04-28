import json
import requests
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask.cli import show_server_banner

class SignalReceiver:
    """Trading Signal Receiver - Accepts signals from TradingView and other sources"""

    def __init__(self, port=5000):
        self.port = port
        self.app = Flask(__name__)
        self.signals = []
        self.started_at = datetime.now().isoformat()
        self.setup_routes()

    def setup_routes(self):
        """Set up Flask routes for signal reception"""

        @self.app.route('/webhook/tradingview', methods=['POST'])
        def tradingview_webhook():
            """Receive signals from TradingView webhooks"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data received'}), 400

                signal = self.parse_tradingview_signal(data)
                self.signals.append(signal)

                print(f"📈 TradingView Signal Received: {signal}")

                return jsonify({'status': 'signal_received', 'signal': signal}), 200

            except Exception as e:
                print(f"Error processing TradingView signal: {e}")
                return jsonify({'error': str(e)}), 500

        @self.app.route('/signal/manual', methods=['POST'])
        def manual_signal():
            """Accept manual trading signals"""
            try:
                data = request.get_json()
                signal = {
                    'source': 'manual',
                    'timestamp': datetime.now().isoformat(),
                    'symbol': data.get('symbol', 'EURUSD'),
                    'action': data.get('action', 'BUY'),
                    'entry_price': data.get('entry_price'),
                    'stop_loss': data.get('stop_loss'),
                    'take_profit': data.get('take_profit'),
                    'timeframe': data.get('timeframe', 'H1'),
                    'strategy': data.get('strategy', 'manual'),
                    'confidence': data.get('confidence', 50)
                }

                self.signals.append(signal)
                print(f"📊 Manual Signal Received: {signal}")

                return jsonify({'status': 'signal_received', 'signal': signal}), 200

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/signals', methods=['GET'])
        def get_signals():
            """Get recent signals"""
            return jsonify({
                'signals': self.signals[-10:],  # Last 10 signals
                'count': len(self.signals)
            })

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'signals_received': len(self.signals)
            })

        @self.app.route('/status', methods=['GET'])
        def status():
            """Detailed status endpoint for operator tooling."""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'started_at': self.started_at,
                'signals_received': len(self.signals),
                'last_signal': self.signals[-1] if self.signals else None,
            })

    def parse_tradingview_signal(self, data):
        """Parse TradingView webhook data into standardized signal format"""
        # TradingView typically sends alerts in various formats
        # This handles common patterns

        signal = {
            'source': 'tradingview',
            'timestamp': datetime.now().isoformat(),
            'raw_data': data
        }

        # Extract common TradingView alert fields
        if 'symbol' in data:
            signal['symbol'] = data['symbol']
        elif 'ticker' in data:
            signal['symbol'] = data['ticker']

        # Parse action/signal
        message = data.get('message', '').upper()
        if 'BUY' in message or 'LONG' in message:
            signal['action'] = 'BUY'
        elif 'SELL' in message or 'SHORT' in message:
            signal['action'] = 'SELL'
        else:
            signal['action'] = data.get('action', 'HOLD')

        # Extract prices if available
        signal['entry_price'] = data.get('entry')
        signal['stop_loss'] = data.get('stop')
        signal['take_profit'] = data.get('target')

        # Additional metadata
        signal['timeframe'] = data.get('timeframe', 'H1')
        signal['strategy'] = data.get('strategy', 'tradingview')
        signal['confidence'] = data.get('confidence', 75)

        return signal

    def start_server(self):
        """Start the signal receiver server"""
        # Keep launchd stderr focused on actual failures, not Flask dev-server noise.
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        self.app.logger.disabled = True
        try:
            import flask.cli
            flask.cli.show_server_banner = lambda *args, **kwargs: None
        except Exception:
            pass

        print(f"🚀 Starting Signal Receiver on port {self.port}")
        print(f"📡 TradingView webhook URL: http://localhost:{self.port}/webhook/tradingview")
        print(f"📊 Manual signals URL: http://localhost:{self.port}/signal/manual")
        print(f"💊 Health check URL: http://localhost:{self.port}/health")

        self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False, threaded=True)

    def get_latest_signals(self, limit=5):
        """Get the most recent signals"""
        return self.signals[-limit:] if self.signals else []

    def clear_signals(self):
        """Clear all stored signals"""
        self.signals = []
