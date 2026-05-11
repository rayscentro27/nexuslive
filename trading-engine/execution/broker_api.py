import os
import requests
import json
import time
from datetime import datetime

# Keep broker execution aligned with the engine's safety posture.
DRY_RUN = os.getenv('NEXUS_DRY_RUN', 'true').lower() == 'true'

class BrokerAPI:
    """Unified Broker API Interface - Supports multiple brokers"""

    def __init__(self, broker_type="demo", config=None):
        self.broker_type = broker_type
        self.config = config or self.get_default_config()
        self.session = None
        self.connected = False

    def get_default_config(self):
        """Get default configuration for different brokers"""
        configs = {
            'oanda': {
                'api_url': os.getenv('OANDA_API_URL', 'https://api-fxpractice.oanda.com'),
                'account_id': os.getenv('OANDA_ACCOUNT_ID', ''),
                'api_key': os.getenv('OANDA_API_KEY', '')
            },
            'metatrader': {
                'mt4_server': 'localhost:8080',  # Would need MT4 API bridge
                'account': 'YOUR_MT4_ACCOUNT',
                'password': 'YOUR_MT4_PASSWORD'
            },
            'demo': {
                'balance': 10000.0,
                'leverage': 100,
                'spread': 0.0002
            }
        }
        return configs.get(self.broker_type, configs['demo'])

    def connect(self):
        """Connect to broker API"""
        try:
            if self.broker_type == 'demo':
                print("⚠️ DRY_RUN enabled - skipping real broker connection")
                self.connected = True
            elif self.broker_type == 'oanda':
                self.session = requests.Session()
                self.session.headers.update({
                    'Authorization': f'Bearer {self.config["api_key"]}',
                    'Content-Type': 'application/json'
                })
                response = self.session.get(f'{self.config["api_url"]}/v3/accounts/{self.config["account_id"]}')
                self.connected = response.status_code == 200
            elif self.broker_type == 'metatrader':
                self.connected = False  # Placeholder
            else:  # demo
                self.connected = True
            return self.connected
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def get_account_info(self):
        """Get account information"""
        if not self.connected:
            return {'error': 'Not connected'}

        if self.broker_type == 'demo':
            balance = self.config.get('balance', 100000.0)
            leverage = self.config.get('leverage', 100)
            return {
                'balance': balance,
                'equity': balance,
                'margin_used': 0,
                'margin_available': balance * leverage,
                'leverage': leverage,
            }

        elif self.broker_type == 'oanda':
            try:
                response = self.session.get(f'{self.config["api_url"]}/v3/accounts/{self.config["account_id"]}')
                if response.status_code == 200:
                    data = response.json()
                    account = data['account']
                    return {
                        'balance': float(account['balance']),
                        'equity': float(account['NAV']),
                        'margin_used': float(account['marginUsed']),
                        'margin_available': float(account['marginAvailable']),
                        'leverage': 50  # Oanda default
                    }
            except Exception as e:
                return {'error': str(e)}

        return {'error': 'Unsupported broker'}

    def get_market_data(self, symbol, timeframe='H1'):
        """Get current market data"""
        if self.broker_type == 'demo':
            # Simulate market data
            base_price = 1.0500 if 'EURUSD' in symbol else 1.2500
            spread = self.config['spread']
            return {
                'symbol': symbol,
                'bid': base_price - spread/2,
                'ask': base_price + spread/2,
                'spread': spread,
                'timestamp': datetime.now().isoformat()
            }

        elif self.broker_type == 'oanda':
            try:
                # Get latest price
                response = self.session.get(
                    f'{self.config["api_url"]}/v3/instruments/{symbol}/candles',
                    params={'count': 1, 'granularity': timeframe}
                )
                if response.status_code == 200:
                    data = response.json()
                    candle = data['candles'][0]
                    return {
                        'symbol': symbol,
                        'bid': float(candle['bid']['c']),
                        'ask': float(candle['ask']['c']),
                        'spread': float(candle['ask']['c']) - float(candle['bid']['c']),
                        'timestamp': candle['time']
                    }
            except Exception as e:
                return {'error': str(e)}

        return {'error': 'Unsupported broker'}

    def place_order(self, order):
        """Place a trading order"""
        if not self.connected:
            return {'error': 'Not connected'}

        order_data = {
            'symbol': order.get('symbol'),
            'type': order.get('type', 'market'),  # market, limit, stop
            'side': order.get('side', 'buy'),  # buy, sell
            'size': order.get('size', 0.01),
            'price': order.get('price'),  # for limit/stop orders
            'stop_loss': order.get('stop_loss'),
            'take_profit': order.get('take_profit')
        }

        # handle demo mode or global dry-run
        if self.broker_type == 'demo' or DRY_RUN:
            # Simulate order execution
            if DRY_RUN and self.broker_type != 'demo':
                print("⚠️ DRY_RUN override - simulating order instead of placing real trade")
            market_data = self.get_market_data(order_data['symbol'])
            if order_data['side'] == 'buy':
                entry_price = market_data['ask']
            else:
                entry_price = market_data['bid']

            return {
                'order_id': f"demo_{int(time.time())}",
                'status': 'filled',
                'entry_price': entry_price,
                'size': order_data['size'],
                'timestamp': datetime.now().isoformat()
            }

        elif self.broker_type == 'oanda':
            try:
                # Oanda requires underscore format: EURUSD → EUR_USD
                raw_symbol = order_data['symbol']
                if '_' not in raw_symbol and len(raw_symbol) == 6:
                    instrument = raw_symbol[:3] + '_' + raw_symbol[3:]
                else:
                    instrument = raw_symbol
                # Negative units = SELL on Oanda
                units = int(order_data['size'] * 100000)
                if order_data['side'].lower() in ('sell', 'short'):
                    units = -units
                oanda_order = {
                    'order': {
                        'instrument': instrument,
                        'units': str(units),
                        'type': 'MARKET',
                        'positionFill': 'DEFAULT'
                    }
                }

                if order_data['stop_loss']:
                    oanda_order['order']['stopLossOnFill'] = {
                        'price': str(order_data['stop_loss'])
                    }

                if order_data['take_profit']:
                    oanda_order['order']['takeProfitOnFill'] = {
                        'price': str(order_data['take_profit'])
                    }

                response = self.session.post(
                    f'{self.config["api_url"]}/v3/accounts/{self.config["account_id"]}/orders',
                    json=oanda_order
                )

                if response.status_code == 201:
                    data = response.json()
                    fill = data.get('orderFillTransaction', {})
                    create = data.get('orderCreateTransaction', {})
                    return {
                        'order_id': create.get('id', fill.get('orderID', 'unknown')),
                        'status': 'filled' if fill else 'created',
                        'entry_price': float(fill['price']) if fill.get('price') else None,
                        'size': order_data['size'],
                        'timestamp': fill.get('time', create.get('time')),
                        'instrument': instrument,
                        'raw': data,
                    }
                else:
                    return {'error': f'Oanda API error: {response.text}'}

            except Exception as e:
                return {'error': str(e)}

        return {'error': 'Unsupported broker'}

    def close_position(self, position_id, symbol=None):
        """Close an open position"""
        if not self.connected:
            return {'error': 'Not connected'}

        if self.broker_type == 'demo':
            return {
                'status': 'closed',
                'pnl': 25.50,  # Simulated P&L
                'timestamp': datetime.now().isoformat()
            }

        elif self.broker_type == 'oanda':
            try:
                # Normalize symbol format for Oanda
                if symbol and '_' not in symbol and len(symbol) == 6:
                    oanda_symbol = symbol[:3] + '_' + symbol[3:]
                else:
                    oanda_symbol = symbol
                # Close all positions for the instrument
                response = self.session.put(
                    f'{self.config["api_url"]}/v3/accounts/{self.config["account_id"]}/positions/{oanda_symbol}/close'
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        'status': 'closed',
                        'pnl': float(data['longOrderFillTransaction']['pl']) if 'longOrderFillTransaction' in data else 0,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    return {'error': f'Oanda API error: {response.text}'}

            except Exception as e:
                return {'error': str(e)}

        return {'error': 'Unsupported broker'}
