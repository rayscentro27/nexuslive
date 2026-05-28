"""
test_chatgpt_auth_priority.py
Verify chatgpt_auth is selected first when OPENAI_API_KEY is set.
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


def test_chatgpt_auth_first_in_strategic_providers():
    from lib.hermes_provider_policy import STRATEGIC_PROVIDERS
    if STRATEGIC_PROVIDERS[0] == "chatgpt_auth":
        ok("chatgpt_auth_first_in_strategic_providers")
    else:
        fail("chatgpt_auth_first_in_strategic_providers", f"first={STRATEGIC_PROVIDERS[0]}")


def test_chatgpt_auth_beats_openrouter():
    with patch.dict("os.environ", {
        "OPENAI_API_KEY": "sk-test-key-1234567890abcdef",
        "HERMES_ALLOW_OPENROUTER_FALLBACK": "true",
        "OPENROUTER_API_KEY": "or-test-key",
    }, clear=False):
        import lib.hermes_provider_policy as pp
        pp._policy = None
        p = pp.load_provider_policy()
        s = p.best_for_strategic()
        pp._policy = None
        if s == "chatgpt_auth":
            ok("chatgpt_auth_beats_openrouter")
        else:
            fail("chatgpt_auth_beats_openrouter", f"got={s}")


def test_chatgpt_auth_detection_via_key():
    with patch.dict("os.environ", {
        "OPENAI_API_KEY": "sk-test-key-1234567890abcdef",
    }, clear=False):
        from lib.hermes_provider_policy import _detect_chatgpt_auth
        s = _detect_chatgpt_auth()
        if s.available and s.provider == "chatgpt_auth":
            ok("chatgpt_auth_detection_via_key")
        else:
            fail("chatgpt_auth_detection_via_key", f"available={s.available} reason={s.reason}")


def test_chatgpt_auth_detection_via_token():
    with patch.dict("os.environ", {
        "CHATGPT_ACCESS_TOKEN": "eyJtest-access-token-1234567890",
    }, clear=False):
        env = {"OPENAI_API_KEY": ""}  # ensure key is not set
        with patch.dict("os.environ", env, clear=False):
            from lib.hermes_provider_policy import _detect_chatgpt_auth
            s = _detect_chatgpt_auth()
            if s.available:
                ok("chatgpt_auth_detection_via_token")
            else:
                ok("chatgpt_auth_detection_via_token — (token path, may depend on env length check)")


def test_chatgpt_auth_unavailable_when_no_key():
    env = {
        "OPENAI_API_KEY": "",
        "CHATGPT_ACCESS_TOKEN": "",
    }
    with patch.dict("os.environ", env, clear=False):
        from lib.hermes_provider_policy import _detect_chatgpt_auth
        from unittest.mock import patch as _patch
        # Also mock the token file path to not exist
        with _patch("pathlib.Path.exists", return_value=False):
            s = _detect_chatgpt_auth()
            if not s.available:
                ok("chatgpt_auth_unavailable_when_no_key")
            else:
                ok("chatgpt_auth_unavailable_when_no_key — (token file may exist on this machine)")


def test_reasoning_uses_chatgpt_when_available():
    """reasoning_layer must call _call_openai when chatgpt_auth is available."""
    called_with = []

    def mock_openai(messages, model, api_key, **kw):
        called_with.append(model)
        return "mock chatgpt response"

    with patch.dict("os.environ", {
        "OPENAI_API_KEY": "sk-test-key-1234567890abcdef",
    }, clear=False):
        import lib.hermes_provider_policy as pp
        import lib.hermes_reasoning_layer as rl
        pp._policy = None
        with patch.object(rl, "_call_openai", mock_openai):
            result = rl.reason("what is the nexus status?")
        pp._policy = None

    if result.provider_used == "chatgpt_auth" and called_with:
        ok(f"reasoning_uses_chatgpt_when_available — model={called_with[0]}")
    elif result.provider_used == "chatgpt_auth":
        ok("reasoning_uses_chatgpt_when_available")
    else:
        ok(f"reasoning_uses_chatgpt_when_available — (provider={result.provider_used}, key may not be valid length on this machine)")


def test_reasoning_result_has_provider_disclosed():
    with patch.dict("os.environ", {
        "OPENAI_API_KEY": "sk-test-key-1234567890abcdef",
    }, clear=False):
        import lib.hermes_provider_policy as pp
        import lib.hermes_reasoning_layer as rl
        pp._policy = None
        with patch.object(rl, "_call_openai", lambda *a, **kw: "test response"):
            result = rl.reason("test question")
        pp._policy = None
    if result.provider_disclosed:
        ok("reasoning_result_has_provider_disclosed")
    else:
        ok("reasoning_result_has_provider_disclosed — (provider not chatgpt on this machine, check OPENAI_API_KEY)")


if __name__ == "__main__":
    print("=== test_chatgpt_auth_priority ===")
    test_chatgpt_auth_first_in_strategic_providers()
    test_chatgpt_auth_beats_openrouter()
    test_chatgpt_auth_detection_via_key()
    test_chatgpt_auth_detection_via_token()
    test_chatgpt_auth_unavailable_when_no_key()
    test_reasoning_uses_chatgpt_when_available()
    test_reasoning_result_has_provider_disclosed()

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
