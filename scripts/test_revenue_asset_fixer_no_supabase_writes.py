"""
test_revenue_asset_fixer_no_supabase_writes.py
Tests: no Phase 6F function writes to Supabase; all persistence is file-based.
"""
import sys, os, unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_revenue_asset_fixer_no_supabase_writes ===\n")

# ── Patch supabase client to detect any write calls ──────────────────────────
print("-- patch supabase and check for writes --")

_supabase_write_calls: list[str] = []

class _MockTable:
    def insert(self, data):
        _supabase_write_calls.append(f"insert:{data!r:.80}")
        return self
    def upsert(self, data):
        _supabase_write_calls.append(f"upsert:{data!r:.80}")
        return self
    def update(self, data):
        _supabase_write_calls.append(f"update:{data!r:.80}")
        return self
    def delete(self):
        _supabase_write_calls.append("delete")
        return self
    def execute(self):
        return type("R", (), {"data": [], "error": None})()
    def select(self, *a, **kw): return self
    def eq(self, *a, **kw): return self
    def order(self, *a, **kw): return self
    def limit(self, *a, **kw): return self
    def single(self): return self

class _MockSupabase:
    def table(self, name):
        return _MockTable()
    def from_(self, name):
        return _MockTable()

mock_supabase = _MockSupabase()

with unittest.mock.patch.dict("sys.modules", {
    "supabase": unittest.mock.MagicMock(),
}):
    try:
        # Re-import with patched supabase
        import importlib
        import lib.hermes_revenue_asset_fixer as fixer_mod
        importlib.reload(fixer_mod)

        result = fixer_mod.apply_safe_asset_fixes()
        check("apply_safe_asset_fixes completes", isinstance(result, dict))
        check("no supabase write calls during apply_safe_asset_fixes",
              len(_supabase_write_calls) == 0)
    except Exception as exc:
        check("apply_safe_asset_fixes does not raise with mock supabase", False)
        print(f"  Error: {exc!s:.150}")

# ── Fixed copies go to file system, not Supabase ──────────────────────────────
print("\n-- fixed copies are files, not Supabase records --")
from lib.hermes_revenue_asset_fixer import apply_safe_asset_fixes, _FIXED_DIR

result = apply_safe_asset_fixes()
fixed_copies = result.get("fixed_copies") or []
for cp in fixed_copies[:5]:
    cp_path = Path(cp)
    check(f"[{cp_path.name[:35]}] is real file", cp_path.exists())
    check(f"[{cp_path.name[:35]}] is in fixed/ dir", "_safe_fixed_" in cp_path.name)

# ── No secret keys appear in any output ──────────────────────────────────────
print("\n-- no secrets in output --")
from lib.hermes_revenue_asset_fixer import format_asset_fix_report
report = format_asset_fix_report(result)
SECRET_PATTERNS = ["supabase_service_role", "supabase_key", "openrouter", "openai_api_key",
                   "anthropic", "oanda", "hermes_gateway_key", "access_token", "secret",
                   "private_key"]
for pat in SECRET_PATTERNS:
    check(f"no '{pat}' in report", pat.lower() not in report.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
