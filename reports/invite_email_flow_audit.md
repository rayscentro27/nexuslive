# Invite Email Flow Audit

Date: 2026-05-10

## Located Components
- Invite endpoint: `POST /api/admin/users/<user_id>/send-tester-email` in `control_center/control_center_server.py`.
- Template builder: `build_tester_email(...)` in `scripts/prelaunch_utils.py`.
- Waived access path:
  - `/api/admin/users/<user_id>/waive-payment`
  - `/api/admin/users/<user_id>/revoke-waiver`

## Token / Link Generation
- Endpoint currently accepts a provided login link and falls back to configured login URL.
- Signup token generation source is outside this specific helper; invite email includes supplied link as-is.

## Billing / Waiver Safety
- Waiver endpoint updates override rows and profile subscription level.
- No changes in this pass to billing trigger/execution behavior.

## Security / Secrets
- No secrets are embedded in email template output.
- Sender auth still uses existing environment-based SMTP path.
