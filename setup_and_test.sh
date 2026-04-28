#!/bin/bash

# 🦞 Nexus AI System - Complete Setup & Testing Guide
# This script walks through the complete system setup and testing

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║    🦞 NEXUS AI HEDGE FUND - SETUP & TEST HARNESS          ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Step 1: Check prerequisites
echo -e "${BLUE}📋 STEP 1: Checking Prerequisites${NC}"
echo "==========================================="

# Activate virtual environment first
echo "Activating virtual environment..."
if [ -f "research-env/bin/activate" ]; then
    source research-env/bin/activate
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${RED}❌ Virtual environment not found. Run this from ~/nexus-ai directory${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python 3 found${NC}"

if ! command -v pip &> /dev/null; then
    echo -e "${RED}❌ pip not found${NC}"
    exit 1
fi
echo -e "${GREEN}✅ pip found${NC}"

echo ""

# Step 2: Get Telegram credentials
echo -e "${BLUE}📱 STEP 2: Configure Telegram${NC}"
echo "==========================================="
echo "To get your Telegram bot token:"
echo "1. Message @BotFather on Telegram"
echo "2. Type: /newbot"
echo "3. Follow the prompts and get your token"
echo ""
echo "To get your Chat ID:"
echo "1. Message your bot or add it to a group"
echo "2. Message @userinfobot"
echo "3. It will show your Chat ID"
echo ""

read -p "Enter your Telegram Bot Token (or press Enter to skip): " TELEGRAM_TOKEN
read -p "Enter your Telegram Chat ID (or press Enter to skip): " TELEGRAM_CHAT_ID

if [ ! -z "$TELEGRAM_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
    echo -e "${GREEN}✅ Telegram credentials received${NC}"
else
    echo -e "${YELLOW}⚠️  Telegram skipped${NC}"
fi

echo ""

# Step 3: Get Supabase credentials
echo -e "${BLUE}🗄️  STEP 3: Configure Supabase${NC}"
echo "==========================================="
echo "Get your Supabase credentials from:"
echo "1. Go to supabase.com"
echo "2. Create a new project (if needed)"
echo "3. Go to Settings → API"
echo "4. Copy the Project URL and Anon Key"
echo ""

read -p "Enter your Supabase Project URL (or press Enter to skip): " SUPABASE_URL
read -p "Enter your Supabase Anon Key (or press Enter to skip): " SUPABASE_KEY
echo ""
# Step 3.5: Hugging Face token for embeddings

read -p "Enter your Hugging Face token (or press Enter to skip): " HF_TOKEN

if [ ! -z "$HF_TOKEN" ]; then
    echo -e "${GREEN}✅ Hugging Face token received${NC}"
else
    echo -e "${YELLOW}⚠️  Hugging Face skipped (vector search will be limited)${NC}"
fi

if [ ! -z "$SUPABASE_URL" ] && [ ! -z "$SUPABASE_KEY" ]; then
    echo -e "${GREEN}✅ Supabase credentials received${NC}"
else
    echo -e "${YELLOW}⚠️  Supabase skipped${NC}"
fi

echo ""

# Step 4: Update configuration files
echo -e "${BLUE}⚙️  STEP 4: Updating Configuration Files${NC}"
echo "==========================================="

# Update telegram_config.json and .env
if [ ! -z "$TELEGRAM_TOKEN" ] && [ ! -z "$TELEGRAM_CHAT_ID" ]; then
    python3 << EOF
import json

config = {
    "bot_token": "$TELEGRAM_TOKEN",
    "chat_id": "$TELEGRAM_CHAT_ID",
    "enabled": True,
    "alert_level": "INFO",
    "include_charts": True,
    "include_metrics": True,
    "nexus_api_url": "http://localhost:3000",
    "hermes_url": "http://localhost:8642",
    "supabase_url": "$SUPABASE_URL",
    "supabase_key": "$SUPABASE_KEY"
}

with open('telegram_config.json', 'w') as f:
    json.dump(config, f, indent=2)

print("✅ telegram_config.json updated")
EOF
fi

# store HF_TOKEN in .env if provided
if [ ! -z "$HF_TOKEN" ]; then
    # append or replace in .env
    if grep -q "^HF_TOKEN" .env 2>/dev/null; then
        sed -i '' "s/^HF_TOKEN=.*/HF_TOKEN=$HF_TOKEN/" .env
    else
        echo "HF_TOKEN=$HF_TOKEN" >> .env
    fi
    echo -e "✅ .env updated with HF_TOKEN"
fi

echo ""

# Step 5: Display system components
echo -e "${BLUE}🔧 STEP 5: System Components${NC}"
echo "==========================================="
echo ""
echo "Your Nexus AI system includes:"
echo ""
echo "1️⃣  Hermes Gateway (port 8642)"
echo "   └─ AI brain for trading decisions"
echo ""
echo "2️⃣  Signal Router (port 8000)"
echo "   └─ TradingView webhook integration"
echo ""
echo "3️⃣  Dashboard (port 3000)"
echo "   └─ Real-time metrics & monitoring"
echo ""
echo "4️⃣  Telegram Bot"
echo "   └─ Trading alerts & notifications"
echo ""
echo "5️⃣  Research Engine"
echo "   └─ YouTube → Strategy extraction"
echo ""
echo "6️⃣  Trading Engine"
echo "   └─ Signal → Execution"
echo ""

# Step 6: Show testing sequence
echo -e "${BLUE}🧪 STEP 6: Testing Sequence${NC}"
echo "==========================================="
echo ""
echo "Run these commands in separate terminal windows:"
echo ""
echo -e "${YELLOW}Terminal 1 - Hermes Gateway:${NC}"
echo "  hermes gateway"
echo ""
echo -e "${YELLOW}Terminal 2 - Signal Router:${NC}"
echo "  cd signal-router && ./start_router.sh"
echo ""
echo -e "${YELLOW}Terminal 3 - Dashboard:${NC}"
echo "  python3 dashboard.py"
echo ""
echo -e "${YELLOW}Terminal 4 - Research Engine (6 hours interval):${NC}"
echo "  cd research-engine && ./run_research.sh"
echo ""
echo -e "${YELLOW}Terminal 5 - Strategy Agent:${NC}"
echo "  cd trading-engine && python3 nexus_trading_engine.py"
echo ""

# Step 7: Generate test commands
echo -e "${BLUE}📝 STEP 7: Test Commands${NC}"
echo "==========================================="
echo ""

cat > /tmp/nexus_test_commands.sh << 'EOF'
#!/bin/bash

echo "🧪 NEXUS SYSTEM TEST COMMANDS"
echo "=============================="
echo ""

echo "1️⃣  TEST HERMES GATEWAY:"
echo "   curl http://localhost:8642/health"
echo ""

echo "2️⃣  TEST SIGNAL ROUTER:"
echo "   curl http://localhost:8000/health"
echo ""

echo "3️⃣  TEST DASHBOARD:"
echo "   curl http://localhost:3000/api/metrics"
echo ""

echo "4️⃣  SEND TEST SIGNAL:"
echo "   curl -X POST http://localhost:8000/test \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"symbol\":\"EURUSD\",\"action\":\"BUY\",\"entry_price\":1.0500}'"
echo ""

echo "5️⃣  RESEARCH PIPELINE TEST:"
echo "   cd research-engine && python3 collector.py"
echo ""

echo "6️⃣  VIEW SIGNAL HISTORY:"
echo "   curl http://localhost:8000/signals/history?limit=5"
echo ""

echo "7️⃣  TELEGRAM TEST (if configured):"
echo "   python3 telegram_bot.py"
echo ""
EOF

chmod +x /tmp/nexus_test_commands.sh
cat /tmp/nexus_test_commands.sh

echo ""

# Step 8: Final instructions
echo -e "${BLUE}✨ STEP 8: Ready to Launch${NC}"
echo "==========================================="
echo ""
echo -e "${GREEN}Configuration complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Open 5-6 terminal windows"
echo "2. Run the commands from STEP 6 in each window"
echo "3. Use the test commands from STEP 7 to verify connectivity"
echo "4. Access dashboard at http://localhost:3000"
echo "5. Start trading!"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANT:${NC}"
echo "- Keep Hermes gateway running (it's the AI brain)"
echo "- Signal router needs to be active to receive TradingView alerts"
echo "- Dashboard should auto-refresh with metrics"
echo "- Telegram alerts will send to your configured chat"
echo ""

echo -e "${BLUE}📚 For more info:${NC}"
echo "  NEXUS_SYSTEM_OVERVIEW.md - Complete architecture"
echo "  research-engine/README.md - Research pipeline docs"
echo "  trading-engine/README.md - Trading engine docs"
echo "  signal-router/README.md - Signal router docs"
echo ""

echo -e "${GREEN}🚀 NEXUS AI is ready to launch!${NC}"