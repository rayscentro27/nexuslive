#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib import hermes_knowledge_brain as kb


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True

    sample = [
        {
            "id": "a1",
            "summary": "Funding recommendation: gather bank statements",
            "workflow_type": "funding_strategy",
            "status": "completed",
            "created_at": "2026-05-01T00:00:00+00:00",
            "updated_at": "2026-05-01T00:00:00+00:00",
        },
        {
            "id": "a2",
            "summary": "Funding recommendation: gather bank statements",
            "workflow_type": "funding_strategy",
            "status": "completed",
            "created_at": "2026-05-01T00:00:00+00:00",
            "updated_at": "2026-05-01T00:00:00+00:00",
        },
        {
            "id": "a3",
            "summary": "",
            "workflow_type": "",
            "event_type": "",
            "status": "completed",
            "created_at": "2026-05-01T00:00:00+00:00",
        },
    ]

    normalized = [kb._normalize(row, "workflow_outputs") for row in sample]
    deduped = kb._dedupe(normalized)
    non_empty = kb._non_empty(normalized)
    stale = kb._stale(normalized, days=1)

    ok &= check("dedupe suppresses duplicate summaries", len(deduped) == 2)
    ok &= check("non-empty filter removes blank summaries", len(non_empty) == 2)
    ok &= check("stale detection marks old rows", len(stale) >= 2)

    old_flag = os.environ.get("KNOWLEDGE_RETRIEVAL_ENABLED")
    os.environ["KNOWLEDGE_RETRIEVAL_ENABLED"] = "false"
    disabled_rows = kb.get_recent_knowledge("funding", limit=5)
    ok &= check("retrieval flag disables reads safely", disabled_rows == [])
    if old_flag is None:
        del os.environ["KNOWLEDGE_RETRIEVAL_ENABLED"]
    else:
        os.environ["KNOWLEDGE_RETRIEVAL_ENABLED"] = old_flag

    context_pack = kb.build_hermes_context_pack("operations")
    ok &= check("context pack shape stable", isinstance(context_pack.get("recent_knowledge"), list) and isinstance(context_pack.get("recent_recommendations"), list))
    ok &= check("context pack includes compact summary", isinstance(context_pack.get("compact_summary"), list))

    ranked = kb.rank_knowledge_results(normalized, category="funding")
    ok &= check("ranked funding knowledge returns ordered results", len(ranked) >= 2 and float(ranked[0].get("ranking_score") or 0.0) >= float(ranked[-1].get("ranking_score") or 0.0))
    reranked = kb.rank_knowledge_results(normalized, category="funding")
    ok &= check("ranking output deterministic", [r.get("workflow_id") for r in ranked] == [r.get("workflow_id") for r in reranked])

    credit_rows = [dict(r, category="credit") for r in normalized]
    credit_ranked = kb.rank_knowledge_results(credit_rows, category="credit")
    ok &= check("ranked credit knowledge returns ordered results", len(credit_ranked) >= 2 and float(credit_ranked[0].get("ranking_score") or 0.0) >= float(credit_ranked[-1].get("ranking_score") or 0.0))

    dup_suppressed = kb.suppress_duplicate_knowledge(normalized)
    ok &= check("duplicate suppression works", len(dup_suppressed) == 2)

    stale_detected = kb.detect_stale_knowledge(normalized, days=1)
    ok &= check("stale detection helper works", len(stale_detected) >= 2)

    source_pack = kb.build_source_aware_context_pack("funding", limit=4)
    ok &= check("source aware context pack shape", isinstance(source_pack.get("source_quality_summary"), dict) and isinstance(source_pack.get("top_ranked"), list))

    audit = kb.audit_knowledge_sources()
    ok &= check("audit includes discovered sources", isinstance(audit.get("knowledge_sources_discovered"), list))
    ok &= check("audit includes category counts", isinstance(audit.get("category_counts"), dict))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
