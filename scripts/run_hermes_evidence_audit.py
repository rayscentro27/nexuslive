"""
run_hermes_evidence_audit.py
==============================
Audit all Hermes evidence claim types against actual artifacts on disk.
Reports which claim types have verified artifacts and which are missing.

NO ARTIFACT = NO CLAIM. This script makes that contract visible.

Output:
  Console: full evidence audit table
  docs/reports/evidence/hermes_evidence_audit_<ts>.json
  docs/reports/evidence/hermes_evidence_audit_<ts>.md
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EVIDENCE_DIR = ROOT / "docs" / "reports" / "evidence"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main() -> None:
    from lib.hermes_evidence_mode import (
        CLAIM_EVIDENCE_MAP,
        HermesEvidenceMode,
        verified_status_block,
    )

    ts       = _ts()
    ev       = HermesEvidenceMode()
    results  = []
    missing  = []
    present  = []

    print(f"\n{'='*60}")
    print(f"HERMES EVIDENCE AUDIT — {_now()}")
    print(f"{'='*60}\n")

    CLAIM_LABELS = {
        "approval_queue":       "Approval Queue (handoffs)",
        "decisions_made":       "Decision Log",
        "research_completed":   "Research Packets",
        "youtube_processed":    "YouTube Sources",
        "youtube_transcript":   "YouTube Transcripts",
        "trading_backtest":     "Trading Backtest Results",
        "oanda_demo":           "OANDA Demo Execution",
        "premium_blocker":      "Premium Blocker Resolutions",
        "github_trends":        "GitHub Trend Reports",
        "content_generated":    "Content Generated",
        "ceo_packet":           "CEO Packet",
        "monetization_packet":  "Monetization Plan",
        "compliance_review":    "Compliance Reviews",
        "notifications":        "Proactive Notifications",
        "provider_status":      "Provider Status",
        "strategy_validation":  "Strategy Validation",
    }

    for claim_type in CLAIM_EVIDENCE_MAP:
        result = ev.require_evidence_for_claim(claim_type, f"audit: {claim_type}")
        label  = CLAIM_LABELS.get(claim_type, claim_type.replace("_", " ").title())

        if result.found:
            latest = Path(result.paths[-1]).name
            status_icon = "✅"
            status_text = "PRESENT"
            present.append(claim_type)
        else:
            latest = "none"
            status_icon = "❌"
            status_text = "MISSING"
            missing.append(claim_type)

        print(f"{status_icon} {label:40s} [{status_text}]")
        if result.found and result.paths:
            print(f"   Latest: {latest}")

        results.append({
            "claim_type":  claim_type,
            "label":       label,
            "status":      status_text,
            "found":       result.found,
            "artifacts":   result.paths,
            "latest":      latest,
        })

    print(f"\n{'─'*60}")
    print(f"SUMMARY: {len(present)}/{len(results)} claim types have verified artifacts")
    if missing:
        print(f"\nMISSING ({len(missing)}):")
        for m in missing:
            action = ev._suggest_next_action(m)
            print(f"  • {m.replace('_', ' ')}")
            print(f"    Next: {action[:100]}")

    print(f"\n{'─'*60}")
    print("\nVERIFIED STATUS BLOCK:\n")
    print(verified_status_block())

    # Save artifacts
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    json_path = EVIDENCE_DIR / f"hermes_evidence_audit_{ts}.json"
    json_path.write_text(json.dumps({
        "audited_at":       _now(),
        "total_claim_types": len(results),
        "present_count":    len(present),
        "missing_count":    len(missing),
        "present":          present,
        "missing":          missing,
        "details":          results,
    }, indent=2))

    # Build markdown report
    rows = ""
    for r in results:
        icon = "✅" if r["found"] else "❌"
        rows += f"| {icon} | {r['label']} | {r['status']} | {r['latest'][:50]} |\n"

    missing_actions = ""
    for m in missing:
        action = ev._suggest_next_action(m)
        missing_actions += f"\n### {m.replace('_', ' ').title()}\n```\n{action}\n```\n"

    md_path = EVIDENCE_DIR / f"hermes_evidence_audit_{ts}.md"
    md_path.write_text(f"""# Hermes Evidence Audit
*Generated: {_now()}*

**Summary:** {len(present)}/{len(results)} claim types have verified artifacts.

---

## Evidence Status

| Status | Claim Type | Result | Latest Artifact |
|---|---|---|---|
{rows}

---

## Missing — Recommended Actions
{missing_actions or '*(all claim types have artifacts)*'}

---

{verified_status_block()}
""")

    print(f"\n  Saved: {json_path}")
    print(f"  Saved: {md_path}")
    print(f"\n[DONE] Evidence audit complete.")


if __name__ == "__main__":
    main()
