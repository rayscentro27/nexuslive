#!/usr/bin/env python3
"""
create_telegram_approval_request.py — build a structured Telegram approval request (file-based).

Writes a request (md + json) + a pending log, links it to the board card, and OPTIONALLY sends via the
EXISTING gated Telegram sender (only if TELEGRAM_AUTO_REPORTS_ENABLED=true + token/chat set). It never
prints secrets, never executes the approved action, never enables the executor, never uploads/posts/schedules.

Since telegram_bot.py has no inline buttons, each "button" is rendered as a reply command Ray can send.

Usage:
  python scripts/create_telegram_approval_request.py --type CONTENT_REVIEW --title "..." \
     --content-id <id> --risk-level low --preview-path <mp4> --summary "..." \
     --allowed-scope "unlisted test only, improve/retry, reject, ask summary" \
     --blocked-actions "no public post, no scheduling, no paid tools, no secrets" [--send]
"""
from __future__ import annotations
import argparse, json, sys, uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.content_board import load_board, find, save_board, _now  # noqa: E402

REQ_DIR = ROOT / "reports" / "full_system_practice_mode" / "telegram_approval_requests"
LOG_DIR = ROOT / "reports" / "full_system_practice_mode" / "telegram_approval_logs"

# type -> list of (label, reply-command suffix)
TYPES: dict[str, list[tuple[str, str]]] = {
    "CONTENT_REVIEW": [("Approve for Unlisted Test", "approve {id} unlisted"), ("Improve / Retry", "retry {id}"),
                       ("Reject", "reject {id}"), ("Ask for Summary", "summary {id}")],
    "CONTROLLED_YOUTUBE_UPLOAD": [("Approve Unlisted Upload", "approve {id} unlisted-upload"), ("Reject", "reject {id}"),
                                  ("Revise Copy", "revise {id} copy"), ("View Preview Path", "preview {id}")],
    "NEWSLETTER_SEED_TEST": [("Approve Seed Test", "approve {id} seed"), ("Reject", "reject {id}"),
                             ("Revise Email", "revise {id} email"), ("Show Recipients", "recipients {id}")],
    "SOCIAL_PRIVATE_TEST": [("Approve Private Test Post", "approve {id} private"), ("Reject", "reject {id}"),
                            ("Revise Caption", "revise {id} caption"), ("Show Platform Details", "platform {id}")],
    "DEMO_TRADING_TEST": [("Approve Demo Test", "approve {id} demo"), ("Reject", "reject {id}"),
                          ("Show Risk Summary", "risk {id}"), ("Run Check-Only First", "checkonly {id}")],
    "NETLIFY_TEST_PAGE": [("Approve Test Deploy", "approve {id} test-deploy"), ("Reject", "reject {id}"),
                          ("Show Diff", "diff {id}"), ("Preview Locally First", "previewlocal {id}")],
    "TOOL_INSTALL_EVALUATION": [("Approve Tool Lab Install", "approve {id} toollab"), ("Reject", "reject {id}"),
                                ("More Info", "info {id}"), ("Safety Report", "safety {id}")],
    "GOAL_MODE_RECOMMENDATION": [("Approve Next Run", "approve {id} next-run"), ("Reject", "reject {id}"),
                                 ("Revise Plan", "revise {id} plan"), ("Show Evidence", "evidence {id}")],
}


def maybe_send(text: str) -> dict:
    """Reuse the existing gated send posture. Sends ONLY if explicitly enabled. Never prints secrets."""
    import os
    if os.getenv("TELEGRAM_AUTO_REPORTS_ENABLED", "false").lower() != "true":
        return {"sent": False, "reason": "TELEGRAM_AUTO_REPORTS_ENABLED!=true (request written, not sent)"}
    token = os.getenv("HERMES_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("HERMES_CHAT_ID", "")
    if not (token and chat):
        return {"sent": False, "reason": "bot token or chat id not set"}
    try:
        import requests
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat, "text": text}, timeout=15).json()
        return {"sent": bool(r.get("ok")), "message_id": r.get("result", {}).get("message_id")}
    except Exception as exc:
        return {"sent": False, "reason": f"send error: {type(exc).__name__}"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Create a Telegram approval request (file-based)")
    ap.add_argument("--type", required=True, choices=sorted(TYPES))
    ap.add_argument("--title", required=True)
    ap.add_argument("--content-id", default="")
    ap.add_argument("--approval-id", default="")
    ap.add_argument("--risk-level", default="low", choices=["low", "medium", "high"])
    ap.add_argument("--preview-path", default="")
    ap.add_argument("--summary", default="")
    ap.add_argument("--allowed-scope", default="")
    ap.add_argument("--blocked-actions", default="")
    ap.add_argument("--output-path", default=None)
    ap.add_argument("--send", action="store_true")
    args = ap.parse_args()

    REQ_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    rid = "tgr-" + uuid.uuid4().hex[:10]
    options = [(label, cmd.format(id=rid)) for label, cmd in TYPES[args.type]]

    md = [f"# Telegram Approval Request — {args.type}",
          f"# request_id: {rid} · DECISION-ONLY (no command executes a broad action)",
          "",
          f"- **Title:** {args.title}",
          f"- **content_id:** {args.content_id or '(none)'}",
          f"- **approval_id:** {args.approval_id or '(none)'}",
          f"- **risk_level:** {args.risk_level}",
          f"- **preview:** {args.preview_path or '(none)'}",
          "",
          f"## Summary\n{args.summary or '(none)'}",
          "",
          f"## Allowed scope\n{args.allowed_scope or '(internal/controlled test only)'}",
          "",
          f"## Blocked (not approved by this request)\n{args.blocked_actions or 'no public post, no schedule, no paid tools, no secrets'}",
          "",
          "## Reply options (no inline buttons exist → reply with a command)"]
    for label, cmd in options:
        md.append(f"- **{label}** → `/{cmd}`")
    md += ["",
           "_This request records a decision only. Approving does NOT upload/post/schedule/enable the executor; "
           "those stay behind their own gates. Generated by create_telegram_approval_request.py · " + _now() + "_"]
    text = "\n".join(md)

    out = Path(args.output_path) if args.output_path else REQ_DIR / f"{(args.content_id.split('-')[0] or rid)}_{args.type.lower()}.md"
    if not out.is_absolute():
        out = (ROOT / out)
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n", encoding="utf-8")

    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            return str(p)

    record = {"request_id": rid, "type": args.type, "title": args.title, "content_id": args.content_id,
              "approval_id": args.approval_id, "risk_level": args.risk_level, "preview_path": args.preview_path,
              "status": "pending", "options": [c for _, c in options], "created_at": _now(),
              "request_path": rel(out)}
    (REQ_DIR / f"{rid}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    with (LOG_DIR / f"{rid}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"event": "created", "at": _now(), **record}) + "\n")

    # link to board card (additive; never clobber)
    linked = False
    if args.content_id:
        cards = load_board()
        c = find(cards, args.content_id)
        if c:
            c["telegram_approval_request_id"] = rid
            c["telegram_approval_status"] = "pending"
            c["telegram_last_prompted_at"] = _now()
            c["updated_at"] = _now()
            save_board(cards)
            linked = True

    send_result = maybe_send(text) if args.send else {"sent": False, "reason": "--send not passed (write-only)"}
    print(f"request: {rel(out)} · id={rid} · type={args.type} · risk={args.risk_level}")
    print(f"board linked: {linked} · telegram: {send_result}")
    print("NO action executed · executor not enabled · no upload/post/schedule · no secrets printed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
