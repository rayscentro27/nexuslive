#!/usr/bin/env python3
"""
run_nexus_learn_by_doing_cycle.py — Nexus Learn-by-Doing: Credit Repair / Funding Readiness
============================================================================================
Nexus researches new credit repair / funding readiness strategies autonomously,
validates them, creates client education, content, and monetization artifacts.

Process:
  1. Search Supabase/Nexus memory for prior known strategies
  2. Search stored transcripts/notes
  3. Discover new strategies via LLM + knowledge synthesis
  4. Validate safety/compliance
  5. Create client education packet
  6. Create content pack
  7. Create monetization packet
  8. Log failures separately

Artifacts: docs/reports/learn_by_doing/credit_repair/<type>_<timestamp>.md

Usage:
    python scripts/run_nexus_learn_by_doing_cycle.py --domain credit_repair
    python scripts/run_nexus_learn_by_doing_cycle.py --domain business_funding
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_env = ROOT / ".env"
if _env.exists():
    import os
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip(); v = v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v

DOMAINS = ["credit_repair", "business_funding", "grant_readiness", "business_setup"]
OUTPUT_BASE = ROOT / "docs" / "reports" / "learn_by_doing"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _llm(prompt: str, system: str = "", tier: str = "reasoning", timeout: int = 120) -> str:
    try:
        from lib.content_generation_router import generate_content
        r = generate_content(prompt=prompt, system=system, tier=tier, timeout=timeout, max_tokens=4000)
        return r.get("response", "") if isinstance(r, dict) else str(r)
    except Exception as exc:
        return f"[LLM_ERROR: {exc}]"


def _parse_json(text: str, fallback=None):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        return fallback


def _save(domain: str, suffix: str, content: str) -> Path:
    path = OUTPUT_BASE / domain / f"{suffix}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _search_supabase_memory(domain: str) -> list[dict]:
    """Search Supabase knowledge_entries for prior domain knowledge."""
    try:
        import os, requests
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_KEY", "")
        if not url or not key:
            return []
        resp = requests.get(
            f"{url}/rest/v1/knowledge_entries?category=ilike.%25{domain.replace('_', '%20')}%25&limit=30",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=8,
        )
        return resp.json() if resp.ok and isinstance(resp.json(), list) else []
    except Exception:
        return []


def run_credit_repair_cycle(domain: str, ts: str) -> dict:
    run_id   = f"lbd_{ts}_{uuid.uuid4().hex[:6]}"
    artifacts: dict[str, str] = {}
    failures:  list[str] = []

    print(f"\n[learn] Domain: {domain}")

    # ── 1. Memory search ─────────────────────────────────────────────────────
    print("[learn] 1/8 Searching Supabase memory…")
    prior_knowledge = _search_supabase_memory(domain)
    mem_content = f"# Memory Search — {domain}\n*{_now()}*\n\nPrior entries found: {len(prior_knowledge)}\n\n"
    if prior_knowledge:
        for e in prior_knowledge[:10]:
            mem_content += f"- {e.get('title', e.get('topic', 'untitled'))[:80]}\n"
    else:
        mem_content += "No prior entries found in Supabase — relying on LLM knowledge.\n"
    mem_path = _save(domain, f"memory_search_{ts}", mem_content)
    artifacts["memory_search"] = str(mem_path)

    prior_summary = "\n".join(e.get("title", "") for e in prior_knowledge[:10]) or "None"

    # ── 2. Strategy discovery ─────────────────────────────────────────────────
    print("[learn] 2/8 Discovering new strategies…")
    discovery_prompt = f"""You are an expert in {domain.replace('_', ' ')}.

Prior strategies Nexus already knows: {prior_summary}

Find 5 new or underused strategies that:
1. Are not commonly known by small business owners
2. Are legally compliant and safe
3. Have high impact on {domain.replace('_', ' ')} outcomes
4. Can be taught as education content
5. Could lead to a monetizable offer

