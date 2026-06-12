#!/usr/bin/env python3
"""Verify Hermes Mobile message cleaning + reply routing (offline, read-only).
/start -> intro, help -> help, weather -> unsupported honesty, Nexus question ->
real advisor reply, command -> drafted not executed, no intro for normal Qs."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_mobile_telegram as T   # noqa: E402
from lib import hermes_mobile_conversation as HM  # noqa: E402

# (raw input, expectation checker)
CASES = [
    ("@NexusHermesMobileBot how is the weather", "how is the weather"),
    ("Hermes, what should I do next?", "what should i do next?"),   # preserve '?'
    ("@NexusHermesMobileBot   ", ""),
    ("what is Nexus doing right now?", "what is nexus doing right now?"),
]


def main() -> int:
    print("=== mention/name stripping ===")
    fails = 0
    for raw, expect in CASES:
        got = T._strip_mention(raw).lower()
        ok = got == expect
        fails += (not ok)
        print(f"  {'✓' if ok else '✗FAIL'} {raw!r} -> {got!r}")

    print("\n=== reply routing (read-only) ===")
    INTRO = T.INTRO_TEXT[:30]
    checks = [
        ("/start", lambda r: r.startswith("Hermes Mobile Advisor")),
        ("help", lambda r: r.startswith("I can help")),
        ("@NexusHermesMobileBot how is the weather",
         lambda r: "don't have live weather" in r and "won't guess" in r),
        ("@NexusHermesMobileBot what is Nexus doing right now?",
         lambda r: INTRO not in r and len(r) > 40),
        ("Hermes, what should I do next?", lambda r: INTRO not in r),
        ("explain the daily report", lambda r: INTRO not in r),
        ("tell TheChoseone to run monetization scout",
         lambda r: "thechoseone" in r.lower() and "never execute" in r.lower()),
        ("approve all credit assets with notes: looks good",
         lambda r: ("send to TheChoseone" in r or "TheChoseone" in r)),
        ("@NexusHermesMobileBot   ", lambda r: r.startswith("I can help")),
    ]
    for msg, check in checks:
        r = T._reply_for(msg)
        ok = check(r)
        # safety: never claims execution
        executed_claim = "i approved" in r.lower() or "i executed" in r.lower() or "i sent the" in r.lower()
        ok = ok and not executed_claim
        fails += (not ok)
        print(f"\n  {'✓' if ok else '✗FAIL'} :: {msg}")
        print("     " + r.replace("\n", " ⏎ ")[:200])

    # capability guard
    assert HM.CAPABILITIES["execute_commands"] is False and HM.CAPABILITIES["write_nexus"] is False
    print(f"\n=== {len(CASES)+len(checks)} checks · {fails} failures · read-only verified ===")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
