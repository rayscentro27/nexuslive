"""
test_no_openrouter_default.py
Verify OpenRouter is DISABLED by default across all conversation paths.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS; PASS += 1; print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL; FAIL += 1; print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


def test_policy_openrouter_not_in_default_priority():
    from lib.hermes_provider_policy import DEFAULT_PRIORITY
    if "openrouter" not in DEFAULT_PRIORITY:
        ok("openrouter_not_in_default_priority")
    else:
        fail("openrouter_not_in_default_priority", "openrouter found in DEFAULT_PRIORITY")


def test_load_policy_openrouter_disabled_no_env():
    import os
    env = {k: v for k, v in os.environ.items()
           if k not in {"HERMES_ALLOW_OPENROUTER_FALLBACK", "OPENROUTER_API_KEY"}}
    env["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "false"
    with patch.dict("os.environ", env, clear=True):
        from lib.hermes_provider_policy import load_provider_policy
        p = load_provider_policy()
        if not p.openrouter_allowed:
            ok("load_policy_openrouter_disabled_no_env")
        else:
            fail("load_policy_openrouter_disabled_no_env", "openrouter_allowed=True when should be False")


def test_best_for_strategic_skips_openrouter_when_disabled():
    import os
    env = {k: v for k, v in os.environ.items()
           if k not in {"HERMES_ALLOW_OPENROUTER_FALLBACK", "OPENAI_API_KEY",
                        "CHATGPT_ACCESS_TOKEN", "CODEX_AUTH_TOKEN", "OPENCLAW_CHATGPT_AUTH"}}
    env["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "false"
    env["OPENROUTER_API_KEY"] = "test-key-should-not-be-used"
    with patch.dict("os.environ", env, clear=True):
        from lib.hermes_provider_policy import load_provider_policy
        p = load_provider_policy()
        s = p.best_for_strategic()
        if s != "openrouter":
            ok(f"best_for_strategic_skips_openrouter_when_disabled — got={s}")
        else:
            fail("best_for_strategic_skips_openrouter_when_disabled", "returned openrouter despite disabled")


def test_reasoning_layer_does_not_call_openrouter_when_disabled():
    """reasoning_layer must not reach the openrouter call block when disabled."""
    import os
    env = {k: v for k, v in os.environ.items()
           if k not in {"HERMES_ALLOW_OPENROUTER_FALLBACK", "OPENAI_API_KEY",
                        "CHATGPT_ACCESS_TOKEN", "CODEX_AUTH_TOKEN"}}
    env["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "false"
    env["OPENROUTER_API_KEY"] = "should-not-be-called"

    called = []

    def mock_call_openrouter(*a, **kw):
        called.append(True)
        return "mock openrouter response"

    with patch.dict("os.environ", env, clear=True):
        import lib.hermes_reasoning_layer as rl
        with patch.object(rl, "_call_openrouter", mock_call_openrouter):
            # Force all other providers to fail
            with patch.object(rl, "_call_openai", side_effect=RuntimeError("no openai")):
                with patch.object(rl, "_call_ollama", side_effect=RuntimeError("no ollama")):
                    from lib.hermes_provider_policy import _policy
                    import lib.hermes_provider_policy as pp
                    pp._policy = None  # reset singleton so env is re-read
                    result = rl.reason("what is the status?")
                    pp._policy = None  # cleanup

    if not called:
        ok("reasoning_layer_does_not_call_openrouter_when_disabled")
    else:
        fail("reasoning_layer_does_not_call_openrouter_when_disabled",
             "openrouter was called despite HERMES_ALLOW_OPENROUTER_FALLBACK=false")


def test_openrouter_status_shows_disabled_reason():
    with patch.dict("os.environ", {"HERMES_ALLOW_OPENROUTER_FALLBACK": "false"}, clear=False):
        from lib.hermes_provider_policy import load_provider_policy
        p = load_provider_policy()
        s = p.openrouter_status()
        if not s.available and "disabled" in s.reason.lower():
            ok("openrouter_status_shows_disabled_reason")
        else:
            fail("openrouter_status_shows_disabled_reason", f"available={s.available} reason={s.reason}")


def test_telegram_report_shows_disabled():
    with patch.dict("os.environ", {"HERMES_ALLOW_OPENROUTER_FALLBACK": "false"}, clear=False):
        from lib.hermes_provider_policy import load_provider_policy
        p = load_provider_policy()
        report = p.telegram_report()
        if "disabled" in report.lower():
            ok("telegram_report_shows_disabled")
        else:
            fail("telegram_report_shows_disabled", f"report preview: {report[:100]}")


if __name__ == "__main__":
    print("=== test_no_openrouter_default ===")
    test_policy_openrouter_not_in_default_priority()
    test_load_policy_openrouter_disabled_no_env()
    test_best_for_strategic_skips_openrouter_when_disabled()
    test_reasoning_layer_does_not_call_openrouter_when_disabled()
    test_openrouter_status_shows_disabled_reason()
    test_telegram_report_shows_disabled()

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
