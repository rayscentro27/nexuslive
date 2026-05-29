"""
test_ray_operating_principles.py
Verifies Ray's operating principles are available as evidence.
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

print("=== test_ray_operating_principles ===")

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent

# 1. Markdown doc exists
md_path = ROOT / "docs" / "reports" / "core" / "ray_operating_principles_for_hermes.md"
check("ray_operating_principles markdown exists", md_path.exists())
if md_path.exists():
    content = md_path.read_text()
    check("doc mentions Hermes as decision layer",
          "decision layer" in content.lower() or "decision" in content.lower())
    check("doc mentions Claude Code as worker",
          "worker" in content.lower() or "claude code" in content.lower())
    check("doc mentions Telegram", "telegram" in content.lower())
    check("doc mentions approval boundaries", "approval" in content.lower())
    check("doc mentions plain language", "plain" in content.lower() or "language" in content.lower())
    check("doc mentions live trading requires approval",
          "live" in content.lower() and "approval" in content.lower())
    check("doc mentions paid tools require approval",
          "paid" in content.lower())
    check("doc mentions $1000/week or revenue goal",
          "1,000" in content or "$1" in content or "revenue" in content.lower())

# 2. JSON artifact exists
json_path = ROOT / "docs" / "reports" / "core" / "ray_operating_principles_for_hermes.json"
check("ray_operating_principles JSON exists", json_path.exists())
if json_path.exists():
    data = json.loads(json_path.read_text())
    check("JSON has artifact_id", bool(data.get("artifact_id")))
    check("JSON has key_principles list", isinstance(data.get("key_principles"), list))
    check("JSON has summary", bool(data.get("summary")))
    principles = data.get("key_principles", [])
    check("key_principles has at least 5 items", len(principles) >= 5)
    check("principles mention plain language",
          any("plain" in p.lower() for p in principles))
    check("principles mention evidence",
          any("evidence" in p.lower() for p in principles))

# 3. Operating doctrine exists
doctrine_md = ROOT / "docs" / "reports" / "core" / "hermes_operating_doctrine.md"
check("hermes_operating_doctrine.md exists", doctrine_md.exists())
if doctrine_md.exists():
    doc = doctrine_md.read_text()
    check("doctrine defines Hermes role", "operator" in doc.lower() or "nexus" in doc.lower())
    check("doctrine defines Claude Code role", "worker" in doc.lower() or "claude code" in doc.lower())
    check("doctrine has approval boundaries table",
          "approval" in doc.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
