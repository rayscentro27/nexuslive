"""
test_hermes_tool_scout_registry.py
Verifies tool/scout registry loads and all scouts have required fields.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_hermes_tool_scout_registry ===")

from lib.hermes_tool_scout_registry import (
    _build_default_registry, get_scouts, route_to_scout,
    registry_summary_plain_english, ToolOrScout
)

# 1. Registry builds
items = _build_default_registry()
check("registry returns list", isinstance(items, list))
check("at least 10 tools/scouts", len(items) >= 10)

# 2. All required fields on every item
for item in items:
    check(f"'{item.id}' has name", bool(item.name))
    check(f"'{item.id}' has type", item.type in ("core_memory", "agent", "scout", "system"))
    check(f"'{item.id}' has purpose", bool(item.purpose))

# 3. Specific scouts exist
scout_ids = [s.id for s in items if s.type == "scout"]
REQUIRED_SCOUTS = [
    "youtube_research_scout", "content_intelligence_scout", "monetization_scout",
    "vibe_trading_backtest", "oanda_demo_adapter", "trading_research_scout",
]
for sid in REQUIRED_SCOUTS:
    check(f"scout '{sid}' in registry", sid in scout_ids)

# 4. OANDA demo requires approval for live trading
oanda = next((s for s in items if s.id == "oanda_demo_adapter"), None)
check("oanda_demo_adapter exists", oanda is not None)
if oanda:
    check("oanda requires approval for live trading",
          any("live" in r.lower() for r in oanda.requires_ray_approval))

# 5. Evidence_only mode never fails
evidence_only = next((s for s in items if s.id == "evidence_only_mode"), None)
check("evidence_only_mode exists", evidence_only is not None)
if evidence_only:
    check("evidence_only never fails", "never" in evidence_only.failure_mode.lower())

# 6. Scout routing
yt_scout = route_to_scout("youtube_url")
check("youtube_url routes to a scout", yt_scout is not None)
if yt_scout:
    check("youtube_url routes to youtube_research_scout",
          "youtube" in yt_scout.id.lower())

# 7. Plain English summary
summary = registry_summary_plain_english()
check("summary non-empty", len(summary) > 30)
check("summary mentions scouts", "scout" in summary.lower())
check("summary mentions agents", "agent" in summary.lower())

# 8. Compliance guard requires approval
compliance = next((s for s in items if s.id == "compliance_guard"), None)
check("compliance_guard exists", compliance is not None)
if compliance:
    check("compliance guard not autonomous", compliance.autonomous_allowed is False)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
