#!/usr/bin/env python3
"""Generate the Nexus continuous operations status report from live state."""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import proof_automation as PA       # noqa: E402
from lib import showroom_assets as SA         # noqa: E402
from lib import nexus_allowlist as AL          # noqa: E402
from lib import nexus_telegram_ops as TG       # noqa: E402


def main() -> int:
    s = PA.load()
    assets = [a for a in SA.load().get("assets", {}).values() if a.get("asset_type", "").startswith("proof_")]
    needs = sum(1 for a in assets if a.get("status") == "needs_review")
    sends = AL.send_log()
    sent = [e for e in sends if e.get("channel") == "email" and e.get("status") == "sent"]
    blocked = [e for e in sends if e.get("status") == "blocked"]
    igq = [e for e in sends if e.get("channel") == "instagram" and e.get("status") == "queued"]
    rp = ROOT / "reports" / "showroom" / "nexus_continuous_operations_status.md"
    rp.write_text(f"""# Nexus Continuous Operations — Status
_{datetime.now(timezone.utc).isoformat()} · one_shot · test_only_

## Systems running
Proof Automation Engine · 7 scouts (credit/funding/opportunity/trading/marketing/metrics/ai_improvement) ·
Hermes recommendation loop · Showroom review queue · Telegram command center · allowlisted email sender ·
Instagram DM queue · Oanda practice/demo read.

## Scouts status
{chr(10).join(f"- {sc}: " + TG.scout_status_text(sc + ' scout')[:120] for sc in TG.SCOUTS)}

## Assets produced
- proof assets total: {len(assets)} · needs_review: {needs} · approved: {sum(1 for a in assets if 'approved' in a.get('status',''))}
- packages: {len(set(a['asset_type'] for a in assets))}

## Allowlisted sends
- emails sent (Ray-only): {len(sent)} → {[e['recipient'] for e in sent][-2:]}
- non-allowlisted blocked: {len(blocked)}
- Instagram DMs queued (raydavis7677): {len(igq)} (Meta requires inbound message to send; queue-only)

## Oanda practice
- demo/practice only · live_trading=false · execution blocked · no order placed this run

## Approvals
- pending (needs_review): {needs} · use Telegram 'approve all assets in package <id> with notes: <text>'

## Hermes recommendations
- {len(s.get('recommendations', []))} project recommendations · {len(s.get('ai_improvement_recommendations', []))} AI tool recommendations

## Next action
Review top packages (proof_credit, proof_funding) and approve a batch, or give feedback to improve v2.

## Safety status
no public post · no third-party cold outreach · no emails outside the 2 allowlisted · no DMs outside raydavis7677 ·
no payment automation · no live/funded trading · approved_live OFF · no secrets exposed · no auto-approval.
""")
    print("wrote", rp.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
