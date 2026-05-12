# Telegram SSL Diagnostics

Date: 2026-05-10

## Scope
- Diagnose Telegram HTTPS failure in Mac mini service environment.
- Keep SSL verification enabled.
- Avoid changes outside certificate trust repair.

## Baseline Symptoms
- Telegram sends failed with:
  - `CERTIFICATE_VERIFY_FAILED: self-signed certificate in certificate chain`
- Email notifications were already working.

## Environment Diagnostics

### Python / SSL Runtime
- Python version: `3.14.4`
- Python executable: `/usr/local/opt/python@3.14/bin/python3.14`
- OpenSSL: `OpenSSL 3.6.1 27 Jan 2026`
- `ssl.get_default_verify_paths()`:
  - cafile: `None`
  - capath: `/usr/local/etc/openssl@3/certs`
  - openssl default cafile: `/usr/local/etc/openssl@3/cert.pem`

### certifi
- Installed: yes
- Version: `2026.02.25`
- Bundle path: `/usr/local/lib/python3.14/site-packages/certifi/cacert.pem`

### Shell Environment (before repair)
- `REQUESTS_CA_BUNDLE`: unset
- `SSL_CERT_FILE`: unset
- `SSL_CERT_DIR`: unset
- `HTTPS_PROXY`: unset
- `HTTP_PROXY`: unset
- `NO_PROXY`: unset

### launchctl Environment (before repair)
- `REQUESTS_CA_BUNDLE`: unset
- `SSL_CERT_FILE`: unset
- `SSL_CERT_DIR`: unset
- `HTTPS_PROXY`: unset
- `HTTP_PROXY`: unset
- `NO_PROXY`: unset

## Shell vs Service Comparison
- Telegram service runs with `/usr/local/bin/python3` (`com.raymonddavis.nexus.telegram`).
- Both shell and launchctl lacked explicit CA bundle overrides before repair.
- Python default TLS verification failed for `https://api.telegram.org` with self-signed chain error.
- `curl` to `https://api.telegram.org` succeeded, indicating network reachability and a trust-path issue specific to Python/OpenSSL defaults.

## HTTPS Tests

### Before Repair
- `python urllib` default context to `https://api.telegram.org`: failed (`CERTIFICATE_VERIFY_FAILED`).
- `python urllib` with `certifi.where()` as cafile: succeeded.

### After Repair
- `python urllib` with environment CA override: succeeded (`200`).
- Telegram `sendMessage`: succeeded.

## Root Cause
- Python/OpenSSL default certificate chain resolution in this runtime did not trust the presented chain for Telegram endpoint.
- Using certifi CA bundle resolved trust verification without disabling SSL checks.

## Safety Notes
- No SSL verification bypass used.
- No `verify=False` usage.
- No automation policy flags were relaxed.
