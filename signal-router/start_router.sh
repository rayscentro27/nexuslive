#!/bin/bash

# Nexus TradingView Signal Router Startup Script
echo "🦞 Starting Nexus TradingView Signal Router..."

# Check if virtual environment exists
if [ ! -d "../research-env" ]; then
    echo "❌ Virtual environment not found. Run research setup first."
    exit 1
fi

# Activate environment
source ../research-env/bin/activate

# Install Flask if not already installed
pip install flask 2>/dev/null

# Check if Hermes is running
if ! curl -s http://localhost:8642/health > /dev/null; then
    echo "⚠️  Warning: Hermes gateway not detected on port 8642"
    echo "   Make sure Hermes is running before starting signal router"
fi

# Start the signal router
echo "🚀 Starting signal router on port 8000..."
echo "📡 TradingView webhook URL: http://localhost:8000/webhook/tradingview"
echo "🧪 Test endpoint: http://localhost:8000/test"
echo "💊 Health check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"

python3 tradingview_router.py --host 0.0.0.0 --port 8000