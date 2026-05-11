# 🦞 Nexus AI Trading Engine

**Complete AI-Powered Trading System**

This is the execution layer of your Nexus AI system. It takes research knowledge from the Research Brain and executes trades through a complete AI pipeline.

## Architecture

```
TradingView Signals
        ↓
Signal Receiver (Flask API)
        ↓
Strategy Agent (Codex Analysis)
        ↓
Risk Manager (Position Sizing)
        ↓
Broker API (Oanda/MetaTrader/Demo)
        ↓
Trade Execution & Monitoring


*Before Codex is called, a **vector search** runs against the Supabase knowledge base (embeddings) to retrieve relevant strategies. This reduces model calls and speeds up analysis.*
```

## Quick Start

> ⚠️ **DEVELOPMENT SAFETY:** the system defines a `DRY_RUN = True` flag in `broker_api.py` and `nexus_trading_engine.py`.
> This enforces demo behaviour even if `live_trading` is accidentally set to true. It is automatically enabled when you run locally and can be disabled for production after thorough testing.


### 1. Install Dependencies

```bash
cd ~/nexus-ai/trading-engine
source ../../research-env/bin/activate  # Use same virtual env
pip install -r requirements.txt
```

### 2. Configure Your Broker

Edit `trading_config.json`:

**For Demo Trading (Safe):**
```json
{
  "broker_type": "demo",
  "live_trading": false
}
```

**For Live Trading (Oanda):**
```json
{
  "broker_type": "oanda",
  "live_trading": true,
  "broker_config": {
    "api_url": "https://api-fxtrade.oanda.com",
    "account_id": "YOUR_OANDA_ACCOUNT_ID",
    "api_key": "YOUR_OANDA_API_KEY"
  }
}
```

### 3. Start the Trading Engine

Run in this order to make debugging easier:

```bash
# 1. Start OpenClaw gateway (in separate terminal)
openclaw gateway

# 2. Start the Telegram bot (in separate terminal)
python3 ../telegram_bot.py

# 3. Then in trading-engine directory:
python3 nexus_trading_engine.py
```

```bash
# alternatively start everything via tmux as shown in central guide
```

---

## Signal Sources

### TradingView Webhooks

1. **Create Alert in TradingView:**
   - Go to TradingView chart
   - Create alert with message like: `BUY EURUSD at {{strategy.order.price}} SL {{strategy.order.stop}} TP {{strategy.order.profit}}`

2. **Set Webhook URL:**
   ```
   http://YOUR_SERVER_IP:5000/webhook/tradingview
   ```

### Manual Signals

Send signals via API:

```bash
curl -X POST http://localhost:5000/signal/manual \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "action": "BUY",
    "entry_price": 1.0500,
    "stop_loss": 1.0450,
    "take_profit": 1.0600,
    "timeframe": "H1",
    "strategy": "manual"
  }'
```

## Components

### 🤖 Strategy Agent (`agents/strategy_agent.py`)
- Uses Codex AI to analyze market conditions
- Queries Supabase research knowledge
- Generates trading signals with confidence scores

### ⚠️ Risk Manager (`risk/risk_manager.py`)
- Enforces position sizing rules
- Monitors daily loss limits
- Validates reward/risk ratios
- Manages correlation between positions

### 📡 Signal Receiver (`signals/signal_receiver.py`)
- Flask API for receiving signals
- Supports TradingView webhooks
- Manual signal input
- Signal history and health checks

### 💰 Broker API (`execution/broker_api.py`)
- Unified interface for multiple brokers
- Currently supports: Demo, Oanda, MetaTrader (placeholder)
- Real-time market data
- Order execution and position management

## Configuration Options

### Risk Management
```json
{
  "max_daily_loss": 100.0,
  "max_position_size": 0.01,
  "max_open_positions": 3,
  "risk_per_trade": 0.02,
  "reward_risk_ratio": 2.0
}
```

### Trading Parameters
```json
{
  "auto_trading": true,
  "max_trades_per_day": 5,
  "trading_pairs": ["EURUSD", "GBPUSD"],
  "check_interval": 60
}
```

## API Endpoints

- `POST /webhook/tradingview` - Receive TradingView signals
- `POST /signal/manual` - Send manual signals
- `GET /signals` - Get recent signals
- `GET /health` - Health check

## Monitoring

### Logs
- Trading activity: `logs/trading_YYYYMMDD.json`
- Risk events: `logs/risk_YYYYMMDD.json`
- System events: `logs/system_YYYYMMDD.json`

### Status Check
```bash
curl http://localhost:5000/health
```

## Safety Features

### Risk Controls
- ✅ Daily loss limits
- ✅ Position size limits
- ✅ Maximum open positions
- ✅ Reward/risk ratio validation
- ✅ Correlation monitoring

### Demo Mode
- 🛡️ Paper trading with virtual balance
- 🛡️ No real money at risk
- 🛡️ Full pipeline testing

### Emergency Stops
- Manual stop via Ctrl+C
- Automatic stop on risk limit breach
- Broker connection monitoring

## Integration with Research Brain

The trading engine automatically queries your Supabase research database for:

- Trading strategies from analyzed YouTube content
- Risk management rules from expert analysis
- Market psychology insights
- Technical analysis patterns

## Next Steps

1. **Configure Supabase** in `strategy_agent.py`
2. **Set up your broker** credentials
3. **Test with demo mode** first
4. **Connect TradingView** alerts
5. **Enable automated trading**

## Production Deployment

For live trading:

```bash
# Run in background
nohup python3 nexus_trading_engine.py &

# Monitor logs
tail -f logs/trading_$(date +%Y%m%d).json
```

## Security Notes

- 🔐 Never commit API keys to version control
- 🔐 Use environment variables for sensitive data
- 🔐 Enable 2FA on your broker accounts
- 🔐 Test extensively in demo mode first
- 🔐 Start with small position sizes

---

**Your Nexus AI Hedge Fund is now operational!** 🎯📈

The system combines AI research, risk management, and automated execution into a complete trading solution.