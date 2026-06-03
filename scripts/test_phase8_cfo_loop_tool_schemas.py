"""test_phase8_cfo_loop_tool_schemas.py — Tool schemas exist and are well-formed."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASS = 0
FAIL = 0

def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")

from pathlib import Path

SCHEMA_JSON = Path(__file__).parent.parent / "docs" / "reports" / "strategy" / "phase8_hermes_tool_schemas.json"
SCHEMA_MD = Path(__file__).parent.parent / "docs" / "reports" / "strategy" / "phase8_hermes_tool_schemas.md"

# ── Files exist ───────────────────────────────────────────────────────────────
check("tool schemas JSON exists", SCHEMA_JSON.exists())
check("tool schemas MD exists", SCHEMA_MD.exists())

# ── JSON is valid ─────────────────────────────────────────────────────────────
schemas = None
try:
    schemas = json.loads(SCHEMA_JSON.read_text())
    check("tool schemas JSON is valid JSON", True)
except Exception as e:
    check("tool schemas JSON is valid JSON", False)

if schemas:
    tools = schemas.get("tools", [])
    tool_names = [t["name"] for t in tools]

    # ── Required tools present ────────────────────────────────────────────────
    required_tools = [
        "compare_drafts", "show_approval_queue", "bulk_approval_safety_check",
        "show_scout_status", "create_scout_assignment", "create_implementation_prompt",
        "show_revenue_plan", "select_option", "explain_recommendation",
        "simplify_last_response", "show_tool_status", "create_research_assignment",
    ]
    for tool_name in required_tools:
        check(f"tool schema exists: {tool_name}", tool_name in tool_names)

    # ── Each tool has required fields ─────────────────────────────────────────
    for tool in tools:
        name = tool.get("name", "unknown")
        check(f"{name}: has description", bool(tool.get("description")))
        check(f"{name}: has parameters", "parameters" in tool)
        check(f"{name}: has safety_notes", bool(tool.get("safety_notes")))
        check(f"{name}: has example_call", "example_call" in tool)
        check(f"{name}: has example_response", "example_response" in tool)

    # ── Safety notes mention safety constraints ───────────────────────────────
    dangerous_tools = ["bulk_approval_safety_check", "create_implementation_prompt"]
    for dt in dangerous_tools:
        tool = next((t for t in tools if t["name"] == dt), None)
        if tool:
            notes = (tool.get("safety_notes") or "").lower()
            check(f"{dt}: safety notes are substantive", len(notes) > 20)

# ── Prototype AVAILABLE_TOOLS list matches schemas ────────────────────────────
from prototypes.hermes_agentic_cfo_loop import AVAILABLE_TOOLS
prototype_tools = {t["name"] for t in AVAILABLE_TOOLS}
if schemas:
    schema_tool_names = set(tool_names)
    # All schema tools should be in prototype (or subset)
    for name in required_tools:
        check(f"prototype has tool: {name}", name in prototype_tools)

print(f"\nPhase 8 tool schemas: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
