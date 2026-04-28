# 🦞 NEXUS AI HEDGE FUND - QUICK START GUIDE

## ⚡ 60-Second Overview

You now have a complete AI trading system with:
- **AI Brain:** OpenClaw (Codex model)
- **Signal Processing:** TradingView webhooks
- **Risk Management:** Automated position sizing
- **Trading Execution:** Multi-broker API
- **Research:** YouTube → Strategy extraction
- **Monitoring:** Real-time dashboard + Telegram alerts

---

## 🚀 QUICK START (5 minutes)

### 1. **Gather Your Credentials** (2 minutes)

You'll need:

#### **Telegram Bot (for alerts)**

> **New requirement:** to enable the vector memory you must set `OPENAI_API_KEY` in your environment or `.env`.  This key is used only for embedding generation and can be the same token you already have for Codex.


1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Type `/newbot` and follow prompts
3. You'll get a **Bot Token** (save it)
   - ⚠️ **Security tip:** if you've ever shared the previous token publicly, run `/revoke` on the old bot and generate a new token immediately.
4. Message @userinfobot to get your **Chat ID** (save it)

> Store these values in the `.env` file or `telegram_config.json` and never commit them to Git. The system now reads from environment variables first.
#### **Supabase (for knowledge storage)**
1. Go to [supabase.com](https://supabase.com)
2. Create free account → new project
3. Go Settings → API
4. Copy **Project URL** and **Anon Key**

#### **OpenAI (already configured!)**
- Your OpenClaw is set up with Codex ✅

### 2. **Run Setup Script** (2 minutes)

```bash
cd ~/nexus-ai
chmod +x setup_and_test.sh
bash setup_and_test.sh
```

The script will:
- Ask for Telegram credentials
- Ask for Supabase credentials  
- Update all config files
- Show you what to run next

### 3. **Start the System** (1 minute)

Open **5 separate terminal windows** and run these commands:

**Terminal 1 - OpenClaw Gateway (THE AI BRAIN)**
```bash
openclaw gateway
```
*This is your AI headquarters - must stay running*

**Terminal 2 - Signal Router**
```bash
cd ~/nexus-ai/signal-router
./start_router.sh
```
*Listens for TradingView alerts*

**Terminal 3 - Dashboard**
```bash
cd ~/nexus-ai
python3 dashboard.py
```
*Visit http://localhost:3000 in browser*

**Terminal 4 - Trading Engine** (optional, demo mode)
```bash
cd ~/nexus-ai/trading-engine
source ../research-env/bin/activate
python3 nexus_trading_engine.py
```

**Terminal 5 - Research Pipeline** (optional, runs hourly)
```bash
cd ~/nexus-ai/research-engine
source ../research-env/bin/activate
bash run_research.sh
```

---

## ✅ VERIFY IT'S WORKING

### Test 1: OpenClaw is running
```bash
curl http://localhost:18789/health
```
**Expected:** JSON response with gateway info ✅

### Test 2: Signal Router is ready
```bash
curl http://localhost:8000/health
```
**Expected:** Shows signals processed ✅

### Test 3: Dashboard is loading
```bash
curl http://localhost:3000/api/metrics
```
**Expected:** Shows P&L and metrics ✅

### Test 4: Send a test signal
```bash
curl -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "action": "BUY",
    "entry_price": 1.0500,
    "stop_loss": 1.0450,
    "take_profit": 1.0600
  }'
```
**Expected:** Signal processed successfully ✅
**Your Telegram will get an alert!** 📱

### Test 5: Check signal history
```bash
curl http://localhost:8000/signals/history?limit=5
```
**Expected:** Shows your test signal ✅

---

## 🎯 CONFIGURE TRADINGVIEW

1. **Create a TradingView Alert on your chart:**
   ```
   Alert Message:
   BUY {{ticker}} at {{close}} SL {{strategy.order.stop}} TP {{strategy.order.profit}}
   ```

2. **Set Webhook URL:**
   ```
   http://YOUR_SERVER_IP:8000/webhook/tradingview
   ```
   
   *(If testing locally: http://localhost:8000/webhook/tradingview)*

3. **When alert triggers:**
   - → Sent to Signal Router
   - → Parsed and validated  
   - → Sent to OpenClaw AI
   - → AI analyzes risk
   - → Trade executed (if approved)
   - → Telegram alert sent 📱

---

## 📊 YOUR DASHBOARD

**Access:** http://localhost:3000

Shows:
- 📈 Today's P&L
- 📊 Active trades
- ⚡ Signals today
- 🤖 System status
- 🔗 Broker connection
- 💰 Account balance

---

## 🧠 SYSTEM ARCHITECTURE

```
Your Mac Mini = AI Operations Server

┌─────────────────────────────────────┐
│     OpenClaw (AI Brain)             │
│     Port 18789                      │
└──────────────┬──────────────────────┘
               │
    ┌──────────┼──────────┐
    ▼          ▼          ▼
Research  Trading    Signal
Engine    Engine     Router
    │          │         │
    ▼          ▼         ▼
Supabase  Broker API  TradingView
(Knowledge) (Execution) (Alerts)
    │          │         │
    └──────────┼─────────┘
               ▼
         Telegram Bot
         (Notifications)
```

---

## 🎯 TESTING IN ORDER

### 1. **OpenClaw Connection** ✅
```bash
openclaw gateway
# Wait for it to start
curl http://localhost:18789/health
```

### 2. **Telegram** ✅
```bash
python3 telegram_bot.py
# Should send test alert to your Telegram
```

### 3. **Dashboard** ✅
```bash
python3 dashboard.py
# Visit http://localhost:3000
```

### 4. **Research Run** ✅
```bash
cd research-engine && ./run_research.sh
# Should process YouTube videos (if configured)
```

### 5. **Strategy Agent** ✅
```bash
cd trading-engine
python3 -c "from agents.strategy_agent import NexusStrategyAgent; print('✅ Loaded')"
```

### 6. **Signal Processing** ✅
```bash
# Send test signal
curl -X POST http://localhost:8000/test \
  -H "Content-Type: application/json" \
  -d '{"symbol":"EURUSD","action":"BUY"}'
```

---

## 🔧 CONFIGURATION FILES

### `telegram_config.json`
```json
{
  "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID",
  "supabase_url": "YOUR_SUPABASE_URL",
  "supabase_key": "YOUR_SUPABASE_ANON_KEY"
}
```

### `trading-engine/trading_config.json`
```json
{
  "broker_type": "demo",      // Change to "oanda" for live
  "live_trading": false,      // Stay false until ready!
  "auto_trading": false
}
```

### `research-engine/collector.py`
Edit the `CHANNELS` list to watch specific YouTube traders

---

## ⚠️ SAFETY GUIDELINES

**DO:**
- ✅ Test everything in DEMO mode first
- ✅ Use small position sizes (0.01 lots)
- ✅ Monitor risk limits closely
- ✅ Keep daily loss limit set
- ✅ Check logs frequently

**DON'T:**
- ❌ Enable live trading until you've tested extensively
- ❌ Leave system unattended
- ❌ Use large position sizes
- ❌ Trade without risk limits configured
- ❌ Commit credentials to git

---

## 📝 LOGGING & MONITORING

**View logs:**
```bash
# Signal router logs
tail -f signal-router/signal-router.log

# Trading engine logs
tail -f trading-engine/logs/trading_*.json

# Research logs
tail -f research-engine/logs/research_*.log
```

**Check system health:**
```bash
# All endpoints
curl http://localhost:18789/health
curl http://localhost:8000/health
curl http://localhost:3000/api/health
```

---

## 🚨 TROUBLESHOOTING

### "Port already in use"
```bash
# Kill existing process
lsof -i :18789  # Check which process
kill -9 <PID>   # Kill it
```

### "Telegram not sending alerts"
- Check bot token is correct
- Check chat ID is correct
- Bot must be messaging the chat
- Run `python3 telegram_bot.py` to test

### "Signal router not receiving"
- Verify TradingView alert format
- Check webhook URL is correct
- Test with: `curl http://localhost:8000/test`

### "OpenClaw gateway not responding"
- Make sure `openclaw gateway` is running
- Check port 18789 is available
- Check OpenClaw config

---

## 🎓 NEXT STEPS

1. ✅ Get all credentials filled in
2. ✅ Run setup script
3. ✅ Start all components
4. ✅ Test each endpoint
5. ✅ Send one test signal
6. ✅ Verify Telegram alert
7. ✅ Run research pipeline
8. ✅ Set up TradingView alert

Then:
- 📊 Monitor dashboard daily
- 📈 Let research pipeline run automatically  
- 🎯 Start with small demo trades
- 💹 Scale up once confident

---

## 📚 DOCUMENTATION

- `NEXUS_SYSTEM_OVERVIEW.md` - Complete architecture
- `research-engine/README.md` - YouTube research pipeline
- `trading-engine/README.md` - Trading execution
- `signal-router/README.md` - TradingView integration

---

## 💬 QUICK COMMAND REFERENCE

```bash
# Start everything
openclaw gateway &
cd signal-router && ./start_router.sh &
python3 dashboard.py &
cd trading-engine && python3 nexus_trading_engine.py &
cd research-engine && ./run_research.sh

# Test everything
bash test_components.sh

# Run setup
bash setup_and_test.sh

# View logs
tail -f signal-router/signal-router.log
tail -f trading-engine/logs/*.json
```

---

**Your AI hedge fund is ready to trade!** 🚀📈

*Start with demo mode. Test thoroughly. Scale carefully.* 🦞

