"""
test_revenue_asset_packet_creation.py
Tests: packet is created, saved as markdown/json, latest pointer updated.
"""
import sys, os, json
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


print("=== test_revenue_asset_packet_creation ===\n")

from lib.hermes_revenue_asset_packet import (
    build_revenue_asset_packet, save_revenue_asset_packet,
    load_latest_revenue_asset_packet,
    _PACKET_DIR, _LATEST_FILE, SAFETY_BOUNDARY,
)

# ── build_revenue_asset_packet ────────────────────────────────────────────────
print("-- build_revenue_asset_packet structure --")
packet = build_revenue_asset_packet()
check("packet_id present", bool(packet.get("packet_id")))
check("packet_id starts with pkt_", packet.get("packet_id", "").startswith("pkt_"))
check("created_at present", bool(packet.get("created_at")))
check("goal present", bool(packet.get("goal")))
check("goal mentions 1000/week", "1,000/week" in packet.get("goal", "") or "1000" in packet.get("goal",""))
check("primary_offer present", bool(packet.get("primary_offer")))
check("assets is list", isinstance(packet.get("assets"), list))
check("at least 1 asset", len(packet.get("assets", [])) >= 1)
check("readiness_score 0-100", 0 <= packet.get("readiness_score", -1) <= 100)
check("cta_options present", bool(packet.get("cta_options")))
check("launch_checklist present", bool(packet.get("launch_checklist")))
check("approval_checklist present", bool(packet.get("approval_checklist")))
check("approval_candidates is list", isinstance(packet.get("approval_candidates"), list))
check("safety_boundary present", bool(packet.get("safety_boundary")))
check("safety_boundary mentions publish",
      "publish" in packet.get("safety_boundary", "").lower())
check("next_best_step present", bool(packet.get("next_best_step")))

# ── save_revenue_asset_packet ─────────────────────────────────────────────────
print("\n-- save_revenue_asset_packet --")
saved = save_revenue_asset_packet(packet)
check("saved_json path returned", bool(saved.get("saved_json")))
check("saved_md path returned", bool(saved.get("saved_md")))
check("latest_updated path returned", bool(saved.get("latest_updated")))

json_path = Path(saved["saved_json"])
md_path   = Path(saved["saved_md"])
check("json file exists", json_path.exists())
check("md file exists",   md_path.exists())
check("latest pointer exists", _LATEST_FILE.exists())

# ── saved JSON is valid and has required fields ───────────────────────────────
print("\n-- saved JSON structure --")
saved_data = json.loads(json_path.read_text())
check("packet_id in saved json", "packet_id" in saved_data)
check("assets in saved json", "assets" in saved_data)
check("readiness_score in saved json", "readiness_score" in saved_data)
check("cta_options in saved json", "cta_options" in saved_data)
check("safety_boundary in saved json", "safety_boundary" in saved_data)
check("text_preview NOT in saved assets",
      all("text_preview" not in a for a in saved_data.get("assets", [])))

# ── saved markdown has correct headers ───────────────────────────────────────
print("\n-- saved markdown content --")
md_text = md_path.read_text()
check("md starts with NEXUS REVENUE ASSET PACKET", md_text.startswith("NEXUS REVENUE ASSET PACKET"))
check("md contains Goal section", "Goal:" in md_text)
check("md contains Approval boundary", "Approval boundary" in md_text or "approval boundary" in md_text.lower())
check("md does not contain secrets", not any(
    s in md_text for s in ["sk-", "eyJ", "TELEGRAM_BOT_TOKEN", "supabase_key"]
))

# ── latest pointer ────────────────────────────────────────────────────────────
print("\n-- latest pointer --")
ptr = json.loads(_LATEST_FILE.read_text())
check("latest pointer has packet_id", bool(ptr.get("packet_id")))
check("latest pointer has json_path",  bool(ptr.get("json_path")))
check("latest pointer has md_path",    bool(ptr.get("md_path")))
check("latest pointer has readiness_score", "readiness_score" in ptr)

# ── load_latest_revenue_asset_packet ─────────────────────────────────────────
print("\n-- load_latest_revenue_asset_packet --")
loaded = load_latest_revenue_asset_packet()
check("loaded is not None", loaded is not None)
if loaded:
    check("loaded has packet_id", bool(loaded.get("packet_id")))
    check("loaded packet_id matches saved", loaded.get("packet_id") == packet["packet_id"])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
