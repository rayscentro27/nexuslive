#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.hermes_supabase_first import nexus_knowledge_reply
from lib.nexus_youtube_ops import (
    add_idea,
    generate_outline,
    generate_upload_metadata,
    ingest_channel_link,
    load_channel_config,
    list_ideas,
    load_content_queue,
    recommend_revenue_tieins,
)


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    cfg = load_channel_config()
    ok &= check("config loads", isinstance(cfg, dict) and bool(cfg.get("channel_name")))
    ok &= check("no secrets written in config", "api_key" not in str(cfg).lower() or "PLACEHOLDER_ONLY" in str(cfg))

    item = add_idea("business_funding", "How to get funding ready in 30 days")
    ok &= check("add idea works", bool(item.get("id")))
    ideas = list_ideas()
    ok &= check("list ideas works", len(ideas) >= 1)

    outline = generate_outline("Business Funding Readiness Checklist", "business_funding")
    ok &= check("outline generation stub", isinstance(outline.get("sections"), list) and len(outline.get("sections")) >= 3)

    meta = generate_upload_metadata("Top 5 AI Tools for Starting a Business", "ai_automation")
    ok &= check("metadata generation", bool(meta.get("description")) and meta.get("manual_upload_only") is True)

    queue = load_content_queue()
    ok &= check("content queue persistence", any(r.get("title") == "How to get funding ready in 30 days" for r in queue))

    tieins = recommend_revenue_tieins("business_funding")
    ok &= check("revenue tie-in suggestions", bool(tieins.get("lead_magnet")) and bool(tieins.get("affiliate_recommendation")))

    ingest = ingest_channel_link("https://www.youtube.com/@NexusFundingIntelligence")
    ok &= check("ingestion command creates safe job stub", ingest.get("mode") == "safe_stub" and ingest.get("max_videos") == 30)

    h1 = nexus_knowledge_reply("Add YouTube idea: Funding myths founders should avoid")
    h2 = nexus_knowledge_reply("Plan a YouTube video about business credit utilization")
    h3 = nexus_knowledge_reply("Generate YouTube description for Funding Readiness Guide")
    h4 = nexus_knowledge_reply("Ingest this playlist https://youtube.com/playlist?list=PL123")
    ok &= check("Telegram commands parse safely", all(isinstance(x, str) and len(x) > 0 for x in [h1, h2, h3, h4]))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
