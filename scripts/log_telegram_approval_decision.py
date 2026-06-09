#!/usr/bin/env python3
"""
log_telegram_approval_decision.py — record Ray's reply to an approval request (decision-only).

Appends the decision to the request log and updates the board card's telegram_decision fields.
It RECORDS a decision; it NEVER executes the action: it does not change status to Approved*/Published,
does not upload/post/schedule, does not enable the executor, does not send email/money. Moving a card
forward still requires the guarded content_board_update.py --ray-approved in a separate explicit step.

Usage:
  python scripts/log_telegram_approval_decision.py --request-id tgr-xxxx --decision approve_unlisted [--note "..."]
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.content_board import load_board, find, save_board, _now  # noqa: E402

REQ_DIR = ROOT / "reports" / "full_system_practice_mode" / "telegram_approval_requests"
LOG_DIR = ROOT / "reports" / "full_system_practice_mode" / "telegram_approval_logs"

# decision -> recorded telegram_approval_status (never executes anything)
DECISIONS = {
    "approve_unlisted": "approved", "approve_unlisted_upload": "approved", "approve_seed": "approved",
    "approve_private": "approved", "approve_demo": "approved", "approve_test_deploy": "approved",
    "approve_toollab": "approved", "approve_next_run": "approved",
    "retry": "retry", "reject": "rejected",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Record a Telegram approval decision (decision-only, no execution)")
    ap.add_argument("--request-id", required=True)
    ap.add_argument("--decision", required=True, choices=sorted(DECISIONS))
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    rec_path = REQ_DIR / f"{args.request_id}.json"
    if not rec_path.exists():
        print(f"ERROR: no request {args.request_id}", file=sys.stderr)
        return 2
    record = json.loads(rec_path.read_text())
    status = DECISIONS[args.decision]
    record["status"] = status
    record["decision"] = args.decision
    record["decided_at"] = _now()
    rec_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with (LOG_DIR / f"{args.request_id}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "decision", "at": _now(), "decision": args.decision,
                            "status": status, "note": args.note}) + "\n")

    linked = False
    cid = record.get("content_id")
    if cid:
        cards = load_board()
        c = find(cards, cid)
        if c:
            c["telegram_decision"] = args.decision
            c["telegram_decision_at"] = _now()
            c["telegram_approval_status"] = status
            c["updated_at"] = _now()
            save_board(cards)
            linked = True

    print(f"recorded: {args.request_id} · decision={args.decision} · status={status} · board linked={linked}")
    print("DECISION RECORDED ONLY — no upload/post/schedule, executor not enabled.")
    print("To actually advance the card (Ray's explicit step): "
          "content_board_update.py --id <id> --ray-approved --status 'Approved for Unlisted' --approval-status approved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
