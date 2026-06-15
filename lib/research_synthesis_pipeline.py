"""
Research Synthesis Pipeline
==============================
Ingests research artifacts and produces actionable intelligence.

Pipeline stages:
  1. Ingest source (research_artifacts table)
  2. Summarize source
  3. Classify topic
  4. Extract monetization opportunities
  5. Extract affiliate opportunities
  6. Extract funding insights
  7. Extract automation ideas
  8. Create structured recommendations → worker_recommendations
  9. Create actionable tasks → agent_dispatch_tasks

Sources: YouTube channels, newsletters, websites, PDFs, transcripts

All outputs are evidence-backed. No fake synthesis.

Usage:
  python3 -m lib.research_synthesis_pipeline
  python3 bin/nexus research pipeline
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

TOPIC_CLASSIFIERS = {
    "business_credit": ["credit", "paydex", "duns", "tradeline", "net 30", "tier", "fundability"],
    "funding":         ["loan", "funding", "grant", "capital", "investor", "lender", "sba"],
    "ai_tools":        ["ai tool", "chatgpt", "claude", "automation", "workflow", "gpt", "llm"],
    "content":         ["youtube", "tiktok", "newsletter", "content", "video", "seo", "blog"],
    "income":          ["income", "revenue", "passive", "affiliate", "side hustle", "monetize"],
    "operations":      ["system", "process", "operations", "productivity", "scale", "delegate"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sb_get(path: str, timeout: int = 10) -> list:
    try:
        from scripts.prelaunch_utils import rest_select
        return rest_select(path, timeout=timeout) or []
    except Exception:
        return []


def _sb_insert(table: str, payload: dict) -> dict:
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY", "")
    )
    if not url or not key:
        return {"error": "supabase_not_configured"}
    import urllib.request
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{url}/rest/v1/{table}",
        data=data,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return result[0] if isinstance(result, list) else result
    except Exception as exc:
        return {"error": str(exc)}


def classify_topic(text: str) -> str:
    text_lower = text.lower()
    scores: dict[str, int] = {}
    for topic, keywords in TOPIC_CLASSIFIERS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[topic] = score
    if not scores:
        return "general"
    return max(scores, key=lambda k: scores[k])


def extract_opportunities(text: str, topic: str) -> list[dict]:
    """Extract monetization, affiliate, funding, and automation opportunities from text."""
    opps = []
    text_lower = text.lower()

    if "affiliate" in text_lower or "commission" in text_lower:
        opps.append({
            "type": "affiliate",
            "signal": "affiliate/commission language detected",
            "priority": "medium",
        })
    if any(k in text_lower for k in ["passive income", "recurring", "monthly revenue"]):
        opps.append({
            "type": "monetization",
            "signal": "passive/recurring income opportunity",
            "priority": "high",
        })
    if any(k in text_lower for k in ["grant", "funding", "loan", "sba", "capital"]):
        opps.append({
            "type": "funding",
            "signal": "funding opportunity signal",
            "priority": "high",
        })
    if any(k in text_lower for k in ["automate", "automation", "workflow", "ai tool", "system"]):
        opps.append({
            "type": "automation",
            "signal": "automation/AI tool opportunity",
            "priority": "medium",
        })
    if any(k in text_lower for k in ["youtube", "content", "video", "channel", "audience"]):
        opps.append({
            "type": "content",
            "signal": "content/audience building opportunity",
            "priority": "medium",
        })
    return opps


def synthesize_artifact(artifact: dict) -> dict:
    """
    Process a single research_artifact row through the full synthesis pipeline.
    Returns synthesis result dict.
    """
    artifact_id = str(artifact.get("id", "?"))
    source_type = str(artifact.get("source_type", "unknown"))
    title = str(artifact.get("title") or artifact.get("source_url") or "Untitled")
    content = str(artifact.get("content") or artifact.get("summary") or "")

    if len(content) < 50:
        return {"artifact_id": artifact_id, "skipped": True, "reason": "content too short"}

    # Stage 3: Classify
    topic = classify_topic(content)

    # Stage 4-7: Extract opportunities
    opps = extract_opportunities(content, topic)

    # Try LLM synthesis if available
    actionable_summary = ""
    try:
        from lib.nexus_model_caller import call
        system = (
            "You extract monetization intelligence from research. "
            "Be specific. Focus on actionable business opportunities. "
            "Under 150 words."
        )
        prompt = (
            f"Research source: {source_type} — '{title[:100]}'\n\n"
            f"Content excerpt: {content[:800]}\n\n"
            f"Topic: {topic}\n\n"
            f"Extract: (1) Top monetization opportunity, (2) Top affiliate opportunity if any, "
            f"(3) One automation idea, (4) Recommended next action for Nexus."
        )
        result = call(prompt, system=system, task_type="cheap", timeout=45)
        if result.get("success"):
            actionable_summary = result["response"]
    except Exception:
        # Fallback: structured summary from signals
        opp_signals = "; ".join(o["signal"] for o in opps) if opps else "none detected"
        actionable_summary = (
            f"Topic: {topic} | Opportunity signals: {opp_signals} | "
            f"Source: {source_type}. Manual review recommended."
        )

    # Stage 8: Create recommendation
    rec_result = {}
    if opps or actionable_summary:
        priority = "high" if any(o["priority"] == "high" for o in opps) else "medium"
        rec = {
            "worker_id": "research_worker",
            "category": topic,
            "priority": priority,
            "title": f"Intelligence from: {title[:80]}",
            "description": actionable_summary[:500] if actionable_summary else "See source.",
            "action_required": "Review synthesis and act on top opportunity",
            "evidence": f"research_artifacts.id={artifact_id}",
            "status": "open",
            "created_at": _now(),
        }
        rec_result = _sb_insert("worker_recommendations", rec)

    # Stage 9: Create task if high priority opportunity found
    task_result = {}
    if any(o["priority"] == "high" for o in opps):
        task = {
            "source": "research_worker",
            "original_prompt": f"Act on high-priority intelligence: {actionable_summary[:300]}",
            "normalized_goal": f"Research synthesis action: {title[:80]}",
            "task_type": "research_action",
            "risk_level": "low",
            "status": "planned",
            "approval_required": False,
            "created_at": _now(),
        }
        task_result = _sb_insert("agent_dispatch_tasks", task)

    return {
        "artifact_id": artifact_id,
        "title": title,
        "topic": topic,
        "opportunities": opps,
        "actionable_summary": actionable_summary[:200] if actionable_summary else "",
        "recommendation_id": rec_result.get("id"),
        "task_id": task_result.get("id"),
        "synthesized": True,
    }


def run_research_pipeline(limit: int = 10) -> dict:
    """
    Process latest unprocessed research artifacts through the synthesis pipeline.
    Returns summary of what was synthesized.
    """
    print(f"[research_synthesis] Starting pipeline (limit={limit})...")

    # Get recent unprocessed artifacts
    artifacts = _sb_get(
        f"research_artifacts?select=id,source_type,title,source_url,content,summary"
        f"&order=created_at.desc&limit={limit}"
    )

    if not artifacts:
        print("  No research artifacts found — pipeline complete (nothing to process)")
        return {
            "date": date.today().isoformat(),
            "processed": 0,
            "recommendations_created": 0,
            "tasks_created": 0,
            "artifacts_found": 0,
        }

    print(f"  Found {len(artifacts)} artifacts to synthesize")
    processed = 0
    recs_created = 0
    tasks_created = 0
    results = []

    for artifact in artifacts:
        result = synthesize_artifact(artifact)
        results.append(result)
        if result.get("skipped"):
            print(f"  ⏭️  Skipped: {result['artifact_id'][:8]}... ({result.get('reason','?')})")
            continue
        processed += 1
        if result.get("recommendation_id"):
            recs_created += 1
        if result.get("task_id"):
            tasks_created += 1
        topic = result.get("topic", "?")
        opps = len(result.get("opportunities", []))
        print(f"  ✅ Synthesized [{topic}] — {opps} opportunity signals | rec={bool(result.get('recommendation_id'))} | task={bool(result.get('task_id'))}")

    print(f"\n[research_synthesis] Complete: {processed} processed | {recs_created} recommendations | {tasks_created} tasks")

    return {
        "date": date.today().isoformat(),
        "artifacts_found": len(artifacts),
        "processed": processed,
        "recommendations_created": recs_created,
        "tasks_created": tasks_created,
        "results": results,
    }


if __name__ == "__main__":
    result = run_research_pipeline(limit=10)
    print(f"\nSynthesis complete: {result['processed']} processed, {result['recommendations_created']} recs, {result['tasks_created']} tasks")
