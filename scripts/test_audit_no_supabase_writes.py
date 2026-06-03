#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "docs" / "reports" / "audits"

json_files = [
    sorted(AUDIT_DIR.glob("hermes_system_layer_audit_*.json"))[-1],
    sorted(AUDIT_DIR.glob("hermes_data_source_audit_*.json"))[-1],
    sorted(AUDIT_DIR.glob("hermes_safety_approval_audit_*.json"))[-1],
    sorted(AUDIT_DIR.glob("hermes_layer_test_results_*.json"))[-1],
    sorted(AUDIT_DIR.glob("hermes_command_test_results_*.json"))[-1],
]

for path in json_files:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("supabase_write_attempted") not in (False, None):
        print(f"Supabase write flag unexpected in {path.name}")
        sys.exit(1)

print("Audit scripts report no Supabase writes.")
