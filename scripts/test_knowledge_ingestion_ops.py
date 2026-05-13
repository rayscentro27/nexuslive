#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.knowledge_ingestion_ops import (
    build_ingestion_snapshot,
    build_searchable_tags,
    normalize_category,
    normalize_source_url,
    owner_for_category,
    quality_score,
    source_metadata,
    trust_score,
)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True

    ok &= check("category normalization", normalize_category("business_setup") == "businessopps")
    ok &= check("category owner routing", owner_for_category("trading") == "trading_intelligence")
    ok &= check(
        "youtube url normalization",
        normalize_source_url("https://youtu.be/abc12345678") == "https://www.youtube.com/watch?v=abc12345678",
    )

    sm = source_metadata("https://www.youtube.com/@NitroTrades")
    ok &= check("source metadata channel detection", sm.get("channel_name") == "nitrotrades")

    tags = build_searchable_tags("trading", "youtube", "ICT silver bullet in NY session with liquidity sweep", "test")
    ok &= check("keyword expansion tags", "silver_bullet" in tags and "session_timing" in tags)

    score = quality_score("step by step risk process", "risk stop drawdown rules with entries", "youtube")
    scam = quality_score("guaranteed no risk", "100% win no risk", "youtube")
    ok &= check("quality scoring differentiates", score > scam)

    trust = trust_score("checklist with risk and stop loss", "calm educational breakdown")
    hype = trust_score("", "secret formula guaranteed millionaire")
    ok &= check("trust scoring hype penalty", trust > hype)

    snap = build_ingestion_snapshot(
        [
            {"source_url": "https://a", "source_type": "youtube", "status": "ready"},
            {"source_url": "https://b", "source_type": "website", "status": "failed"},
        ],
        [
            {"source_url": "https://a", "status": "proposed"},
            {"source_url": "https://c", "status": "approved"},
        ],
    )
    ok &= check("snapshot counts", snap.get("approved_count") == 1 and snap.get("ingestion_failure_count") == 1)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
