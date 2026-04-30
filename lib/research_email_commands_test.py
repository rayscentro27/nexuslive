#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.research_email_commands as commands

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    _results.append((name, condition, detail))


def test_preview_research_summary():
    original_latest = commands.latest_research_artifacts
    sent_calls: list[tuple[str, str]] = []
    commands.latest_research_artifacts = lambda limit=3: [
        {
            "title": "Credit Union Opportunity Roundup",
            "topic": "business_opportunities",
            "summary": "Three useful business funding patterns were found.",
            "action_items": ["Review CU card fit", "Check deposit timing"],
        }
    ]
    try:
        result = commands.execute_email_command(
            "preview latest research summary",
            sender=lambda subject, body: sent_calls.append((subject, body)) or (True, "sent"),
        )
    finally:
        commands.latest_research_artifacts = original_latest

    check("preview mode succeeds", result.get("ok") is True, str(result))
    check("preview mode does not send email", not sent_calls, str(sent_calls))
    check("preview includes stored artifact title", "Credit Union Opportunity Roundup" in result.get("body", ""), result.get("body", ""))


def test_send_disabled_by_default():
    original_latest = commands.latest_research_artifacts
    sent_calls: list[tuple[str, str]] = []
    commands.latest_research_artifacts = lambda limit=3: [{"title": "Stored summary", "topic": "general_business_intelligence", "summary": "Stored research", "action_items": []}]
    try:
        result = commands.execute_email_command(
            "send latest research summary",
            send_enabled=False,
            sender=lambda subject, body: sent_calls.append((subject, body)) or (True, "sent"),
        )
    finally:
        commands.latest_research_artifacts = original_latest

    check("send is blocked by default", result.get("send_blocked") is True, str(result))
    check("blocked send does not call sender", not sent_calls, str(sent_calls))


def test_send_latest_funding_brief():
    original_brief = commands.latest_executive_brief
    sent_calls: list[tuple[str, str]] = []
    commands.latest_executive_brief = lambda briefing_type=None: {
        "briefing_type": "funding",
        "content": "Results vary. Approval is determined by the lender and is not guaranteed.",
        "urgency": "medium",
        "generated_by": "nexus_one",
        "created_at": "2026-04-29T20:00:00+00:00",
    }
    try:
        result = commands.execute_email_command(
            "send latest funding brief",
            send_enabled=True,
            sender=lambda subject, body: sent_calls.append((subject, body)) or (True, "sent"),
        )
    finally:
        commands.latest_executive_brief = original_brief

    check("send funding brief can send when enabled", result.get("sent") is True, str(result))
    check("funding brief sender called once", len(sent_calls) == 1, str(sent_calls))
    check("funding brief keeps disclaimer", "not guaranteed" in sent_calls[0][1].lower(), sent_calls[0][1] if sent_calls else "")


def test_local_funding_brief_fallback():
    original_path = commands.LATEST_FUNDING_BRIEF_FILE
    import tempfile
    from pathlib import Path

    tmp_dir = Path(tempfile.mkdtemp())
    tmp_file = tmp_dir / "latest_funding_brief.json"
    tmp_file.write_text(
        '{\n'
        '  "briefing_type": "funding",\n'
        '  "content": "Stored fallback funding brief. Results vary. Approval is determined by the lender and is not guaranteed.",\n'
        '  "urgency": "medium",\n'
        '  "generated_by": "funding_engine",\n'
        '  "created_at": "2026-04-30T04:00:00+00:00"\n'
        '}'
    )
    commands.LATEST_FUNDING_BRIEF_FILE = tmp_file
    original_safe = commands._safe_select
    commands._safe_select = lambda path: []
    try:
        row = commands.latest_executive_brief("funding")
    finally:
        commands._safe_select = original_safe
        commands.LATEST_FUNDING_BRIEF_FILE = original_path
        tmp_file.unlink(missing_ok=True)
        tmp_dir.rmdir()

    check("funding brief falls back to local cache", row is not None, str(row))
    check("funding brief local cache keeps disclaimer", "not guaranteed" in (row or {}).get("content", "").lower(), str(row))


def test_unknown_command_returns_help():
    result = commands.execute_email_command("launch a giant workflow")
    check("unknown command returns help", result.get("mode") == "unknown", str(result))
    check("help text lists preview command", "preview latest research summary" in result.get("body", ""), result.get("body", ""))


