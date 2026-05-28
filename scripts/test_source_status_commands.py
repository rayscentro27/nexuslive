"""
test_source_status_commands.py
Verify that "show source intake", "show artifact registry", and URL submission
commands route correctly through run_command().
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS; PASS += 1; print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL; FAIL += 1; print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


from hermes_command_router.intake import classify_intent


def test_show_source_intake_routes_correctly():
    intent, _, _ = classify_intent("show source intake")
    if intent == "source_intake_status":
        ok("show_source_intake_routes_correctly")
    else:
        fail("show_source_intake_routes_correctly", intent)


def test_what_links_did_i_send():
    intent, _, _ = classify_intent("what links did i send")
    if intent == "source_intake_status":
        ok("what_links_did_i_send")
    else:
        fail("what_links_did_i_send", intent)


def test_show_artifact_registry():
    intent, _, _ = classify_intent("show artifact registry")
    if intent == "artifact_registry_status":
        ok("show_artifact_registry")
    else:
        fail("show_artifact_registry", intent)


def test_what_artifacts_exist():
    intent, _, _ = classify_intent("what artifacts exist")
    if intent == "artifact_registry_status":
        ok("what_artifacts_exist")
    else:
        fail("what_artifacts_exist", intent)


def test_youtube_url_routes_to_source_intake():
    intent, _, _ = classify_intent("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    if intent == "source_intake":
        ok("youtube_url_routes_to_source_intake")
    else:
        fail("youtube_url_routes_to_source_intake", intent)


def test_github_url_routes_to_source_intake():
    intent, _, _ = classify_intent("https://github.com/anthropics/anthropic-sdk-python")
    if intent == "source_intake":
        ok("github_url_routes_to_source_intake")
    else:
        fail("github_url_routes_to_source_intake", intent)


def test_url_with_context_text_routes_to_source_intake():
    intent, _, _ = classify_intent("Check this out: https://youtube.com/watch?v=abc123 let me know what you think")
    if intent == "source_intake":
        ok("url_with_context_text_routes_to_source_intake")
    else:
        fail("url_with_context_text_routes_to_source_intake", intent)


def test_show_pending_source():
    intent, _, _ = classify_intent("show pending source")
    if intent == "source_intake_status":
        ok("show_pending_source")
    else:
        fail("show_pending_source", intent)


def test_backfill_artifact_registry():
    intent, _, _ = classify_intent("backfill the artifact registry")
    if intent == "source_intake_status":
        ok("backfill_artifact_registry — maps to source_intake_status")
    else:
        fail("backfill_artifact_registry", intent)


def test_show_unregistered_artifacts():
    intent, _, _ = classify_intent("show unregistered artifacts")
    if intent == "source_intake_status":
        ok("show_unregistered_artifacts")
    else:
        fail("show_unregistered_artifacts", intent)


def test_show_all_artifacts():
    intent, _, _ = classify_intent("show all artifacts")
    if intent == "artifact_registry_status":
        ok("show_all_artifacts")
    else:
        fail("show_all_artifacts", intent)


def test_source_intake_status_priority_medium():
    _, priority, _ = classify_intent("show source intake")
    if priority == "medium":
        ok("source_intake_status_priority_medium")
    else:
        fail("source_intake_status_priority_medium", priority)


if __name__ == "__main__":
    print("=== test_source_status_commands ===")
    test_show_source_intake_routes_correctly()
    test_what_links_did_i_send()
    test_show_artifact_registry()
    test_what_artifacts_exist()
    test_youtube_url_routes_to_source_intake()
    test_github_url_routes_to_source_intake()
    test_url_with_context_text_routes_to_source_intake()
    test_show_pending_source()
    test_backfill_artifact_registry()
    test_show_unregistered_artifacts()
    test_show_all_artifacts()
    test_source_intake_status_priority_medium()

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
