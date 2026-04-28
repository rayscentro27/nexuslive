#!/bin/bash

# Test individual Nexus components
echo "🧪 NEXUS COMPONENT TEST SUITE"
echo "=============================="
echo ""

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local color=$3
    
    echo -n "Testing $name... "
    if curl -s -m 5 "$url" > /dev/null 2>&1; then
        echo "✅ OK"
    else
        echo "❌ FAILED (is it running?)"
    fi
}

# Function to run command
run_command() {
    local name=$1
    local desc=$2
    echo ""
    echo "📝 $name"
    echo "   $desc"
}

# Test Hermes
test_endpoint "Hermes Gateway" "http://localhost:8642/health"

# Test Signal Router  
test_endpoint "Signal Router" "http://localhost:8000/health"

# Test Dashboard
test_endpoint "Dashboard" "http://localhost:3000/api/metrics"

echo ""
echo "════════════════════════════════════════════"
echo ""

# Available test commands
echo "🎯 TEST COMMANDS"
echo ""

run_command "1. Test Single Signal" \
"curl -X POST http://localhost:8000/test \
  -H 'Content-Type: application/json' \
  -d '{\"symbol\":\"EURUSD\",\"action\":\"BUY\",\"entry_price\":1.0500,\"stop_loss\":1.0450,\"take_profit\":1.0600}'"

run_command "2. Get Signal History" \
"curl http://localhost:8000/signals/history?limit=5"

run_command "3. Run Research Pipeline" \
"cd research-engine && source ../research-env/bin/activate && python3 collector.py"

run_command "4. Test Trading Strategy" \
"cd trading-engine && source ../research-env/bin/activate && python3 -c 'from agents.strategy_agent import NexusStrategyAgent; agent = NexusStrategyAgent(); print(\"✅ Strategy agent loaded\")'"

run_command "5. Check Risk Manager" \
"cd trading-engine && source ../research-env/bin/activate && python3 -c 'from risk.risk_manager import NexusRiskManager; rm = NexusRiskManager(); print(\"✅ Risk manager loaded\")'"

run_command "6. Test Telegram Bot" \
"python3 telegram_bot.py"

run_command "7. Verify Embeddings" \
"cd research-engine && python3 - <<'PYEOF'
from supabase import create_client
import os, sys
url=os.getenv('SUPABASE_URL')
key=os.getenv('SUPABASE_KEY')
if not url or not key:
    print('No Supabase credentials set')
    sys.exit(1)

supabase=create_client(url,key)
resp = supabase.table('research').select('id,embedding').limit(1).execute()
print('Embedding entries:', resp.data)
PYEOF"

run_command "8. Vector Search Demo" \
"cd trading-engine && python3 - <<'PYEOF'
from agents.strategy_agent import NexusStrategyAgent
agent = NexusStrategyAgent()
print('Running vector search for \"risk management rules\"...')
print(agent.vector_search('risk management rules', top_k=3))
PYEOF"

run_command "9. Get Dashboard Metrics" \
"curl http://localhost:3000/api/metrics"

run_command "10. View Recent Trades" \
"curl http://localhost:3000/api/trades"

echo ""
echo "════════════════════════════════════════════"
echo ""

# Show what to check for
echo "🔍 WHAT TO LOOK FOR"
echo ""
echo "✅ Hermes: Should show gateway info"
echo "✅ Signal Router: Should show signal processing logs"
echo "✅ Dashboard: Should show metrics and P&L"
echo "✅ Telegram: Should send test alert"
echo "✅ Research: Should process YouTube videos"
echo "✅ Trading: Should analyze market conditions"
echo ""

## Actually run basic checks
echo "════════════════════════════════════════════"
echo ""
echo "🚀 RUNNING QUICK SYSTEM CHECK..."
echo ""

# Check Python imports
python3 << 'PYEOF'
import sys

try:
    print("Checking Python packages:")
    import flask; print("  ✅ Flask")
    import requests; print("  ✅ Requests")
    print("✅ Core dependencies OK")
except ImportError as e:
    print(f"  ⚠️  {e}")
PYEOF

echo ""
echo "✨ Test suite ready!"
echo ""
echo "For detailed testing, run:"
echo "  bash setup_and_test.sh"