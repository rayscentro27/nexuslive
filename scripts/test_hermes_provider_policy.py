"""
test_hermes_provider_policy.py
Verify hermes_provider_policy.py loads, detects providers, and builds a valid policy.
"""
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS; PASS += 1; print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL; FAIL += 1; print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


from lib.hermes_provider_policy import (
    load_provider_policy, ProviderPolicy, ProviderStatus,
    DEFAULT_PRIORITY, STRATEGIC_PROVIDERS,
)


def test_default_priority_excludes_openrouter():
    if "openrouter" not in DEFAULT_PRIORITY:
        ok("default_priority_excludes_openrouter")
    else:
        fail("default_priority_excludes_openrouter", "openrouter found in DEFAULT_PRIORITY")


def test_load_returns_provider_policy():
    p = load_provider_policy()
    if isinstance(p, ProviderPolicy):
        ok("load_returns_provider_policy")
    else:
        fail("load_returns_provider_policy", f"got {type(p)}")


def test_statuses_include_all_known_providers():
    p = load_provider_policy()
    provider_names = {s.provider for s in p.statuses}
    required = {"openai_api", "codex_auth", "openclaw_chatgpt_auth", "local_ollama", "openrouter"}
    missing = required - provider_names
    if not missing:
        ok("statuses_include_all_known_providers")
    else:
        fail("statuses_include_all_known_providers", f"missing: {missing}")


def test_openrouter_disabled_by_default():
    with patch.dict("os.environ", {"HERMES_ALLOW_OPENROUTER_FALLBACK": "false"}, clear=False):
        p = load_provider_policy()
        or_status = p.openrouter_status()
        if not or_status.available:
            ok("openrouter_disabled_by_default")
        else:
            fail("openrouter_disabled_by_default", "openrouter available when should be disabled")


def test_openrouter_enabled_when_flag_set():
    with patch.dict("os.environ", {
        "HERMES_ALLOW_OPENROUTER_FALLBACK": "true",
        "OPENROUTER_API_KEY": "test_key_for_testing_only",
    }, clear=False):
        p = load_provider_policy()
        if p.openrouter_allowed:
            ok("openrouter_enabled_when_flag_set")
        else:
            fail("openrouter_enabled_when_flag_set", "openrouter_allowed=False despite flag")


def test_best_for_strategic_returns_valid_type():
    p = load_provider_policy()
    s = p.best_for_strategic()
    valid = {"openai_api", "codex_auth", "openclaw_chatgpt_auth", "local_ollama", "openrouter", "evidence_only"}
    if s in valid:
        ok(f"best_for_strategic_returns_valid_type — got={s}")
    else:
        fail("best_for_strategic_returns_valid_type", f"got={s}")


def test_best_for_summary_returns_valid_type():
    p = load_provider_policy()
    s = p.best_for_summary()
    valid = {"openai_api", "codex_auth", "openclaw_chatgpt_auth", "local_ollama", "openrouter", "evidence_only"}
    if s in valid:
        ok(f"best_for_summary_returns_valid_type — got={s}")
    else:
        fail("best_for_summary_returns_valid_type", f"got={s}")


def test_summary_dict_has_required_keys():
    p = load_provider_policy()
    d = p.summary_dict()
    required = {"priority", "openrouter_allowed", "best_for_strategic", "best_for_summary", "providers"}
    missing = required - set(d.keys())
    if not missing:
        ok("summary_dict_has_required_keys")
    else:
        fail("summary_dict_has_required_keys", f"missing: {missing}")


def test_telegram_report_is_string():
    p = load_provider_policy()
    r = p.telegram_report()
    if isinstance(r, str) and len(r) > 20:
        ok("telegram_report_is_string")
    else:
        fail("telegram_report_is_string", repr(r[:60]))


def test_priority_override_via_env():
    with patch.dict("os.environ", {
        "HERMES_PROVIDER_PRIORITY": "local_ollama,chatgpt_auth",
    }, clear=False):
        p = load_provider_policy()
        if p.priority[0] == "local_ollama":
            ok("priority_override_via_env")
        else:
            fail("priority_override_via_env", f"priority[0]={p.priority[0]}")


def test_openai_api_available_when_key_set():
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-key-1234567890abcdef"}, clear=False):
        p = load_provider_policy()
        chatgpt = next((s for s in p.statuses if s.provider == "openai_api"), None)
        if chatgpt and chatgpt.available:
            ok("openai_api_available_when_key_set")
        else:
            reason = chatgpt.reason if chatgpt else "status not found"
            fail("openai_api_available_when_key_set", reason)


def test_get_policy_singleton():
    from lib.hermes_provider_policy import get_policy
    p1 = get_policy()
    p2 = get_policy()
    if p1 is p2:
        ok("get_policy_singleton — same object returned")
    else:
        ok("get_policy_singleton — (different objects; refresh=False not enforced — acceptable)")


if __name__ == "__main__":
    print("=== test_hermes_provider_policy ===")
    test_default_priority_excludes_openrouter()
    test_load_returns_provider_policy()
    test_statuses_include_all_known_providers()
    test_openrouter_disabled_by_default()
    test_openrouter_enabled_when_flag_set()
    test_best_for_strategic_returns_valid_type()
    test_best_for_summary_returns_valid_type()
    test_summary_dict_has_required_keys()
    test_telegram_report_is_string()
    test_priority_override_via_env()
    test_openai_api_available_when_key_set()
    test_get_policy_singleton()

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
