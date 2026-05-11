# 🦞 Nexus TradingView Signal Router

**Automated Trading Bridge: TradingView → OpenClaw → Live Trading**

This system automatically routes TradingView alerts through your OpenClaw AI agents for intelligent trade execution.

## Architecture

```
TradingView Alert
       ↓
   Webhook POST
       ↓
 Signal Parser
       ↓
OpenClaw Agent
       ↓
 Risk Validation
       ↓
Trade Execution
```

## Quick Start

### 1. Start the Signal Router

```bash
cd ~/nexus-ai/signal-router
./start_router.sh
```

The router will start on `http://localhost:8000`

### 2. Configure TradingView Webhook

In TradingView:

1. **Create an Alert**
2. **Set Webhook URL:**
   ```
   http://YOUR_SERVER_IP:8000/webhook/tradingview
   ```
3. **Alert Message Format:**
   ```
   BUY EURUSD at {{strategy.order.price}} SL {{strategy.order.stop}} TP {{strategy.order.profit}}
   ```

### 3. Test the System

```bash
# Test with curl
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

## API Endpoints

### `POST /webhook/tradingview`
**Main endpoint for TradingView alerts**

**Expected JSON format:**
```json
{
  "symbol": "EURUSD",
  "message": "BUY EURUSD at 1.0500 SL 1.0450 TP 1.0600",
  "timeframe": "H1",
  "strategy": "My Strategy"
}
```

**Response:**
```json
{
  "status": "processed",
  "signal": {
    "action": "BUY",
    "symbol": "EURUSD",
    "entry_price": 1.0500,
    "stop_loss": 1.0450,
    "take_profit": 1.0600
  },
  "result": {
    "status": "routed",
    "openclaw_response": "..."
  }
}
```

### `POST /test`
**Manual signal injection for testing**

### `GET /signals/history`
**Get recent signal processing history**

**Query parameters:**
- `limit` (default: 10) - Number of recent signals to return

### `GET /health`
**System health check**

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-09T...",
  "signals_processed": 42,
  "openclaw_connected": true
}
```

## TradingView Alert Formats

The router automatically parses various TradingView alert formats:

### Format 1: Message-based
```
BUY EURUSD at 1.0500 SL 1.0450 TP 1.0600
```

### Format 2: Structured JSON
```json
{
  "action": "BUY",
  "symbol": "EURUSD",
  "entry": 1.0500,
  "stop": 1.0450,
  "target": 1.0600
}
```

### Format 3: TradingView Placeholders
```
{{strategy.order.action}} {{ticker}} at {{strategy.order.price}} SL {{strategy.order.stop}} TP {{strategy.order.profit}}
```

## Signal Processing Flow

1. **Receive Webhook** - TradingView sends alert
2. **Parse Signal** - Extract action, symbol, prices
3. **Validate** - Check format and required fields
4. **Route to OpenClaw** - Send to AI agent for analysis
5. **Risk Check** - AI validates against risk rules
6. **Execute** - Place trade if approved
7. **Log** - Record all actions

## Configuration

Edit `config.json`:

```json
{
  "openclaw_url": "http://localhost:18789",
  "auth_token": "your_auth_token",
  "host": "0.0.0.0",
  "port": 8000,
  "allowed_symbols": ["EURUSD", "GBPUSD", "USDJPY"],
  "max_signals_per_hour": 10,
  "require_confirmation": false
}
```

## Integration with Nexus Trading Engine

The signal router works alongside your trading engine:

- **Signal Router** receives and parses TradingView alerts
- **OpenClaw Agent** analyzes signals using research knowledge
- **Risk Manager** validates position sizing and limits
- **Broker API** executes approved trades

## Security Features

- **IP Whitelisting** - Only accept from known TradingView IPs
- **Rate Limiting** - Prevent signal spam
- **Signal Validation** - Reject malformed signals
- **Audit Logging** - Complete signal history

## Monitoring

### Check System Health
```bash
curl http://localhost:8000/health
```

### View Recent Signals
```bash
curl "http://localhost:8000/signals/history?limit=5"
```

### Check Logs
```bash
tail -f signal-router.log
```

## Troubleshooting

### OpenClaw Not Connected
```
Error: Connection error to OpenClaw
```
**Solution:** Ensure OpenClaw gateway is running on port 18789

### Invalid Signal Format
```
Could not determine action from: [message]
```
**Solution:** Check TradingView alert message format

### Rate Limit Exceeded
```
Too many signals per hour
```
**Solution:** Increase `max_signals_per_hour` in config or reduce alert frequency

## Production Deployment

For live trading:

```bash
# Run in background
nohup ./start_router.sh &

# Monitor
tail -f signal-router.log
```

## Integration Examples

### Pine Script Alert
```pinescript
alertcondition(condition, "BUY Signal",
  "{{strategy.order.action}} {{ticker}} at {{strategy.order.price}} SL {{strategy.order.stop}} TP {{strategy.order.profit}}")
```

### External System Integration
```python
import requests

signal = {
    "symbol": "EURUSD",
    "action": "BUY",
    "entry_price": 1.0500,
    "stop_loss": 1.0450,
    "take_profit": 1.0600
}

response = requests.post("http://localhost:8000/webhook/tradingview", json=signal)
```

---

**Your AI can now receive TradingView signals and execute trades automatically!** 🎯📈

The signal router bridges your technical analysis with AI-powered execution.