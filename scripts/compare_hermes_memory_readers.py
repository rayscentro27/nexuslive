"""
compare_hermes_memory_readers.py
Phase 4D — Compare current active memory reader vs hermes_memory_v2 preview.

READ-ONLY. No writes. No reader switch.
Outputs comparison to docs/reports/memory/.
"""
import json, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
MEMORY_DIR = ROOT / "docs" / "reports" / "memory"

# Load .env credentials if available (local dev env may not have them exported)
import os as _os
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            _os.environ.setdefault(_k.strip(), _v.strip())

_SUPABASE_WRITE_ATTEMPTED = False


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    assert _SUPABASE_WRITE_ATTEMPTED is False
    ts = _ts()
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    print("=== Hermes Memory Reader Comparison ===")
    print("Mode: READ-ONLY. No writes. No reader switch.")
    print()

    # ── Current reader summary ──────────────────────────────────────────────
    from lib.hermes_active_memory_reader import (
        load_active_memory,
        active_memory_available,
        CATEGORIES,
    )
    current_available = active_memory_available()
    current_mem = load_active_memory()

    current_populated = [c for c in CATEGORIES if current_mem.get(c)]
    current_sources = [
        "Current conversation context",
        "Latest content artifacts (artifact registry)",
        "Action queue",
        "Decision log",
        "Source intake records",
        "Active operating rules (hermes_executive_memory)",
    ]

    print("Current reader (hermes_active_memory_reader):")
    print(f"  Available: {current_available}")
    print(f"  Populated categories: {current_populated or ['(none)']}")
    for src in current_sources:
        print(f"  - {src}")
    print()

    # ── V2 reader summary ───────────────────────────────────────────────────
    from lib.hermes_memory_v2_reader import (
        build_v2_memory_context_pack,
        compare_v2_with_current_memory,
        explain_v2_reader_status,
    )
    pack = build_v2_memory_context_pack(limit=50)
    v2_available = pack.get("available", False)
    v2_total = pack.get("total", 0)
    v2_by_type = pack.get("by_type", {})

    print("Memory v2 preview (hermes_memory_v2_reader):")
    print(f"  Available: {v2_available}")
    print(f"  Total active/live_answer records: {v2_total}")
    if v2_by_type:
        for mt, cnt in sorted(v2_by_type.items()):
            print(f"  - {mt}: {cnt}")
    else:
        print("  (no records or credentials not set)")
    print()

    # ── Comparison ──────────────────────────────────────────────────────────
    cmp = compare_v2_with_current_memory()
    overlap = cmp.get("overlap", [])
    missing = cmp.get("missing_from_v2", [])
    extra = cmp.get("extra_in_v2", [])

    print("Overlap (v2 covers current reader capability):")
    if overlap:
        for o in overlap:
            print(f"  ✓ {o}")
    else:
        print("  (none)")
    print()

    print("Missing from v2 (Batch 2 targets):")
    if missing:
        for m in missing:
            print(f"  ✗ {m}")
    else:
        print("  (none)")
    print()

    if extra:
        print("Extra in v2 (not in current reader):")
        for e in extra:
            print(f"  + {e}")
        print()

    # ── Risks ───────────────────────────────────────────────────────────────
    risks = []
    if not v2_available:
        risks.append("v2 reader has no Supabase credentials — cannot compare live data")
    if v2_total < 10:
        risks.append(f"v2 has only {v2_total} records — insufficient for full reader switch")
    if missing:
        risks.append(f"v2 missing types: {missing} — Batch 2 needed before switch")
    if not current_available:
        risks.append("Current reader also has no live data — both readers limited")

    print("Risks:")
    if risks:
        for r in risks:
            print(f"  ⚠ {r}")
    else:
        print("  (none identified)")
    print()

    print("Recommendation:")
    print(f"  {cmp.get('recommendation', 'Keep v2 in preview until Batch 2 and comparison pass.')}")
    print()

    assert _SUPABASE_WRITE_ATTEMPTED is False

    # ── Write reports ───────────────────────────────────────────────────────
    result = {
        "phase":                        "4D",
        "generated_at":                 _now(),
        "mode":                         "read_only_comparison",
        "current_reader_available":     current_available,
        "current_populated_categories": current_populated,
        "current_sources":              current_sources,
        "v2_available":                 v2_available,
        "v2_total":                     v2_total,
        "v2_by_type":                   v2_by_type,
        "overlap":                      overlap,
        "missing_from_v2":              missing,
        "extra_in_v2":                  extra,
        "risks":                        risks,
        "recommendation":               cmp.get("recommendation", ""),
        "supabase_writes_attempted":    False,
        "live_reader_switched":         False,
    }

    json_path = MEMORY_DIR / f"phase4d_reader_comparison_{ts}.json"
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

    md_lines = [
        "# Phase 4D — Memory Reader Comparison",
        "",
        f"*Generated: {result['generated_at']}*",
        "",
        "**Read-only. No writes. No reader switch.**",
        "",
        "## Current Reader (hermes_active_memory_reader)",
        "",
        f"Available: {current_available}",
        "",
    ]
    for src in current_sources:
        md_lines.append(f"- {src}")
    md_lines += [
        "",
        "## Memory v2 Preview (hermes_memory_v2_reader)",
        "",
        f"Available: {v2_available}",
        f"Total active/live_answer records: {v2_total}",
        "",
    ]
    for mt, cnt in sorted(v2_by_type.items()):
        md_lines.append(f"- {mt}: {cnt}")
    md_lines += ["", "## Overlap", ""]
    for o in overlap:
        md_lines.append(f"- {o}")
    md_lines += ["", "## Missing from v2 (Batch 2 targets)", ""]
    for m in missing:
        md_lines.append(f"- {m}")
    md_lines += ["", "## Risks", ""]
    for r in risks:
        md_lines.append(f"- {r}")
    md_lines += ["", "## Recommendation", "", cmp.get("recommendation", ""), ""]
    md_path = MEMORY_DIR / f"phase4d_reader_comparison_{ts}.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"Reports written:")
    print(f"  {json_path.name}")
    print(f"  {md_path.name}")

    assert _SUPABASE_WRITE_ATTEMPTED is False
    return 0


if __name__ == "__main__":
    sys.exit(main())
