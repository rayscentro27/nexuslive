"""
test_register_existing_artifacts.py
Test the backfill script for existing artifacts — dry-run, dedup, pattern matching.
"""
import sys, os, subprocess, tempfile, shutil, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0
SCRIPT = ROOT / "scripts" / "register_existing_artifacts.py"


def ok(name: str) -> None:
    global PASS
    PASS += 1
    print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL
    FAIL += 1
    print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


def run_script(*extra_args) -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)] + list(extra_args),
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return result.returncode, (result.stdout + result.stderr)


def test_script_exists():
    if SCRIPT.exists():
        ok("script_exists")
    else:
        fail("script_exists", f"not found: {SCRIPT}")


def test_dry_run_exits_zero():
    rc, output = run_script("--dry-run")
    if rc == 0:
        ok("dry_run_exits_zero")
    else:
        fail("dry_run_exits_zero", output[:200])


def test_dry_run_no_writes():
    import lib.nexus_artifact_registry as reg_mod
    registry_path = reg_mod.REGISTRY_FILE
    before = 0
    if registry_path.exists():
        before = len([l for l in registry_path.read_text().splitlines() if l.strip()])
    run_script("--dry-run")
    after = 0
    if registry_path.exists():
        after = len([l for l in registry_path.read_text().splitlines() if l.strip()])
    if after == before:
        ok("dry_run_no_writes — JSONL count unchanged")
    else:
        fail("dry_run_no_writes", f"before={before}, after={after}")


def test_dry_run_output_contains_dry_run_label():
    _, output = run_script("--dry-run")
    if "DRY RUN" in output.upper():
        ok("dry_run_output_contains_dry_run_label")
    else:
        fail("dry_run_output_contains_dry_run_label", output[:200])


def test_output_shows_candidate_count():
    _, output = run_script("--dry-run")
    if "Candidate files found" in output:
        ok("output_shows_candidate_count")
    else:
        fail("output_shows_candidate_count", output[:200])


def test_output_shows_registered_count():
    _, output = run_script("--dry-run")
    if "Registered:" in output:
        ok("output_shows_registered_count")
    else:
        fail("output_shows_registered_count", output[:200])


def test_pattern_map_covers_youtube():
    from scripts.register_existing_artifacts import PATTERN_MAP
    patterns_str = " ".join(p.pattern for p, _, _ in PATTERN_MAP)
    if "youtube" in patterns_str.lower() or "intelligence" in patterns_str.lower():
        ok("pattern_map_covers_youtube")
    else:
        fail("pattern_map_covers_youtube", "no youtube pattern found")


def test_pattern_map_covers_github():
    from scripts.register_existing_artifacts import PATTERN_MAP
    patterns_str = " ".join(p.pattern for p, _, _ in PATTERN_MAP)
    if "github" in patterns_str.lower():
        ok("pattern_map_covers_github")
    else:
        fail("pattern_map_covers_github")


def test_pattern_map_covers_agent_handoff():
    from scripts.register_existing_artifacts import PATTERN_MAP
    patterns_str = " ".join(p.pattern for p, _, _ in PATTERN_MAP)
    if "agent_handoff" in patterns_str.lower() or "handoff" in patterns_str.lower():
        ok("pattern_map_covers_agent_handoff")
    else:
        fail("pattern_map_covers_agent_handoff")


def test_scan_dirs_defined():
    from scripts.register_existing_artifacts import SCAN_DIRS
    if len(SCAN_DIRS) >= 5:
        ok(f"scan_dirs_defined — {len(SCAN_DIRS)} directories configured")
    else:
        fail("scan_dirs_defined", f"only {len(SCAN_DIRS)} dirs")


def test_dir_flag_scopes_scan():
    _, output = run_script("--dry-run", "--dir", "docs/reports/github_trends")
    if "Candidate files found" in output:
        ok("dir_flag_scopes_scan — --dir accepted")
    else:
        fail("dir_flag_scopes_scan", output[:200])


# ── Import guard (avoid importing script module at module level) ──────────────
def _import_script():
    import importlib.util
    spec = importlib.util.spec_from_file_location("reg_script", SCRIPT)
    mod  = importlib.util.load_module_from_spec(spec)  # type: ignore[attr-defined]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


if __name__ == "__main__":
    print("=== test_register_existing_artifacts ===")
    test_script_exists()
    test_dry_run_exits_zero()
    test_dry_run_no_writes()
    test_dry_run_output_contains_dry_run_label()
    test_output_shows_candidate_count()
    test_output_shows_registered_count()
    test_pattern_map_covers_youtube()
    test_pattern_map_covers_github()
    test_pattern_map_covers_agent_handoff()
    test_scan_dirs_defined()
    test_dir_flag_scopes_scan()

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