For each strategy:
{{
  "name": "...",
  "source": "evidence or expert consensus",
  "problem_solved": "...",
  "who_it_helps": "specific audience",
  "impact": "what changes for them",
  "implementation_difficulty": "easy | moderate | complex",
  "risk_or_compliance_concern": "...",
  "already_known": true/false,
  "conflicts_with_prior_knowledge": "yes/no + explanation",
  "client_safe": true/false,
  "client_education_angle": "title and key points",
  "monetization_angle": "product or service tied to this strategy"
}}

Return JSON: {{"strategies": [...]}}"""

    raw       = _llm(discovery_prompt, tier="reasoning")
    discovery = _parse_json(raw, {})
    strategies = discovery.get("strategies", []) if isinstance(discovery, dict) else []

    disc_md = f"# New Strategy Discovery — {domain}\n*{_now()}*\n\n"
    disc_md += f"Found {len(strategies)} strategies.\n\n"
    for s in strategies:
        disc_md += f"## {s.get('name', 'Unknown')}\n"
        disc_md += f"**Source:** {s.get('source', '')}\n"
        disc_md += f"**Problem:** {s.get('problem_solved', '')}\n"
        disc_md += f"**Who:** {s.get('who_it_helps', '')}\n"
        disc_md += f"**Impact:** {s.get('impact', '')}\n"
        disc_md += f"**Risk:** {s.get('risk_or_compliance_concern', '')}\n\n"

    disc_path = _save(domain, f"new_strategy_discovery_{ts}", disc_md)
    artifacts["discovery"] = str(disc_path)

    if not strategies:
        failures.append("strategy_discovery: no strategies returned — LLM may be unavailable")

    # ── 3. Validation ─────────────────────────────────────────────────────────
    print("[learn] 3/8 Validating strategies…")
    valid_strategies = [s for s in strategies if s.get("client_safe") and not s.get("conflicts_with_prior_knowledge", "").startswith("yes")]
    val_md = f"# Strategy Validation — {domain}\n*{_now()}*\n\n"
    val_md += f"**Validated (client-safe):** {len(valid_strategies)} / {len(strategies)}\n\n"
    for s in valid_strategies:
        val_md += f"- ✅ **{s.get('name', '')}** — {s.get('implementation_difficulty', '')} difficulty\n"
    val_path = _save(domain, f"strategy_validation_{ts}", val_md)
    artifacts["validation"] = str(val_path)

    best = valid_strategies[:3] if valid_strategies else strategies[:3]

    # ── 4. Client education packet ────────────────────────────────────────────
    print("[learn] 4/8 Creating client education packet…")
    edu_prompt = f"""Create a client education packet for small business owners on: {domain.replace('_', ' ')}

Strategies to teach:
{json.dumps([s.get('name', '') + ': ' + (s.get('client_education_angle', '') if isinstance(s.get('client_education_angle'), str) else str(s.get('client_education_angle', {}).get('angle', s.get('client_education_angle', '')))) for s in best], indent=2)}

Write:
1. Executive summary (what this means for them, plain language)
2. The 3 strategies explained simply (no jargon)
3. Common mistakes to avoid
4. Next steps they can take this week
5. How Nexus can help

Format: readable markdown, 600-900 words. No legal guarantees. Educational only."""

    edu_text = _llm(edu_prompt, tier="premium", timeout=90)
    if "[LLM_ERROR" in edu_text or len(edu_text) < 200:
        failures.append("client_education: LLM unavailable or returned short response")
        edu_text = f"# Client Education Packet — {domain}\n\n*Artifact: LLM generation failed — retry when provider is available.*\n"

    edu_path = _save(domain, f"client_education_packet_{ts}", edu_text)
    artifacts["client_education"] = str(edu_path)

    # ── 5. Content pack ──────────────────────────────────────────────────────
    print("[learn] 5/8 Creating content pack…")
    best_names = [s.get("name", "") for s in best]
    content_prompt = f"""Create a content pack for Nexus YouTube / newsletter on {domain.replace('_', ' ')}.

