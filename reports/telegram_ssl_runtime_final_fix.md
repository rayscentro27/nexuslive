# Telegram SSL Runtime Final Fix

Date: 2026-05-11
Scope: persist SSL cert environment across shell/launchctl/runtime contexts without disabling SSL verification.

## Root Cause Pattern
- Intermittent Telegram notification failures with `CERTIFICATE_VERIFY_FAILED` were caused by runtime-context differences in CA bundle availability.
- Launchctl service contexts had CA env configured, while ad-hoc shell execution paths did not consistently inherit the same SSL env.

## Audit Results
### Current shell
- `SSL_CERT_FILE`: unset (before fix process)
- `REQUESTS_CA_BUNDLE`: unset (before fix process)

### launchctl
- `SSL_CERT_FILE`: set
- `REQUESTS_CA_BUNDLE`: set
- Value for both: certifi bundle path

### Service runtime env presence
- Telegram service: both vars set
- Scheduler service: both vars set
- Control-center service: both vars set

## Cert Bundle Target
- Detected via `certifi.where()`:
- `/usr/local/lib/python3.14/site-packages/certifi/cacert.pem`

## Changes Applied
1. Added helper script:
- `scripts/ensure_launchctl_ssl_env.py`

2. Script behavior:
- Resolves certifi bundle dynamically.
- Ensures launchctl `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` are set to that path.
- Verifies post-set values.

3. Restarted required services only:
- `com.raymonddavis.nexus.telegram`
- `ai.nexus.control-center`
- `com.raymonddavis.nexus.scheduler`

## Runtime Verification
- Test Telegram send: `✅ Nexus Telegram SSL runtime verification successful.`
- Result: `TELEGRAM_SENT=true`

- Test email summary send:
- Result: `EMAIL_SENT=true`

## Regression Validation
- `scripts/test_telegram_policy.py` -> PASS (20/20)
- `scripts/test_hermes_telegram_pipeline.py` -> PASS (71/71)
- `scripts/test_email_reports.py` -> PASS

## Safety Confirmation
- No SSL bypass used (`verify=False` not used).
- No token/chat-id/env secret output.
- No unsafe automation flags changed.
