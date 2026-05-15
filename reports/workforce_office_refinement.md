# Workforce Office Refinement — Road Trip Pass
Date: 2026-05-15

## Status: IMPROVED ✅

## Changes Made (WorkforceOffice.tsx)

### Summary Bar Improvement

Replaced "Attention" stat with "Overdue":
- **Attention** (before): counted workers in warning/offline state (duplicate of warnWorkers)
- **Overdue** (after): counts research tickets open >24h still in submitted/queued/researching state
- Shows queue pressure to operator — overdue tickets glow red when count > 0

```typescript
const overdueCount = tickets.filter(t => {
  const age = (Date.now() - new Date(t.created_at).getTime()) / 3600000;
  return age > 24 && ['submitted', 'queued', 'researching'].includes(t.status);
}).length;
```

### Safety Footer Enhancement

Added "DEMO trading only" to the footer text:
- Before: `DRY_RUN=true · LIVE_TRADING=false · No broker execution · No auto social`
- After: `DRY_RUN=true · LIVE_TRADING=false · DEMO trading only · No broker execution · No auto social`

## Existing Features Confirmed Intact

| Feature | Status |
|---------|--------|
| 4-panel tabs (Workforce, Research, Ingestion, Live Ops) | ✅ Unchanged |
| Animated pulse rings on active research | ✅ Unchanged |
| 90s auto-refresh with timestamp | ✅ Unchanged |
| Department zones with workers | ✅ Unchanged |
| Ingestion grouped by status | ✅ Unchanged |
| Live ops event stream | ✅ Unchanged |
| Knowledge events in ops feed | ✅ Unchanged |
