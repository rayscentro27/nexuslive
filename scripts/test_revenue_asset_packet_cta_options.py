"""
test_revenue_asset_packet_cta_options.py
Tests: CTA options are generated with correct keys and copy.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_revenue_asset_packet_cta_options ===\n")

from lib.hermes_revenue_asset_packet import build_cta_options, CTA_OPTIONS
from hermes_command_router.router import run_command

# ── CTA_OPTIONS constant ──────────────────────────────────────────────────────
print("-- CTA_OPTIONS constant --")
required_keys = {"short", "newsletter", "video", "landing_page", "soft", "direct"}
for key in required_keys:
    check(f"'{key}' key in CTA_OPTIONS", key in CTA_OPTIONS)
    check(f"CTA_OPTIONS['{key}'] is non-empty string", bool(CTA_OPTIONS.get(key)))

# ── build_cta_options ─────────────────────────────────────────────────────────
print("\n-- build_cta_options --")
opts = build_cta_options()
check("returns dict", isinstance(opts, dict))
check("has 6+ options", len(opts) >= 6)
for key in required_keys:
    check(f"'{key}' in returned opts", key in opts)

# ── CTA copy safety (no unsafe promises) ─────────────────────────────────────
print("\n-- CTA copy has no unsafe promises --")
unsafe_terms = ["guaranteed", "guarantee", "100% success", "risk-free guarantee"]
all_cta_text = " ".join(str(v) for v in opts.values()).lower()
for term in unsafe_terms:
    check(f"CTA does not contain '{term}'", term not in all_cta_text)

# ── show cta options command ──────────────────────────────────────────────────
print("\n-- show cta options command --")
resp = run_command("show cta options", source="cli")
check("starts with CTA OPTIONS", resp.startswith("CTA OPTIONS"))
check("shows short CTA label", "short" in resp.lower())
check("shows direct CTA label", "direct" in resp.lower())
check("shows newsletter label", "newsletter" in resp.lower())
check("mentions not published", "not published" in resp.lower() or "internal" in resp.lower())
check("no ═══", "═══" not in resp)
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))

# ── CTA options in packet ─────────────────────────────────────────────────────
print("\n-- CTA options in built packet --")
from lib.hermes_revenue_asset_packet import build_revenue_asset_packet
packet = build_revenue_asset_packet()
check("packet has cta_options", bool(packet.get("cta_options")))
for key in required_keys:
    check(f"packet cta_options has '{key}'", key in (packet.get("cta_options") or {}))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
