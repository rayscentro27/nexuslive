#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "docs" / "reports" / "audits"

REQUIRED_PATTERNS = [
    "hermes_system_layer_audit_*.md",
    "hermes_system_layer_audit_*.json",
    "hermes_routing_order_audit_*.md",
    "hermes_routing_order_audit_*.json",
    "hermes_command_inventory_*.md",
    "hermes_command_inventory_*.json",
    "hermes_data_source_audit_*.md",
    "hermes_data_source_audit_*.json",
    "hermes_mock_stale_data_audit_*.md",
    "hermes_mock_stale_data_audit_*.json",
    "hermes_safety_approval_audit_*.md",
    "hermes_safety_approval_audit_*.json",
    "hermes_layer_test_results_*.md",
    "hermes_layer_test_results_*.json",
    "hermes_command_test_results_*.md",
    "hermes_command_test_results_*.json",
    "hermes_full_system_audit_summary_*.md",
    "hermes_full_system_audit_summary_*.json",
]

missing = [pattern for pattern in REQUIRED_PATTERNS if not list(AUDIT_DIR.glob(pattern))]
if missing:
    print("Missing audit outputs:")
    for item in missing:
        print(f"- {item}")
    sys.exit(1)

print("Audit outputs exist.")
