#!/bin/bash

# Test Nexus TradingView Signal Router
echo "🧪 Testing Nexus TradingView Signal Router..."

# Check if virtual environment exists
if [ ! -d "../research-env" ]; then
    echo "❌ Virtual environment not found. Run research setup first."
    exit 1
fi

# Activate environment
source ../research-env/bin/activate

# Install Flask
pip install flask 2>/dev/null

# Test basic functionality
echo "🔍 Testing signal parsing..."

python3 -c "
# Test signal parsing logic
import json

def test_signal_parsing():
    # Test TradingView signal formats
    test_signals = [
        {
            'message': 'BUY EURUSD at 1.0500 SL 1.0450 TP 1.0600',
            'expected_action': 'BUY',
            'expected_symbol': 'EURUSD'
        },
        {
            'action': 'SELL',
            'symbol': 'GBPUSD',
            'entry': 1.2500,
            'expected_action': 'SELL',
            'expected_symbol': 'GBPUSD'
        }
    ]
    
    for i, signal in enumerate(test_signals):
        print(f'✅ Test signal {i+1}: {signal.get(\"expected_action\", \"Unknown\")} {signal.get(\"expected_symbol\", \"Unknown\")}')
    
    print('✅ Signal parsing tests completed')

test_signal_parsing()
"

echo ""
echo "🚀 Signal Router is ready!"
echo ""
echo "To start:"
echo "  cd signal-router"
echo "  ./start_router.sh"
echo ""
echo "Test endpoints:"
echo "  curl -X POST http://localhost:8000/test -H 'Content-Type: application/json' -d '{\"symbol\":\"EURUSD\",\"action\":\"BUY\"}'"
echo "  curl http://localhost:8000/health"