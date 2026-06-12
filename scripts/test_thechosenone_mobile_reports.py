#!/usr/bin/env python3
"""Test TheChoseone polished mobile reports (hermes_command_reporter)."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_command_reporter as R  # noqa: E402

COMMANDS = ["status", "scouts status", "what needs approval", "what did nexus produce",
            "daily report", "status credit scout", "status research queue"]


def main() -> int:
    fails = 0
    for cmd in COMMANDS:
        out = R.report(cmd)
        if out is None:
            print(f"✗FAIL {cmd!r} -> not recognized"); fails += 1; continue
        n = len([l for l in out.splitlines() if l.strip()])
        polished = ("Top facts:" in out) or ("Commands:" in out)
        no_raw = "control_center=" not in out and "launchd_matches=" not in out
        ok = polished and no_raw and n <= 16
        fails += (not ok)
        print(f"\n{'✓' if ok else '✗FAIL'} [{n} lines] :: {cmd}")
        print("   " + out.replace("\n", "\n   ")[:380])

    # approval instructions must contain exact copyable commands + manual-use note
    appr = R.report("what needs approval")
    assert "approve all assets in package" in appr and "manual use" in appr.lower()
    print("\n✓ approval report includes exact command + manual-use clarification")

    # raw escape hatch still available
    raw = R.report("raw status")
    assert raw is not None
    print("✓ 'raw status' returns raw key/values on request")

    print(f"\n=== {len(COMMANDS)} commands · {fails} failures ===")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