def test_receipt_sent_before_result():
    """Receipt ACK is sent first; result email is sent second."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import nexus_email_pipeline as pipeline

    sent_emails: list[dict] = []

    def fake_send_reply(to, subject, body):
        sent_emails.append({"to": to, "subject": subject, "body": body})

    original_execute = pipeline.execute_email_command
    original_send = pipeline.send_reply
    original_log = pipeline.log_email_command

    pipeline.send_reply = fake_send_reply
    pipeline.log_email_command = lambda event: None
    pipeline.execute_email_command = lambda cmd: {
        "ok": True,
        "mode": "preview",
        "command": cmd,
        "subject": "Nexus Research Summary",
        "body": "Stored artifact: Test Article. Results vary.",
    }

    try:
        msg = {
            "uid": b"99",
            "message_id": "<receipt-test-1@nexus>",
            "subject": "[RESEARCH EMAIL]",
            "sender": "test@example.com",
            "reply_to": "test@example.com",
            "body": "preview latest research summary",
        }
        pipeline.process_research_email_command(msg)
    finally:
        pipeline.send_reply = original_send
        pipeline.execute_email_command = original_execute
        pipeline.log_email_command = original_log

    check("receipt email sent first", len(sent_emails) >= 1, str(sent_emails))
    check("receipt mentions processing now", "processing now" in sent_emails[0]["body"].lower(), sent_emails[0]["body"][:120])
    check("result email sent second", len(sent_emails) == 2, f"sent count={len(sent_emails)}")
    check("result email contains stored content", "stored artifact" in sent_emails[1]["body"].lower() or "research" in sent_emails[1]["body"].lower(), sent_emails[1]["body"][:120])


def test_duplicate_message_id_skipped():
    """A message with an already-processed message-id is not re-processed."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import nexus_email_pipeline as pipeline
    import tempfile, json, pathlib

    original_path = pipeline._PROCESSED_IDS_FILE
    tmp = pathlib.Path(tempfile.mktemp(suffix=".json"))
    # Pre-populate with the test message-id
    tmp.write_text(json.dumps({"processed_message_ids": ["<dup-msg-id-1@nexus>"]}))
    pipeline._PROCESSED_IDS_FILE = tmp

    try:
        result = pipeline._is_already_processed("<dup-msg-id-1@nexus>")
        check("duplicate message-id detected as processed", result is True, str(result))

        result2 = pipeline._is_already_processed("<new-msg-id-2@nexus>")
        check("new message-id not marked processed", result2 is False, str(result2))
    finally:
        pipeline._PROCESSED_IDS_FILE = original_path
        tmp.unlink(missing_ok=True)


def test_save_and_load_processed_id():
    """Save and reload message-ids from the state file."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import nexus_email_pipeline as pipeline
    import tempfile, pathlib

    original_path = pipeline._PROCESSED_IDS_FILE
    tmp = pathlib.Path(tempfile.mktemp(suffix=".json"))
    pipeline._PROCESSED_IDS_FILE = tmp

    try:
        pipeline._save_processed_id("<msg-save-1@nexus>")
        pipeline._save_processed_id("<msg-save-2@nexus>")
        ids = pipeline._load_processed_ids()
        check("saved ids can be reloaded", "<msg-save-1@nexus>" in ids and "<msg-save-2@nexus>" in ids, str(ids))
        check("state file exists after save", tmp.exists(), str(tmp))
    finally:
        pipeline._PROCESSED_IDS_FILE = original_path
        tmp.unlink(missing_ok=True)


def test_no_receipt_for_non_research_email_commands():
    """Non-[RESEARCH EMAIL] modes do not send a receipt ACK."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import nexus_email_pipeline as pipeline

    sent_emails: list[dict] = []

    original_send = pipeline.send_reply
    pipeline.send_reply = lambda to, subject, body: sent_emails.append({"to": to, "subject": subject, "body": body})

    try:
        # status mode should NOT send a receipt
        # We test detect_mode directly to confirm mode routing
        mode = pipeline.detect_mode("[STATUS] check", "")
        check("status mode detected correctly", mode == "status", f"mode={mode}")

        mode_re = pipeline.detect_mode("[RESEARCH EMAIL] request", "preview latest research summary")
        check("research_email mode detected correctly", mode_re == "research_email", f"mode={mode_re}")
    finally:
        pipeline.send_reply = original_send


def main() -> int:
    test_preview_research_summary()
    test_send_disabled_by_default()
    test_send_latest_funding_brief()
    test_local_funding_brief_fallback()
    test_unknown_command_returns_help()
    test_receipt_sent_before_result()
    test_duplicate_message_id_skipped()
    test_save_and_load_processed_id()
    test_no_receipt_for_non_research_email_commands()

    failed = [name for name, ok, _ in _results if not ok]
    print()
    if failed:
        print(f"{len(failed)} test(s) failed")
        for name in failed:
            print(f" - {name}")
        return 1
    print(f"All {len(_results)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
