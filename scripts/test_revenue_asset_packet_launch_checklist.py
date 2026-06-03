"""
test_revenue_asset_packet_launch_checklist.py
Tests: launch checklist and approval checklist generation and content.
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


print("=== test_revenue_asset_packet_launch_checklist ===\n")

from lib.hermes_revenue_asset_packet import build_launch_checklist, build_approval_checklist
from hermes_command_router.router import run_command

# ── build_launch_checklist structure ─────────────────────────────────────────
print("-- build_launch_checklist --")
lc = build_launch_checklist()
check("returns dict", isinstance(lc, dict))
check("has ray_approval_required", bool(lc.get("ray_approval_required")))
check("has safe_internal_work", bool(lc.get("safe_internal_work")))
check("has blocked_until_ray_approves", bool(lc.get("blocked_until_ray_approves")))

# Verify key approval-gated items
approval_steps = lc.get("ray_approval_required") or []
approval_text = " ".join(approval_steps).lower()
check("approval_required includes lead magnet", "lead magnet" in approval_text)
check("approval_required includes newsletter", "newsletter" in approval_text)
check("approval_required includes video script", "video" in approval_text or "script" in approval_text)

# Verify blocked items
blocked = lc.get("blocked_until_ray_approves") or []
blocked_text = " ".join(blocked).lower()
check("publish in blocked list", "publish" in blocked_text)
check("email subscribers in blocked list", "email" in blocked_text or "subscriber" in blocked_text)
check("stripe/payment in blocked list", "stripe" in blocked_text or "payment" in blocked_text)
check("social media in blocked list", "social" in blocked_text or "post" in blocked_text)

# Verify safe internal work
safe_work = lc.get("safe_internal_work") or []
check("safe_internal_work not empty", len(safe_work) >= 3)

# ── show launch checklist command ─────────────────────────────────────────────
print("\n-- show launch checklist command --")
resp = run_command("show launch checklist", source="cli")
check("starts with LAUNCH CHECKLIST", resp.startswith("LAUNCH CHECKLIST"))
check("shows Before publishing section", "Before publishing" in resp)
check("shows Safe internal work section", "Safe internal work" in resp)
check("shows Requires Ray approval section", "Requires Ray" in resp or "approval" in resp.lower())
check("no ═══", "═══" not in resp)
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))

# ── build_approval_checklist structure ────────────────────────────────────────
print("\n-- build_approval_checklist --")
ac = build_approval_checklist()
check("returns dict", isinstance(ac, dict))
check("has checklist key", bool(ac.get("checklist")))
check("has approval_boundary", bool(ac.get("approval_boundary")))
check("approval_boundary mentions publish",
      "publish" in ac.get("approval_boundary", "").lower())

checklist_items = ac.get("checklist") or []
checklist_text  = " ".join(checklist_items).lower()
check("checklist includes lead magnet review", "lead magnet" in checklist_text)
check("checklist includes compliance check", "complian" in checklist_text or "unsafe" in checklist_text)
check("checklist mentions memory v2", "memory v2" in checklist_text)

# ── show approval checklist command ──────────────────────────────────────────
print("\n-- show approval checklist command --")
resp2 = run_command("show approval checklist", source="cli")
check("starts with APPROVAL CHECKLIST", resp2.startswith("APPROVAL CHECKLIST"))
check("shows checklist items", "lead magnet" in resp2.lower() or "review" in resp2.lower())
check("shows approval boundary", "approval boundary" in resp2.lower() or "boundary" in resp2.lower())
check("no ═══", "═══" not in resp2)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