Top strategies to feature: {best_names}

Create:
1. YouTube video hook (3 options)
2. Newsletter subject line (3 options)
3. 300-word video script intro
4. Email body (300 words)
5. CTA for Nexus funding readiness audit or membership

Format: clear sections, conversion-optimized. Include urgency."""

    content_text = _llm(content_prompt, tier="premium", timeout=90)
    if "[LLM_ERROR" in content_text or len(content_text) < 200:
        failures.append("content_pack: LLM unavailable or returned short response")
        content_text = f"# Content Pack — {domain}\n\n*Artifact: LLM generation failed — retry when provider is available.*\n"

    content_path = _save(domain, f"content_pack_{ts}", content_text)
    artifacts["content_pack"] = str(content_path)

    # ── 6. Monetization packet ────────────────────────────────────────────────
    print("[learn] 6/8 Creating monetization packet…")
    mono_prompt = f"""Create a monetization packet for Nexus around {domain.replace('_', ' ')}.

Strategies: {best_names}

Design:
1. Primary offer (what Nexus sells related to these strategies)
2. Price point and model
3. Funnel: discovery → lead capture → offer → payment
4. Content → CTA → conversion path
5. Affiliate tie-ins (if any)
6. Compliance disclaimers required
7. Revenue estimate (conservative, moderate, optimistic per month)
8. What Ray must approve before launch

Format: business-ready, specific numbers, no vague language."""

    mono_text = _llm(mono_prompt, tier="reasoning", timeout=90)
    if "[LLM_ERROR" in mono_text or len(mono_text) < 200:
        failures.append("monetization_packet: LLM unavailable or returned short response")
        mono_text = f"# Monetization Packet — {domain}\n\n*Artifact: LLM generation failed — retry when provider is available.*\n"

    mono_path = _save(domain, f"monetization_packet_{ts}", mono_text)
    artifacts["monetization"] = str(mono_path)

    # ── 7/8. Success / failure reports ──────────────────────────────────────
    if failures:
        fail_content = f"# Failure Report — {domain}\n*{_now()}*\n\n"
        for f_item in failures:
            fail_content += f"- ❌ {f_item}\n"
        fail_path = _save(domain, f"failure_report_{ts}", fail_content)
        artifacts["failure_report"] = str(fail_path)

    success_count = sum(1 for v in artifacts.values() if v and Path(v).exists())
    success_content = f"# Success Report — {domain}\n*{_now()}*\n\n"
    success_content += f"**Run ID:** {run_id}\n"
    success_content += f"**Artifacts created:** {success_count}\n\n"
    for k, v in artifacts.items():
        success_content += f"- {k}: `{Path(v).name if v else 'MISSING'}`\n"
    success_path = _save(domain, f"success_report_{ts}", success_content)
    artifacts["success_report"] = str(success_path)

    print(f"[learn] Done. {success_count} artifacts created.")
    return {
        "run_id":    run_id,
        "domain":    domain,
        "created":   _now(),
        "strategies_found":   len(strategies),
        "strategies_valid":   len(valid_strategies),
        "artifacts": artifacts,
        "failures":  failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Nexus Learn-by-Doing Cycle")
    parser.add_argument("--domain", default="credit_repair", choices=DOMAINS,
                        help="Research domain")
    parser.add_argument("--json-out", default="", help="Optional: save result JSON")
    args = parser.parse_args()

    ts     = _ts()
    result = run_credit_repair_cycle(args.domain, ts)

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, default=str))
        print(f"[learn] Full result → {out}")

    print(f"\n[learn] Strategies found: {result['strategies_found']} | Valid: {result['strategies_valid']}")
    print(f"[learn] Artifacts:")
    for k, v in result["artifacts"].items():
        status = "✅" if v and Path(v).exists() else "❌"
        print(f"  {status} {k}: {Path(v).name if v else 'MISSING'}")


if __name__ == "__main__":
    main()
