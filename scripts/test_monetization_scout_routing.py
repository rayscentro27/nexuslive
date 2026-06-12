#!/usr/bin/env python3
"""Regression: pasted source + monetization intent routes to the Monetization Scout
(not evidence dump); short asks without a source do not; risky claims are flagged."""
import sys; sys.path.insert(0, ".")
from lib.hermes_monetization_scout import should_handle, run_scout, detect_risks
from lib.hermes_conversational_router import route_conversational_intent

TRANSCRIPT = ("Act as a Nexus Monetization Scout. Transcript: make money with Claude AI - "
              "AI content creation, newsletters, social posts, video scripts for small businesses. "
              "People make $10,000 a month, passive income, guaranteed clients. What can Nexus do with this?\n"
              + "filler line\n" * 10)

def main():
    f = 0
    # 1) pasted source + intent -> scout
    assert should_handle(TRANSCRIPT), "should_handle must be True for transcript+intent"
    resp = route_conversational_intent(TRANSCRIPT) or ""
    assert "MONETIZATION SCOUT" in resp, "router must route to scout"
    assert "30-Day AI Content Growth Pack" in resp, "must recommend the Nexus-first pack"
    assert "NEXT SAFE ACTION" in resp, "must end with a next safe action"
    print("PASS: transcript+intent -> Monetization Scout w/ 30-Day pack + next action")
    # 2) short monetization ask WITHOUT a pasted source -> not the scout
    assert not should_handle("how do we make money?"), "short ask must NOT trigger scout"
    print("PASS: short ask without source does not trigger scout")
    # 3) risky claims flagged
    risks = detect_risks(TRANSCRIPT)
    for need in ("income claim", "guarantee claim", "easy-money claim"):
        assert need in risks, f"missing risk flag: {need}"
    print("PASS: risk claims flagged:", risks)
    print("ALL TESTS PASSED")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
