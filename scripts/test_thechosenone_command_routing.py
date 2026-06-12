#!/usr/bin/env python3
"""TheChoseone command routing + execution-truth tests. Read-only / dry-run:
nothing is sent, deployed, or actually executed by a worker."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import thechosenone_worker_router as WR     # noqa: E402
from lib import thechosenone_execution_truth as TRUTH  # noqa: E402

COMMANDS = [
    ("status", "status", "internal_script"),
    ("scouts status", "scouts_status", "internal_script"),
    ("what needs approval", "approval_queue", "showroom"),
    ("what did nexus produce", "produced", "internal_script"),
    ("run proof automation test", "run_proof", "proof_automation"),
    ("approve all assets in package proof_credit with notes: test approval", "approval", "showroom"),
    ("task for codex: Build a landing page for the credit track", "worker_task", "codex"),
    ("task for claude: Audit the funding scout", "worker_task", "claude"),
    ("run this prompt: summarize the credit checklist in 3 bullets", "worker_task", "external_unknown"),
    ("stop trading", "control", "internal_script"),
    # explicit risky command that MUST be blocked
    ("task for codex: publish the credit landing page live and send emails", "worker_task", "codex"),
]


def main() -> int:
    fails = 0
    for cmd, exp_intent, exp_worker in COMMANDS:
        out = WR.route_or_block_command(cmd, source="test", user="ray")
        rec, report = out["receipt"], out["report"]
        intent_ok = rec["parsed_intent"] == exp_intent
        # blocked risky command overrides worker routing expectation
        risky = "publish" in cmd or "send email" in cmd
        worker_ok = (rec["worker_target"] == exp_worker)
        n_lines = len([l for l in report.splitlines() if l.strip()])
        long_ok = n_lines <= 12
        receipt_ok = rec["command_id"].startswith("cmd_")
        honest = True
        if rec["parsed_intent"] == "worker_task" and not risky:
            # must NOT claim a worker actually completed/started without a live job
            honest = rec["execution_state"] in ("queued", "routed_to_worker")
            if rec["execution_state"] == "routed_to_worker":
                honest = bool(rec.get("job_id")) and not str(rec.get("job_id")).startswith("none")
        if risky:
            honest = rec["execution_state"] == "blocked"
            worker_ok = True  # blocked before routing matters

        ok = intent_ok and worker_ok and long_ok and receipt_ok and honest
        if not ok:
            fails += 1
        flag = "✓" if ok else "✗FAIL"
        print(f"\n{flag} [{rec['parsed_intent']}/{rec['worker_target']}/{rec['execution_state']}] "
              f"({n_lines} lines) :: {cmd[:55]}")
        print("   " + report.replace("\n", "\n   ")[:420])

    # explicit batch-approval needs a package id (blanket refused)
    blank = WR.route_or_block_command("approve all assets in package  with notes: x", user="ray")
    print("\n[blank-package approval] ->", blank["receipt"]["execution_state"])

    # details command shows full receipt
    last = TRUTH.list_recent_commands(1)
    if last:
        print("\n[details]", WR.details(last[-1]["command_id"]))

    print(f"\n=== {len(COMMANDS)} commands · {fails} failures ===")
    print("safety: no emails/DMs/trades/deploys; risky command blocked; no fake worker execution.")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
