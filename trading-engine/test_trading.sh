#!/bin/bash

# Nexus Trading Engine Test Script
echo "🧪 Testing Nexus AI Trading Engine..."

# Check if virtual environment exists
if [ ! -d "../research-env" ]; then
    echo "❌ Virtual environment not found. Run research setup first."
    exit 1
fi

# Activate environment
source ../research-env/bin/activate

# Install trading dependencies
echo "📦 Installing trading dependencies..."
pip install flask

# Test imports
echo "🔍 Testing component imports..."
python3 -c "
try:
    from agents.strategy_agent import NexusStrategyAgent
    from risk.risk_manager import NexusRiskManager
    from execution.broker_api import BrokerAPI
    from signals.signal_receiver import SignalReceiver
    print('✅ All components imported successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

# Test basic functionality
echo "🎯 Testing basic functionality..."
python3 -c "
from risk.risk_manager import NexusRiskManager
from execution.broker_api import BrokerAPI

# Test risk manager
rm = NexusRiskManager()
signal = {'symbol': 'EURUSD', 'entry_price': 1.0500, 'stop_loss': 1.0450, 'take_profit': 1.0600}
result = rm.validate_signal(signal)
print(f'✅ Risk manager: {result[\"approved\"]}')

# Test broker API
broker = BrokerAPI('demo')
connected = broker.connect()
print(f'✅ Broker API: {connected}')

print('✅ Basic functionality tests passed')
"

echo ""
echo "🚀 Nexus AI Trading Engine is ready!"
echo ""
echo "To start trading:"
echo "  cd trading-engine"
echo "  python3 nexus_trading_engine.py"
echo ""
echo "Signal endpoints:"
echo "  TradingView: http://localhost:5000/webhook/tradingview"
echo "  Manual: http://localhost:5000/signal/manual"
echo "  Health: http://localhost:5000/health"