"""
test_agent_handoff_builder.py
Test HermesAgentHandoffBuilder — build, persist, compliance contract embedding.
"""
import sys, shutil, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS; PASS += 1; print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL; FAIL += 1; print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


import lib.hermes_agent_handoff_builder as _mod

_tmp = tempfile.mkdtemp()
_orig_dir = _mod.HANDOFF_DIR
_mod.HANDOFF_DIR = Path(_tmp)
_builder = _mod.HermesAgentHandoffBuilder()


def test_build_returns_handoff():
    h = _builder.build(
        target_agent="claude_code",
        task_summary="Test task",
        task_detail="Do the test thing",
        acceptance_criteria=["artifact.md exists"],
    )
    if h and h.handoff_id:
        ok("build_returns_handoff — has handoff_id")
    else:
        fail("build_returns_handoff")


def test_handoff_id_format():
    h = _builder.build(
        target_agent="codex",
        task_summary="Format test",
        task_detail="detail",
        acceptance_criteria=["x"],
    )
    if h.handoff_id.startswith("hnd_"):
        ok("handoff_id_format — starts with hnd_")
    else:
        fail("handoff_id_format", h.handoff_id)


def test_prompt_contains_compliance_contract():
    h = _builder.build(
        target_agent="claude_code",
        task_summary="Compliance test",
        task_detail="detail",
        acceptance_criteria=["output.md exists"],
    )
    if "NO ARTIFACT = NO COMPLETION" in h.prompt:
        ok("prompt_contains_compliance_contract")
    else:
        fail("prompt_contains_compliance_contract", h.prompt[:200])


def test_prompt_contains_acceptance_criteria():
    h = _builder.build(
        target_agent="claude_code",
        task_summary="Criteria test",
        task_detail="detail",
        acceptance_criteria=["my_output.json exists", "registry updated"],
    )
    if "my_output.json exists" in h.prompt and "registry updated" in h.prompt:
        ok("prompt_contains_acceptance_criteria")
    else:
        fail("prompt_contains_acceptance_criteria", h.prompt[:300])


def test_prompt_blocks_live_trading():
    h = _builder.build_code_task_handoff(
        task_description="Build something for the platform",
        target_files=["lib/example.py"],
    )
    low = h.prompt.lower()
    if "do not enable live trading" in low or "live trading" in low:
        ok("prompt_blocks_live_trading")
    else:
        fail("prompt_blocks_live_trading")


def test_file_persisted_to_disk():
    h = _builder.build(
        target_agent="gemini",
        task_summary="Disk persist test",
        task_detail="detail",
        acceptance_criteria=["file.md exists"],
    )
    if h.file_path and Path(h.file_path).exists():
        ok("file_persisted_to_disk")
    else:
        fail("file_persisted_to_disk", h.file_path)


def test_log_jsonl_created():
    log = _mod.HANDOFF_DIR / "agent_handoff_log.jsonl"
    if log.exists():
        ok("log_jsonl_created — agent_handoff_log.jsonl exists")
    else:
        fail("log_jsonl_created")


def test_build_youtube_handoff():
    h = _builder.build_youtube_handoff(
        source_id="yt_abc123",
        url="https://youtube.com/watch?v=abc123",
        intake_id="intake_001",
    )
    if h.target_agent == "claude_code" and "youtube" in h.prompt.lower():
        ok("build_youtube_handoff — target=claude_code, prompt mentions youtube")
    else:
        fail("build_youtube_handoff", f"agent={h.target_agent}")


def test_build_github_handoff():
    h = _builder.build_github_handoff(
        repo_url="https://github.com/example/repo",
    )
    if "github.com/example/repo" in h.prompt:
        ok("build_github_handoff — URL in prompt")
    else:
        fail("build_github_handoff")


def test_telegram_summary_format():
    h = _builder.build(
        target_agent="claude_code",
        task_summary="Summary test",
        task_detail="detail",
        acceptance_criteria=["x"],
    )
    summary = h.telegram_summary()
    if "Agent Handoff Created" in summary and h.handoff_id in summary:
        ok("telegram_summary_format — contains header and handoff_id")
    else:
        fail("telegram_summary_format", summary[:200])


def test_pending_handoffs_returns_list():
    result = _builder.pending_handoffs()
    if isinstance(result, list):
        ok(f"pending_handoffs_returns_list — len={len(result)}")
    else:
        fail("pending_handoffs_returns_list")


def test_to_dict_has_required_keys():
    h = _builder.build(
        target_agent="claude_code",
        task_summary="Dict test",
        task_detail="detail",
        acceptance_criteria=["x"],
    )
    d = h.to_dict()
    required = {"handoff_id", "target_agent", "task_summary", "acceptance_criteria", "created_at"}
    missing = required - set(d.keys())
    if not missing:
        ok("to_dict_has_required_keys")
    else:
        fail("to_dict_has_required_keys", f"missing: {missing}")


if __name__ == "__main__":
    print("=== test_agent_handoff_builder ===")
    test_build_returns_handoff()
    test_handoff_id_format()
    test_prompt_contains_compliance_contract()
    test_prompt_contains_acceptance_criteria()
    test_prompt_blocks_live_trading()
    test_file_persisted_to_disk()
    test_log_jsonl_created()
    test_build_youtube_handoff()
    test_build_github_handoff()
    test_telegram_summary_format()
    test_pending_handoffs_returns_list()
    test_to_dict_has_required_keys()

    shutil.rmtree(_tmp, ignore_errors=True)
    _mod.HANDOFF_DIR = _orig_dir

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
