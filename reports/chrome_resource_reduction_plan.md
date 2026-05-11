# Chrome Resource Reduction Plan

Date: 2026-05-11

## Why This Matters
Audit shows Chrome renderer/session footprint is a primary memory pressure source on 8 GB hardware.

## Immediate Actions
1. Cap active tabs during operations windows (target <= 8 active tabs)
2. Close stale dashboards duplicated across tabs/windows
3. Pin only essential tabs: admin, workforce, one docs tab
4. Disable or remove high-memory extensions not used for Nexus ops

## AI Tab Isolation Strategy
- Use separate Chrome profile for AI/research-heavy browsing
- Keep ops profile minimal (admin/workforce/remote docs only)
- Restart AI profile between long sessions to release renderer buildup

## Browser Profile Strategy
- Profile A: Nexus Ops (strictly operational)
- Profile B: Research/AI experiments (high churn)
- Profile C: Personal/general browsing (kept off Mac mini during travel mode)

## Memory-Saving Operational Practices
- Restart Chrome at least once daily during unattended periods
- Avoid multiple live dashboards with auto-refresh in parallel
- Prefer one canonical admin tab and one workforce tab
- Use Safari or lightweight browser for static documentation reading

## Expected Savings
- Conservative: 1.0-1.5 GB RAM
- Typical: 1.5-3.0+ GB RAM
- Secondary benefit: reduced swap churn and lower risk of degraded responsiveness
