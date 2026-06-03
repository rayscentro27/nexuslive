#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / "docs" / "reports" / "audits"
patterns = [
    r"SUPABASE_SERVICE_ROLE_KEY\s*=",
    r"SUPABASE_KEY\s*=",
    r"OPENROUTER_API_KEY\s*=",
    r"OPENAI_API_KEY\s*=",
    r"ANTHROPIC_API_KEY\s*=",
    r"HERMES_GATEWAY_KEY\s*=",
    r"ACCESS_TOKEN\s*=",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    r"password\s*[:=]\s*\S+",
    r"https://[A-Za-z0-9-]+\.supabase\.co",
    r"\beyJ[A-Za-z0-9_\-]{20,}\b",
    r"\bsk-[A-Za-z0-9]{20,}\b",
]

for path in AUDIT_DIR.glob("*.md"):
    text = path.read_text(encoding="utf-8")
    for pattern in patterns:
        if re.search(pattern, text, flags=re.I):
            print(f"Potential secret marker in {path.name}: {pattern}")
            sys.exit(1)
for path in AUDIT_DIR.glob("*.json"):
    text = path.read_text(encoding="utf-8")
    for pattern in patterns:
        if re.search(pattern, text, flags=re.I):
            print(f"Potential secret marker in {path.name}: {pattern}")
            sys.exit(1)

print("Audit outputs contain no secret markers.")
