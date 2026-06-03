#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "docs" / "reports" / "audits"

path = sorted(AUDIT_DIR.glob("hermes_layer_test_results_*.json"))[-1]
doc = json.loads(path.read_text(encoding="utf-8"))
required = {
    "message", "handled_by_layer", "intent", "handler", "mode", "output_header",
    "evidence_dump_appeared", "quality_fallback_appeared", "mock_output_appeared",
    "safety_flags", "recommended_fix_if_failed",
}

if "results" not in doc or not isinstance(doc["results"], list) or not doc["results"]:
    print("results missing or empty")
    sys.exit(1)
for idx, item in enumerate(doc["results"]):
    if not required.issubset(item):
        print(f"Layer result {idx} missing keys")
        sys.exit(1)

print("Audit layer results schema OK.")
