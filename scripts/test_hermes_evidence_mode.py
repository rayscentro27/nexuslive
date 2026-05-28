"""
test_hermes_evidence_mode.py — Tests for lib/hermes_evidence_mode.py
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_evidence_mode import (
    HermesEvidenceMode,
    is_fake_trading_claim,
    has_theatrical_language,
    is_beehiiv_query,
    format_missing,
    verified_status_block,
    find_evidence,
    require_evidence,
)

ev = HermesEvidenceMode()
PASS = 0
FAIL = 0


def check(desc: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  ✅ {desc}")
        PASS += 1
    else:
        print(f"  ❌ FAIL: {desc}")
        FAIL += 1


print("\n=== test_hermes_evidence_mode ===\n")

# 1. Theatrical language detection
check("taps tablet blocked",      ev.has_theatrical_language("*taps tablet* Let me check..."))
check("sharp inhale blocked",     ev.has_theatrical_language("*sharp inhale* — this is bad"))
check("leans forward blocked",    ev.has_theatrical_language("*leans forward* tracking live"))
check("normal text allowed",      not ev.has_theatrical_language("Here is the latest CEO packet."))

# 2. Fake trading claim detection
check("trade placed blocked",     ev.is_fake_trading_claim("trade placed at 1.0832"))
check("scalp active blocked",     ev.is_fake_trading_claim("scalp active, target 1.0850"))
check("entering long blocked",    ev.is_fake_trading_claim("Entering long EUR/USD"))
check("order confirmed blocked",  ev.is_fake_trading_claim("order confirmed, filled at 1.0831"))
check("normal trade query ok",    not ev.is_fake_trading_claim("show me oanda demo status"))

# 3. Beehiiv intent normalization
check("beehiiv detected",         is_beehiiv_query("what's a free alternative to beehiiv?"))
check("beehive detected",         is_beehiiv_query("I meant beehive, the newsletter platform"))
check("bee hive detected",        is_beehiiv_query("replace bee hive with something free"))
check("behive detected",          is_beehiiv_query("behive is too expensive"))
check("newsletter alt detected",  is_beehiiv_query("newsletter alternative recommendations"))
check("unrelated not detected",   not is_beehiiv_query("what's the best trading strategy"))

# 4. format_missing response
missing_resp = format_missing("show me the CEO packet")
check("missing response contains 'do not have verified'", "do not have verified evidence" in missing_resp.lower())
check("missing response contains next action",            "next safe action" in missing_resp.lower())

# 5. block_unverified_operational_claim
blocked, phrases = ev.block_unverified_operational_claim("I taps tablet and start tracking live")
check("theatrical in block_unverified returns True",  blocked)
check("theatrical phrases listed",                    len(phrases) > 0)

blocked2, phrases2 = ev.block_unverified_operational_claim("trade placed at current market")
check("fake trade in block_unverified returns True",  blocked2)

clean_resp = "Here are the last 5 entries from the decision log."
blocked3, phrases3 = ev.block_unverified_operational_claim(clean_resp)
check("clean response not blocked",                   not blocked3)

# 6. extract_claims_from_response
claims = ev.extract_claims_from_response("Hermes processed 5 videos and analyzed 3 transcripts.")
verbs_found = [c["verb"] for c in claims]
check("processed extracted",  "processed" in verbs_found)
check("analyzed extracted",   "analyzed" in verbs_found)

# 7. verified_status_block returns a string
vsb = verified_status_block()
check("verified_status_block is a string",            isinstance(vsb, str))
check("verified_status_block has header",             "NEXUS VERIFIED STATUS" in vsb)

# 8. find_evidence returns EvidenceResult
result = find_evidence("show me pending handoffs")
check("find_evidence returns EvidenceResult",         hasattr(result, "found"))
check("find_evidence detects correct claim_type",     result.claim_type == "approval_queue")

# 9. require_evidence
result2 = require_evidence("oanda_demo", "show oanda demo")
check("require_evidence ceo_packet works",            result2.claim_type == "oanda_demo")

print(f"\nResults: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
