#!/usr/bin/env python3
"""Test the war-room router: command verbs -> TheChoseone, conversation ->
Hermes Mobile, no double replies."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import nexus_war_room_router as R  # noqa: E402

CASES = [
    ("status", "thechoseone"),
    ("what needs approval", "thechoseone"),
    ("approve all assets in package proof_credit with notes: looks good", "thechoseone"),
    ("request revision for package proof_funding with notes: tighten", "thechoseone"),
    ("pause automation", "thechoseone"),
    ("/run daily report", "thechoseone"),
    ("!status", "thechoseone"),
    ("daily report", "thechoseone"),
    ("What is Nexus doing right now?", "hermes_mobile"),
    ("What needs my attention?", "hermes_mobile"),
    ("How do we make money in the next 30 days?", "hermes_mobile"),
    ("Explain the daily report in plain English.", "hermes_mobile"),
    ("What is the weakest part of Nexus?", "hermes_mobile"),
    ("Research Postiz and tell me if we should use it.", "hermes_mobile"),
    # Part 7 war-room quality cases
    ("Hermes, what should I do next?", "hermes_mobile"),
    ("how do I approve this?", "hermes_mobile"),
    ("Should we use Postiz?", "hermes_mobile"),
    ("Explain TheChoseone report", "hermes_mobile"),
    ("run monetization scout", "thechoseone"),
]


def main() -> int:
    fails = 0
    for msg, expect in CASES:
        r = R.route(msg)
        ok = r["target"] == expect
        # no-double-reply invariant: exactly one bot should_reply
        a = R.should_reply("thechoseone", msg)
        b = R.should_reply("hermes_mobile", msg)
        single = (a ^ b)
        flag = "✓" if ok and single else "✗FAIL"
        if not (ok and single):
            fails += 1
        print(f"  {flag} [{r['target']:13}] ({r['reason']}) :: {msg[:50]}")
    print(f"\n=== {len(CASES)} routed · {fails} failures · no-double-reply enforced ===")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
