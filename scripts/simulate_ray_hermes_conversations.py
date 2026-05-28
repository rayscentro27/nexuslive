"""
Simulate 7 Ray ↔ Hermes strategic conversations.
Validates that routing, artifact loading, and response quality all work end-to-end.
Saves all results to docs/reports/hermes_conversations/simulations/.

No artifact = no completion. Each conversation must produce a saved JSON.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parents[1] / ".env")
except ImportError:
    pass

from lib.hermes_collaboration_service import HermesCollaboration

SIM_DIR = Path("docs/reports/hermes_conversations/simulations")
SIM_DIR.mkdir(parents=True, exist_ok=True)

SIMULATED_CONVERSATIONS = [
    {
        "id": "sim_001",
        "description": "Travel catch-up: Ray just landed and wants a status update",
        "message": "catch me up — what did Nexus produce while I was traveling?",
        "expected_artifact_key": "ceo_packet",
        "validates": "travel_mode_catch_up",
    },
    {
        "id": "sim_002",
        "description": "Compliance inquiry: Ray wants to know what can be taught to clients",
        "message": "what can Nexus safely teach clients about credit repair right now?",
        "expected_artifact_key": "compliance_review",
        "validates": "compliance_gate_awareness",
    },
    {
        "id": "sim_003",
        "description": "Monetization decision: Ray wants the fastest revenue path",
        "message": "what's the fastest monetization path Nexus found in the last cycle?",
        "expected_artifact_key": "monetization_report",
        "validates": "monetization_first_response",
    },
    {
        "id": "sim_004",
        "description": "Mistake pattern review: Ray wants to know what Hermes keeps getting wrong",
        "message": "what mistakes are you repeating? show me the active patterns",
        "expected_artifact_key": "mistake_memory",
        "validates": "mistake_memory_transparency",
    },
    {
        "id": "sim_005",
        "description": "Pending approvals: Ray checks what needs his sign-off",
        "message": "what are you waiting on me for? show me pending handoffs",
        "expected_artifact_key": "handoffs",
        "validates": "handoff_routing",
    },
    {
        "id": "sim_006",
        "description": "Premium blocker: Ray wants to move off Beehiiv",
        "message": "Beehiiv is getting expensive. What's a free alternative we can use for the newsletter?",
        "expected_artifact_key": "premium_blockers",
        "validates": "premium_blocker_resolution",
    },
    {
        "id": "sim_007",
        "description": "Research queue: Ray wants to know what Nexus should work on next",
        "message": "what should you research overnight? build me a research queue for tomorrow",
        "expected_artifact_key": "continued_research",
        "validates": "continued_research_routing",
    },
]


def run_simulations() -> dict:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    hermes = HermesCollaboration()
    results = []
    passed = failed = artifact_missing = 0

    print(f"\n[sim] Running {len(SIMULATED_CONVERSATIONS)} Ray ↔ Hermes simulations…\n")

    for conv in SIMULATED_CONVERSATIONS:
        print(f"[sim] {conv['id']}: {conv['description']}")
        print(f"      Ray: {conv['message'][:70]}")

        result = hermes.handle(conv["message"])
        expected = conv["expected_artifact_key"]
        actual   = result["artifact_key"]
        art_status = result["artifact_status"]

        route_ok    = actual == expected
        has_reply   = len(result.get("answer", "")) > 20
        not_faking  = "[LLM" not in result.get("answer", "")[:50]

        if art_status == "artifact_missing":
            artifact_missing += 1
            status = "artifact_missing"
        elif route_ok and has_reply:
            passed += 1
            status = "passed"
        else:
            failed += 1
            status = "failed"

        print(f"      Route: {actual} (expected {expected}) → {'✅' if route_ok else '❌'}")
        print(f"      Artifact: {art_status} | Reply: {len(result.get('answer', ''))} chars")
        print(f"      Status: {status}\n")

        sim_result = {
            "sim_id":         conv["id"],
            "description":    conv["description"],
            "message":        conv["message"],
            "expected_key":   expected,
            "actual_key":     actual,
            "artifact_status": art_status,
            "route_ok":       route_ok,
            "has_reply":      has_reply,
            "status":         status,
            "validates":      conv["validates"],
            "hermes_reply":   result.get("answer", "")[:500],
        }
        results.append(sim_result)

        # Save individual conversation
        conv_path = SIM_DIR / f"simulation_{conv['id']}_{ts}.json"
        conv_path.write_text(json.dumps(sim_result, indent=2))

    summary = {
        "run_ts":          ts,
        "total":           len(SIMULATED_CONVERSATIONS),
        "passed":          passed,
        "failed":          failed,
        "artifact_missing": artifact_missing,
        "results":         results,
    }
    summary_path = SIM_DIR / f"simulation_summary_{ts}.json"
    summary_path.write_text(json.dumps(summary, indent=2))

    print(f"[sim] ── Summary ──────────────────────────────")
    print(f"  Total:           {summary['total']}")
    print(f"  Passed:          {passed}")
    print(f"  Failed:          {failed}")
    print(f"  Artifact missing: {artifact_missing} (expected — artifacts generated by cycle)")
    print(f"  Saved: {summary_path}")
    print(f"{'='*50}\n")

    return summary


if __name__ == "__main__":
    result = run_simulations()
    sys.exit(0 if result["failed"] == 0 else 1)
