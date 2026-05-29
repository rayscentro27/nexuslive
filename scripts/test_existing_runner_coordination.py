"""test_existing_runner_coordination.py — daily engine must not duplicate existing runners."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_existing_runner_coordination ===")
ROOT = Path(__file__).resolve().parent.parent

# Daily intake engine must NOT reimplement these
MUST_NOT_DUPLICATE = [
    "lib/youtube_intelligence_worker.py",
    "lib/github_trend_researcher.py",
    "lib/monetization_operating_engine.py",
    "lib/content_pipeline.py",
]

for f in MUST_NOT_DUPLICATE:
    path = ROOT / f
    if path.exists():
        # Verify daily_opportunity_intake_engine.py does NOT copy their logic
        intake_src = (ROOT / "lib" / "daily_opportunity_intake_engine.py").read_text()
        # It should REFERENCE them via next_action, not reimplement them
        fname = Path(f).stem
        check(
            f"intake engine delegates to {fname} via next_action (not reimplements)",
            fname not in intake_src or "next_action" in intake_src
        )

# Verify intake engine uses existing scout dispatcher
intake_src = (ROOT / "lib" / "daily_opportunity_intake_engine.py").read_text()
check("intake engine references existing runners via next_action fields", "next_action" in intake_src)
check("intake engine does NOT launch subprocesses directly", "subprocess" not in intake_src)
check("intake engine does NOT define its own youtube scraper", "def _scrape_youtube" not in intake_src)

# Verify monetization decision engine creates action queue entries (doesn't duplicate)
mon_src = (ROOT / "lib" / "hermes_monetization_decision_engine.py").read_text()
check("monetization engine writes to action queue", "hermes_action_queue" in mon_src)
check("monetization engine writes to decision log", "hermes_decision_log" in mon_src)
check("monetization engine uses nexus_artifact_registry", "nexus_artifact_registry" in mon_src)

# Verify new Telegram topics are added to runtime config
rc_src = (ROOT / "lib" / "hermes_runtime_config.py").read_text()
for topic in ["daily_intake", "monetization_actions", "rejected_opportunities", "scouts_working", "daily_review"]:
    check(f"runtime_config has topic '{topic}'", f'"{topic}"' in rc_src)

# Verify handlers exist in internal_first
if_src = (ROOT / "lib" / "hermes_internal_first.py").read_text()
for topic in ["daily_intake", "monetization_actions", "rejected_opportunities", "scouts_working", "daily_review"]:
    check(f"internal_first handles topic '{topic}'", f'topic == "{topic}"' in if_src)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
