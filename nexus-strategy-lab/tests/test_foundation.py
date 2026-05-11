"""
Smoke tests for the strategy-lab foundation.
Run: cd nexus-strategy-lab && python -m tests.test_foundation
"""
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS = '  PASS'
FAIL = '  FAIL'
results = []


def check(name: str, fn):
    try:
        fn()
        logger.info(f"{PASS}  {name}")
        results.append((name, True, None))
    except Exception as e:
        logger.error(f"{FAIL}  {name}: {e}")
        results.append((name, False, str(e)))


# ── Tests ─────────────────────────────────────────────────────────────────────
def test_settings_load():
    from config import settings
    settings.validate()
    assert settings.SUPABASE_URL.startswith('https://'), "SUPABASE_URL must be https"
    assert len(settings.SUPABASE_KEY) > 10, "SUPABASE_KEY looks empty"


def test_supabase_ping():
    from db.supabase_client import ping
    assert ping(), "Supabase ping returned False"


def test_supabase_select():
    from db import supabase_client as db
    # strategy_sources is always present (created by Windows migration)
    rows = db.select('strategy_sources', 'limit=1')
    assert isinstance(rows, list), f"Expected list, got {type(rows)}"


def test_ai_client_import():
    from db import ai_client  # noqa: F401


def test_log_dir_exists():
    from config import settings
    assert settings.LOG_DIR.exists(), f"LOG_DIR not created: {settings.LOG_DIR}"


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n=== nexus-strategy-lab foundation smoke test ===\n")
    check('settings load + validate', test_settings_load)
    check('supabase ping',            test_supabase_ping)
    check('supabase select',          test_supabase_select)
    check('ai_client import',         test_ai_client_import)
    check('log dir created',          test_log_dir_exists)

    passed = sum(1 for _, ok, _ in results if ok)
    total  = len(results)
    print(f"\n{'='*48}")
    print(f"  {passed}/{total} passed")
    print(f"{'='*48}\n")
    sys.exit(0 if passed == total else 1)
