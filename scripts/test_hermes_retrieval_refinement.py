#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import lib.hermes_supabase_first as hs
import lib.ai_employee_knowledge_router as kr
import lib.research_request_service as rrs


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True

    # Hermes transcript surfacing / NitroTrades recognition
    orig_hs_get = hs._supabase_get
    try:
        def fake_hs_get(table: str, params: dict):
            if table == "transcript_queue":
                return [
                    {
                        "title": "YouTube video research: NitroTrades session timing",
                        "source_url": "https://www.youtube.com/watch?v=nitro1234567",
                        "status": "ready",
                        "domain": "trading",
                        "metadata": {"channel_name": "nitrotrades"},
                    }
                ]
            if table == "knowledge_items":
                return [{"title": "ICT silver bullet overview", "domain": "trading", "quality_score": 85, "status": "approved"}]
            if table == "research_requests":
                return [{"topic": "ICT silver bullet strategy", "status": "needs_review", "priority": "urgent"}]
            if table == "strategies_catalog":
                return [{"name": "London Breakout", "asset_class": "FOREX", "risk_level": "medium", "ai_confidence": 71}]
            return []

        hs._supabase_get = fake_hs_get
        r1 = hs.nexus_knowledge_reply("What trading videos were recently ingested?") or ""
        ok &= check("recent trading ingest summary", "ingested" in r1.lower() or "video" in r1.lower())
        r2 = hs.nexus_knowledge_reply("Did Nexus process the NitroTrades email?") or ""
        ok &= check("nitrotrades recognition", "nitrotrades" in r2.lower() or "processed" in r2.lower())
        r3 = hs.nexus_knowledge_reply("What does Nexus know about ICT silver bullet concepts?") or ""
        ok &= check("partial synthesis mode", "partial" in r3.lower() or "under review" in r3.lower())
        r4 = hs.nexus_knowledge_reply("What knowledge is pending review?") or ""
        ok &= check("pending review retrieval", "pending" in r4.lower() or "proposed" in r4.lower())
    finally:
        hs._supabase_get = orig_hs_get

    # Confidence tuning / no unnecessary escalation
    orig_kr_get = kr._get
    try:
        def fake_kr_get(table: str, params: dict):
            if table == "knowledge_items":
                return []
            if table == "strategies_catalog":
                return []
            if table == "research_requests" and params.get("status") == "eq.completed":
                return []
            if table == "research_requests" and "submitted" in (params.get("status") or ""):
                return [{"topic": "ICT silver bullet", "status": "needs_review", "priority": "urgent"}]
            if table == "transcript_queue":
                return [{"title": "ICT silver bullet timing", "source_url": "https://youtube.com/watch?v=abc", "status": "needs_transcript", "cleaned_content": "session timing entries"}]
            return []

        kr._get = fake_kr_get
        result = kr.route_query("trading_analyst", "ICT silver bullet concepts", {})
        ok &= check("transcript contributes confidence", result.confidence > 0)
        ok &= check("no forced escalation with meaningful context", result.escalation_needed is False)
    finally:
        kr._get = orig_kr_get

    # Service layer should avoid ticket with supportive sources
    orig_route = rrs.handle_employee_query.__globals__["route_query"] if "route_query" in rrs.handle_employee_query.__globals__ else None
    # simpler: monkeypatch imported function path
    import lib.ai_employee_knowledge_router as router_mod
    original_route_query = router_mod.route_query
    original_create = rrs.create_research_ticket
    try:
        router_mod.route_query = lambda role, query, context: kr.KnowledgeResult(
            status="partial",
            confidence=35,
            sources=["transcript_queue"],
            summary="Transcript signals found",
            escalation_needed=True,
        )
        called = {"ticket": False}
        rrs.create_research_ticket = lambda **kwargs: called.update({"ticket": True}) or {"status": "created"}
        out = rrs.handle_employee_query("trading_analyst", "ict", "ict", {})
        ok &= check("service suppresses unnecessary escalation", called["ticket"] is False and out.get("ticket") is None)
    finally:
        router_mod.route_query = original_route_query
        rrs.create_research_ticket = original_create

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
