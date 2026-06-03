"""
test_custom_gpt_trainer_package.py
Phase 7B: Custom GPT Trainer Package.
Verifies that all trainer docs exist and contain required sections.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pathlib import Path

passes = 0
failures = 0

def check(label, cond):
    global passes, failures
    status = "PASS" if cond else "FAIL"
    if not cond:
        failures += 1
    else:
        passes += 1
    print(f"  [{status}] {label}")
    return cond


ROOT = Path(__file__).resolve().parent.parent
TRAINER_DIR = ROOT / "docs" / "hermes" / "custom_gpt_trainer"

print("\nCustom GPT Trainer Package Tests")
print("=" * 50)

print("\n-- Required files exist --")
_REQUIRED_FILES = [
    "NEXUS_CFO_TRAINER_GPT_INSTRUCTIONS.md",
    "NEXUS_CFO_TRAINER_KNOWLEDGE_MANIFEST.md",
    "HERMES_FAILURE_REVIEW_PROMPT.md",
    "HERMES_RESPONSE_REWRITE_RUBRIC.md",
    "HERMES_TEST_GENERATION_RUBRIC.md",
    "HERMES_ACTIONS_API_PLAN.md",
]
for fname in _REQUIRED_FILES:
    path = TRAINER_DIR / fname
    check(f"exists: {fname}", path.exists())

print("\n-- Doctrine files exist --")
DOCTRINE_DIR = ROOT / "docs" / "hermes"
_DOCTRINE_FILES = [
    "HERMES_CFO_CONVERSATION_CONTRACT.md",
    "HERMES_PLAIN_LANGUAGE_STYLE_GUIDE.md",
    "HERMES_UNKNOWN_ANSWER_PROTOCOL.md",
    "HERMES_SCOUT_DISPATCH_CONTRACT.md",
    "HERMES_PROMPT_GENERATION_CONTRACT.md",
    "HERMES_FAILURE_LEARNING_PROTOCOL.md",
]
for fname in _DOCTRINE_FILES:
    path = DOCTRINE_DIR / fname
    check(f"exists: {fname}", path.exists())

print("\n-- GPT instructions has required sections --")
instructions = (TRAINER_DIR / "NEXUS_CFO_TRAINER_GPT_INSTRUCTIONS.md").read_text()
check("has Role section", "## Role" in instructions)
check("has Three Modes section", "Three Modes" in instructions)
check("has safety rules section", "Safety" in instructions)
check("has failure types table", "evidence_dump" in instructions)
check("mentions approval boundary", "approval" in instructions.lower())

print("\n-- Rewrite rubric has required criteria --")
rubric = (TRAINER_DIR / "HERMES_RESPONSE_REWRITE_RUBRIC.md").read_text()
check("has Header criterion", "Header" in rubric)
check("has Answer First criterion", "Answer First" in rubric)
check("has jargon list", "artifact_inventory" in rubric)
check("has rewrite template", "PLAIN ANSWER" in rubric)

print("\n-- Test generation rubric has check() pattern --")
test_rubric = (TRAINER_DIR / "HERMES_TEST_GENERATION_RUBRIC.md").read_text()
check("has check() function", "def check(" in test_rubric)
check("has PASS/FAIL pattern", "PASS" in test_rubric and "FAIL" in test_rubric)
check("has evidence dump markers list", "EVIDENCE_DUMP_MARKERS" in test_rubric)

print("\n-- Actions API plan has safety note --")
api_plan = (TRAINER_DIR / "HERMES_ACTIONS_API_PLAN.md").read_text()
check("has safety section", "Safety" in api_plan)
check("has Ray approval requirement", "Ray approval" in api_plan or "ray approval" in api_plan.lower())
check("NOT YET LIVE note present", "NOT YET LIVE" in api_plan or "not yet live" in api_plan.lower())

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
