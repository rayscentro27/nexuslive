# Test User Invite System Audit v2

Date: 2026-05-10

## Existing Capabilities Found
- Admin user listing endpoint: `/api/admin/users`.
- Payment waiver endpoint: `/api/admin/users/<user_id>/waive-payment`.
- Waiver revoke endpoint: `/api/admin/users/<user_id>/revoke-waiver`.
- Tester tagging endpoint: `/api/admin/users/<user_id>/tester`.
- Tester email endpoint: `/api/admin/users/<user_id>/send-tester-email` with preview/live mode.
- Onboarding completion endpoint exists in funding path.

## Verified in Code (This Pass)
- Waived membership path updates `user_profiles.subscription_plan`.
- Tester metadata table path expected (`prelaunch_testers`) with assigned_by/notes.
- Email send supports safe preview mode via prelaunch utilities.

## Gaps / Follow-ups
- Explicit fields `is_beta_user`, `pilot_group`, `invited_by_admin`, `onboarding_completed` not uniformly visible across all paths.
- End-to-end live invite acceptance requires real user/session testing in target environment.

## Risk
- Medium operational risk if table migrations differ across environments.
- Recommend path-by-path smoke in staging with one disposable tester account.
