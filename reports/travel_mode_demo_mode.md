# Travel Mode Demo Mode

## Status
- Phase G partially implemented in UI surfaces.

## Completed
- Workforce Office now shows explicit `Demo / Simulated` label when `VITE_NEXUS_DEMO_MODE` is enabled.
- Trading Intelligence worker status line reflects simulated mode.

## Safety
- Live trading remains disabled by enforced flags.
- Demo mode does not bypass Telegram policy.

## Remaining
- Full synthetic flow injection (simulated opportunities/grants/tickets) is not expanded in this pass.
