"""
test_revenue_packet_improved_artifacts.py
Tests: save_improved_revenue_packet writes JSON and MD files;
       filenames contain 'improved'; latest pointer updated;
       no secrets in saved files.
"""
import sys, os, json, tempfile
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


print("=== test_revenue_packet_improved_artifacts ===\n")

from lib.hermes_revenue_asset_packet import (
    save_improved_revenue_packet, build_revenue_asset_packet,
)

# ── Save improved packet ───────────────────────────────────────────────────────
print("-- save improved packet --")
packet = build_revenue_asset_packet()
improvements = ["Add internal marker to all files", "Add CTA to checklist"]
result = save_improved_revenue_packet(packet, improvements)

check("save_improved_revenue_packet returns dict", isinstance(result, dict))
check("result has saved_json", "saved_json" in result)
check("result has saved_md", "saved_md" in result)
check("result has latest_updated", "latest_updated" in result)

json_path = Path(result["saved_json"])
md_path   = Path(result["saved_md"])
latest    = Path(result["latest_updated"])

check("json file exists", json_path.exists())
check("md file exists", md_path.exists())
check("latest pointer exists", latest.exists())

# ── Filenames contain 'improved' ──────────────────────────────────────────────
print("\n-- filenames contain 'improved' --")
check("json filename contains 'improved'", "improved" in json_path.name)
check("md filename contains 'improved'", "improved" in md_path.name)

# ── JSON is valid and has required fields ──────────────────────────────────────
print("\n-- saved JSON is valid --")
try:
    saved_json = json.loads(json_path.read_text())
    check("JSON parses OK", True)
    check("saved JSON has packet_id", "packet_id" in saved_json)
    check("saved JSON has readiness_score", "readiness_score" in saved_json)
    check("saved JSON has improvements_applied", "improvements_applied" in saved_json)
    check("improvements_applied in JSON", saved_json.get("improvements_applied") == improvements)
except Exception as exc:
    check(f"JSON parses OK (ERROR: {exc!s:.80})", False)
    check("saved JSON has packet_id", False)
    check("saved JSON has readiness_score", False)
    check("saved JSON has improvements_applied", False)
    check("improvements_applied in JSON", False)

# ── MD file has REVENUE PACKET IMPROVED header ────────────────────────────────
print("\n-- saved MD has correct header --")
md_content = md_path.read_text()
check("MD has REVENUE PACKET IMPROVED header", "REVENUE PACKET IMPROVED" in md_content)
check("MD mentions safety boundary", "safety" in md_content.lower() or "no content published" in md_content.lower())

# ── Latest pointer is valid JSON with phase 6E info ──────────────────────────
print("\n-- latest pointer updated for Phase 6E --")
try:
    ptr = json.loads(latest.read_text())
    check("latest pointer parses OK", True)
    check("latest pointer has json_path", "json_path" in ptr)
    check("latest pointer has readiness_score", "readiness_score" in ptr)
    check("latest pointer has phase '6E'", ptr.get("phase") == "6E")
except Exception as exc:
    check(f"latest pointer parses OK (ERROR: {exc!s:.80})", False)
    check("latest pointer has json_path", False)
    check("latest pointer has readiness_score", False)
    check("latest pointer has phase '6E'", False)

# ── No secrets in saved files ────────────────────────────────────────────────
print("\n-- no secrets in saved files --")
SECRET_PATTERNS = [
    "sk-", "xoxb-", "TELEGRAM_BOT_TOKEN", "SUPABASE_KEY",
    "service_role", "postgres://", "password=",
]
for path_obj, label in [(json_path, "json"), (md_path, "md")]:
    content = path_obj.read_text()
    for pattern in SECRET_PATTERNS:
        check(f"no '{pattern}' in {label}", pattern not in content)

# Cleanup
for p in [json_path, md_path]:
    try:
        p.unlink(missing_ok=True)
    except Exception:
        pass

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
