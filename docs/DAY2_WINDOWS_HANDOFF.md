# Day 2 — Windows / Oracle VM Handoff
# Generated: 2026-04-17

## OVERVIEW
Mac Mini Day 1 is complete — all 9 Mac-side workers are implemented and running.
This document covers the 3 remaining tasks that MUST be done from the Windows machine.

---

## MACHINE BOUNDARY REMINDER
- ✅ Mac Mini: OpenClaw, workers, signal router, dashboard, Telegram, research, Ollama
- ❌ Oracle VM: managed from Windows ONLY (SSH, PM2, nginx, certbot, git deploy)
- ❌ Do NOT SSH to Oracle from Mac Mini

---

## TASK 1 — Oracle VM Deploy (nexus-oracle-api)

### On Windows machine, SSH to Oracle:
```bash
ssh ubuntu@api.goclearonline.cc
```

### Deploy steps:
```bash
cd /opt
git clone https://github.com/YOUR_REPO/nexus-oracle-api.git  # or git pull if already cloned
cd nexus-oracle-api
npm install
cp .env.example .env    # fill in values below
pm2 start ecosystem.config.js --env production
pm2 save
pm2 startup
```

### Required .env values on Oracle VM:
```
SUPABASE_URL=https://ftxbphwlqskimdnqcfxh.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<from Supabase dashboard → Project Settings → API>
TRADINGVIEW_WEBHOOK_SECRET=b0509f51c4db9a3b4163e46a591bda2c83c87225a949ee335f767bc3ad852925
TELEGRAM_BOT_TOKEN=<same as Mac Mini .env TELEGRAM_BOT_TOKEN>
TELEGRAM_CHAT_ID=1288928049
PORT=3001
NODE_ENV=production
```

### nginx proxy (if not already configured):
```nginx
server {
    server_name api.goclearonline.cc;
    location / {
        proxy_pass http://localhost:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Certbot SSL (if not already done):
```bash
sudo certbot --nginx -d api.goclearonline.cc
```

---

## TASK 2 — TradingView Webhook

### Set this webhook URL in TradingView alerts:
```
https://api.goclearonline.cc/api/webhooks/tradingview
```

### Webhook secret (include in alert message JSON):
```json
{
  "secret": "b0509f51c4db9a3b4163e46a591bda2c83c87225a949ee335f767bc3ad852925",
  "symbol": "{{ticker}}",
  "side": "{{strategy.order.action}}",
  "price": {{close}},
  "timeframe": "{{interval}}"
}
```

### Verify pipeline (after deploy):
1. Send a test alert from TradingView
2. Check Supabase `tv_raw_alerts` table — should have a new row
3. Check Telegram — should get a signal alert
4. Check `tv_normalized_signals` — should have status=enriched
5. Mac Mini signal-review worker will pick it up and send to OpenClaw

---

## TASK 3 — ClientPortalAssistant (React Portal)

### Location: goclearonline.cc (React + Netlify)

### What it does:
- Answers client questions using research_briefs from Supabase
- Scoped to approved tables only (no raw artifacts, no client PII)
- Reads: research_briefs, grant_opportunities, business_opportunities

### Oracle API endpoint to create:
```
POST /api/portal/query
Body: { "question": "...", "client_id": "..." }
Returns: { "answer": "...", "sources": [...] }
```

### Logic:
1. Search `research_briefs` for relevant content (keyword match or embedding)
2. Pass top 3 briefs + question to OpenClaw via Mac Mini gateway
3. Return plain-language answer
4. Never expose research_artifacts, research_claims, or client account data

### Mac Mini OpenClaw gateway:
```
POST http://100.69.193.49:18789/v1/chat/completions   (Tailscale IP)
Authorization: Bearer <OPENCLAW_AUTH_TOKEN>
```

### React component location:
Add to the portal UI — a chat/FAQ widget that POSTs to `/api/portal/query`

---

## VERIFY CHECKLIST (run after all 3 tasks)

- [ ] `curl https://api.goclearonline.cc/api/health` → `{"status":"healthy"}`
- [ ] TradingView test alert → `tv_raw_alerts` has new row
- [ ] Signal appears in `tv_normalized_signals` with status=enriched
- [ ] Mac Mini picks up signal → Telegram alert fires
- [ ] Portal query returns answer from research_briefs
- [ ] PM2 shows nexus-oracle-api running
- [ ] SSL cert valid (https works without warning)

---

## DAY 2 STATUS FROM MAC MINI

| Component                 | Status     | Notes |
|---------------------------|------------|-------|
| OpsMonitoringWorker       | ✅ Running  | Daily report @ 08:00 via scheduler |
| GrantWorker               | ✅ Running  | Telegram alerts firing |
| OpportunityWorker         | ✅ Running  | Telegram alerts firing |
| CreditWorker              | ✅ Running  | 14 artifacts analyzed |
| CRMCopilotWorker          | ✅ Running  | 3 CRM artifacts |
| ContentWorker             | ✅ Running  | Awaiting source content |
| TradingResearchWorker     | ✅ Running  | Awaiting enriched signals |
| RiskComplianceWorker      | ✅ Running  | Reviewing proposals |
| Trading Engine (DRY_RUN)  | ✅ Active   | Flip to live after 24h clean demo |
| Oracle API                | ⏳ Pending  | Windows task |
| TradingView Webhook       | ⏳ Pending  | Windows task |
| ClientPortalAssistant     | ⏳ Pending  | Windows + Oracle task |

---

## FLIP TRADING ENGINE LIVE (after 24h demo passes)

On Mac Mini, edit trading-engine/nexus_trading_engine.py line 24:
```python
DRY_RUN = False   # was True
```

Then restart:
```bash
launchctl kickstart -k gui/$(id -u)/com.nexus.trading-engine
```

Check Telegram for confirmation message.
