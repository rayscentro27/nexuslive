#!/usr/bin/env python3
"""
Seed + exercise the Nexus Proof Automation Engine (V1, test_only/draft_only).
Seeds 5 demo projects, runs seeded scout missions, runs the 5 simulator scenarios,
generates compliance-safe asset drafts, registers Showroom packages, logs metrics,
runs the AI Improvement Scout, and writes the status report.

Local-only: no publish, email, payment, live trading, paid API, or auto-approval.
Usage: python3 scripts/run_proof_automation_seed.py [--reset]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import proof_automation as PA  # noqa: E402

SIM_SCENARIOS = [
    "I need help fixing my credit.",
    "I want business funding but I do not know where to start.",
    "I want to make money online with my interest in cleaning products.",
    "I saw a forex strategy on YouTube and want to test it.",
    "Research Postiz and tell me if Nexus should use it.",
]


def main() -> int:
    if "--reset" in sys.argv and PA.STORE.exists():
        PA.STORE.unlink()
        print("[reset] cleared store")
    seed = PA.seed_all()
    print(f"[seed] projects={seed['seeded_projects']} ai_recs={seed['ai_recommendations']}")
    sim_results = []
    for msg in SIM_SCENARIOS:
        r = PA.simulate(msg)
        sim_results.append(r)
        print(f"[sim] {r['track']:14} assets={r['assets']} findings={r['findings']} pkg={r['showroom_package']} ai={bool(r['ai_recommendation'])}")
    summ = PA.summary()
    print("[summary]", summ)

    # status report
    rp = ROOT / "reports" / "showroom" / "proof_automation_engine_status.md"
    rp.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Proof Automation Engine — Status", "_V1 · JSON-backed · test_only/draft_only · nothing published_\n",
             "## Summary counts", *[f"- {k}: {v}" for k, v in summ.items()], "",
             "## Seeded projects", *[f"- {pid}" for pid in seed["seeded_projects"]], "",
             "## Simulator results",
             *[f"- [{r['track']}] project={r['project_id']} assets={r['assets']} findings={r['findings']} showroom={r['showroom_package']}" for r in sim_results],
             "", "## Safety flags", *[f"- {k} = {v}" for k, v in PA.FLAGS.items()],
             "", "All generated assets are needs_review. APPROVED_LIVE is OFF."]
    rp.write_text("\n".join(lines) + "\n")
    print(f"[report] {rp.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
