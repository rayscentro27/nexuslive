"""
ssl_fix.py — Apply certifi CA bundle to Python's default SSL context.

Import this once at the top of any worker that makes HTTPS calls.
Works on Python 3.14 on macOS where the system CA certs are not trusted.

Usage:
    import lib.ssl_fix  # noqa — applies SSL fix on import

Safe to import multiple times — idempotent.
"""
import ssl as _ssl
import urllib.request as _ureq

try:
    import certifi as _certifi
    _CA = _certifi.where()
except ImportError:
    _CA = None

if _CA:
    # Patch the global default HTTPS handler to use certifi's CA bundle.
    # This affects all subsequent urllib.request.urlopen calls in this process.
    _ctx = _ssl.create_default_context(cafile=_CA)
    _https_handler = _ureq.HTTPSHandler(context=_ctx)
    _opener = _ureq.build_opener(_https_handler)
    _ureq.install_opener(_opener)
