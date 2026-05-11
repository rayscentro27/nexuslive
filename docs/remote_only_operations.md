# Remote-Only Operations Plan

## Scenario
Mac mini is unattended; operations run remotely from iPhone/Surface.

## Remote Access Paths
Primary:
- SSH (`*:22`) over trusted network path

Secondary:
- Tailscale and/or cloudflared path for fallback access

## Remote Restart Procedure (Service-Level)
1. Verify remote shell access
2. Check service status (`launchctl list | rg nexus`)
3. Restart only the impacted service label
4. Re-run service health validation checklist

## Dashboard Recovery Sequence
1. Validate control center service (`control_center_server.py`)
2. Validate admin auth behavior
3. Validate workforce endpoint response shape
4. Validate operator dashboard access path

## Telegram Recovery Sequence
1. Confirm bot process exists
2. Confirm outbound connectivity
3. Send one known safe operator query
4. Confirm response and report delivery behavior

## Emergency Rollback
If remote degradation appears after optional optimization:
1. Re-enable last paused optional service
2. Re-enable previous known-good service set
3. Validate Telegram/admin/workforce/email path
4. Pause further optimization until root cause is identified

## Service Validation Order (after any change)
1. Remote access stability
2. Telegram response
3. Admin auth + workforce
4. Email/report path
5. Invite/onboarding checks
