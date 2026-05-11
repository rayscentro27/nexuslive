#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VENV_BIN = ROOT / ".venv-notebooklm" / "bin"


def _run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


def main() -> int:
    result = {
        "isolated_env": str(ROOT / ".venv-notebooklm"),
        "candidates": {
            "notebooklm-cli": "community/unofficial (PyPI package)",
            "notebooklm-py": "community/unofficial Python client",
            "nlm": "command exposed by notebooklm-cli package",
            "mcp": "varies by community project; not installed in this pass",
        },
        "installed": False,
        "version": "",
        "help_ok": False,
        "auth_notes": [
            "CLI requires interactive auth/login flow.",
            "Do not store auth secrets in repo files.",
            "No cookies/tokens captured in this diagnostics script.",
        ],
    }

    nlm = VENV_BIN / "nlm"
    if nlm.exists():
        rc_v, out_v = _run([str(nlm), "--version"])
        rc_h, out_h = _run([str(nlm), "--help"])
        result["installed"] = rc_v == 0 and rc_h == 0
        result["version"] = out_v.splitlines()[0] if out_v else ""
        result["help_ok"] = "NotebookLM CLI" in out_h

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
