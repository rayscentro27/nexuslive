# Current Agenda
_Last updated: 2026-04-10_

## Today

1. **Finish the signal review pipeline**
   - Confirm `signal_review/` components are wired end-to-end
   - Poll new signals from Supabase
   - Review each signal against the 18 stored strategies
   - Run risk checks before approval
   - Send approved/rejected decisions to Telegram

2. **Verify the operating path**
   - Signal enters `tv_normalized_signals`
   - Reviewer returns approve / reject / hold with confidence
   - Risk gate applies daily loss / max positions / R:R rules
   - Signal status is written back to Supabase
   - Telegram alert is sent with reasoning or rejection reason

3. **Close any missing implementation gaps**
   - Check whether the poller, reviewer, risk gate, and startup script are actually complete
   - If partially implemented, finish missing glue code before starting new features

## Next

1. **Research auto-scheduling**
   - Run the research pipeline automatically every 12 hours
   - Load new strategies into the signal reviewer without manual steps

2. **Control Center signal feed**
   - Show approved/rejected signals in the Control Center UI
   - Include confidence and AI reasoning
   - Add a simple confidence trend view

## Later

1. **Daily Risk Office reports**
   - 9am Telegram summary
   - 4pm Telegram summary
   - Include reviewed count, approved/rejected split, exposure, and top strategy matches

2. **Workspace cleanup / grounding**
   - Finish bootstrap basics (`IDENTITY.md`, `USER.md`)
   - Start actual memory files (`memory/YYYY-MM-DD.md`, `MEMORY.md`) so current decisions persist

## Notes

- Windows / Oracle VM remains the home for nginx, PM2, Certbot, webhook config, and `nexus-oracle-api`
- Mac Mini remains the local AI reasoning / review / alerting side
