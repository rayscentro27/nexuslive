"""
github_trend_researcher.py — Nexus Weekly GitHub Trending Research Engine
==========================================================================
Finds trending GitHub repos that can improve existing Nexus operations.
NOT for adding shiny features — for improving existing processes.

Research categories:
  AI agent orchestration, local LLM tools, browser automation,
  research automation, content pipelines, workflow automation,
  Supabase/Postgres, observability, testing/evals, deployment,
  affiliate/funnel tools, data extraction, trading/backtesting,
  compliance/guardrail tools

Output artifacts:
  docs/reports/github_trends/github_trending_research_<ts>.md
  docs/reports/github_trends/github_trending_candidates_<ts>.json
  docs/reports/github_trends/github_trending_recommendations_<ts>.md

Usage:
    from lib.github_trend_researcher import GitHubTrendResearcher
    result = GitHubTrendResearcher().run()
"""
from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT       = Path(__file__).resolve().parent.parent
TREND_DIR  = ROOT / "docs" / "reports" / "github_trends"

NEXUS_IMPROVEMENT_CATEGORIES = [
    "ai_agent_orchestration",
    "local_llm_tools",
    "browser_automation",
    "research_automation",
    "content_generation_pipeline",
    "workflow_automation",
    "supabase_postgres_tooling",
    "observability_monitoring",
    "testing_evals",
    "deployment_helpers",
    "affiliate_funnel_tools",
    "data_extraction_transcripts",
    "trading_backtesting",
    "compliance_guardrails",
]

VALID_STATUSES = [
    "reject_shiny_object",     # trending but no clear Nexus improvement
    "reject",                  # not relevant at all
    "watch",                   # potential future relevance
    "test_in_sandbox",         # worth isolated testing
    "recommend_for_prompt",    # ready for Claude/Codex implementation prompt
    "high_priority_integration", # clear improvement to existing system
    "improves_existing_system",  # directly improves a named Nexus module
    "monetization_relevant",   # improves revenue/funnel capabilities
    "reliability_relevant",    # improves uptime/error recovery
]

NEXUS_IMPROVEMENT_QUESTIONS = [
    "Does this improve an existing Nexus process?",
    "Does it reduce failure or improve error recovery?",
    "Does it improve Hermes learning or memory?",
    "Does it improve monetization or funnel capabilities?",
    "Does it improve artifact generation quality?",
    "Does it improve Supabase/workflow memory?",
    "Does it improve content or funnel production?",
    "Does it improve reliability or self-recovery?",
    "Does it reduce cost?",
    "Is it worth sandbox testing?",
]


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


def _parse_json(text: str, fallback: Any = None) -> Any:
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


def _save(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _try_web_fetch(url: str, timeout: int = 15) -> str | None:
    """Try to fetch a URL. Returns None if unavailable."""
    try:
        import requests
        r = requests.get(url, timeout=timeout,
                         headers={"Accept": "application/vnd.github+json",
                                  "User-Agent": "Nexus-Trend-Researcher/1.0"})
        if r.ok:
            return r.text
        return None
    except Exception:
        return None


def _fetch_github_trending_api() -> tuple[list[dict], str | None]:
    """
    Attempt to fetch from GitHub's unofficial trending endpoint.
    Returns (repos_list, error_reason).
    """
    # GitHub has no official trending API — use search as proxy
    # Search for repos created in last 7 days with 50+ stars, sorted by stars
    week_ago = (datetime.now() - __import__("datetime").timedelta(days=7)).strftime("%Y-%m-%d")
    url = (
        "https://api.github.com/search/repositories"
        f"?q=created:>{week_ago}+stars:>50"
        "&sort=stars&order=desc&per_page=50"
    )
    token = os.getenv("GITHUB_TOKEN", "")
    try:
        import requests
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "Nexus-Trend-Researcher/1.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 403 and "rate limit" in r.text.lower():
            return [], "github_api_rate_limited — set GITHUB_TOKEN env var"
        if r.status_code == 401:
            return [], "github_api_unauthorized — check GITHUB_TOKEN"
        if not r.ok:
            return [], f"github_api_error_{r.status_code}"
        items = r.json().get("items", [])
        repos = [
            {
                "name":        f"{it.get('owner',{}).get('login','?')}/{it.get('name','?')}",
                "url":         it.get("html_url", ""),
                "stars":       it.get("stargazers_count", 0),
                "description": it.get("description", ""),
                "language":    it.get("language", ""),
                "topics":      it.get("topics", []),
                "created_at":  it.get("created_at", ""),
                "forks":       it.get("forks_count", 0),
            }
            for it in items
        ]
        return repos, None
    except ImportError:
        return [], "requests_not_installed"
    except Exception as exc:
        return [], str(exc)


class GitHubTrendResearcher:

    SYSTEM = (
        "You are the Nexus system improvement researcher. "
        "Your job is to evaluate GitHub repos for their potential to improve the EXISTING Nexus platform — "
        "NOT to add random features. "
        "Be harsh: reject anything that doesn't clearly improve an existing Nexus workflow. "
        "Output only valid JSON."
    )

    NEXUS_CONTEXT = """
Nexus is a Python monorepo with:
- lib/ : agents, content pipeline, trading adapter, Discord notifier, content router
- scripts/ : CLI runners for all workflows
- integrations/ : vibe-trading (backtesting), Supabase, OpenRouter
- Hermes : Telegram/CLI AI operator (Ollama LLM, local)
- Content Engine : 7-agent assembly line (research, hooks, script, edit, monetize, approve)
- Daily scout workers : affiliate, research, content, trading scouts
- Supabase : workflow_outputs, content drafts, knowledge base tables
- Discord : CEO, Content, Ops notification channels
- Deployment : Netlify (frontend), PM2 (background workers)
- LLM routing : OpenRouter (paid: deepseek-r1, deepseek-chat), Ollama (local/free)
"""

    def run(self) -> dict:
        """
        Run the weekly GitHub trend research cycle.
        Returns dict with repos, analysis, recommendations, artifact paths.
        """
        ts       = _ts()
        run_id   = f"trend_{ts}_{uuid.uuid4().hex[:6]}"
        result   = {
            "run_id":        run_id,
            "created":       _now(),
            "source_status": "unknown",
            "repos_fetched": 0,
            "candidates":    [],
            "top_10":        [],
            "top_3_worth_testing": [],
            "top_1_recommendation": {},
            "unavailability_reason": None,
            "artifacts":     {},
        }

        # ── 1. Fetch trending repos ───────────────────────────────────────────
        repos, error = _fetch_github_trending_api()
        if error:
            result["source_status"]        = "unavailable"
            result["unavailability_reason"] = error
            self._save_unavailable_artifact(ts, error, result)
            repos = self._llm_knowledge_repos()
            result["source_status"] = "llm_knowledge_only"
        else:
            result["source_status"] = "github_api"

        result["repos_fetched"] = len(repos)

        if not repos:
            return result

        # ── 2. LLM evaluation ────────────────────────────────────────────────
        # Cap at 15 repos, trim descriptions to avoid context overflow
        trimmed = []
        for r in repos[:15]:
            trimmed.append({
                "name":        r.get("name", ""),
                "url":         r.get("url", ""),
                "stars":       r.get("stars", 0),
                "description": (r.get("description") or "")[:120],
                "language":    r.get("language", ""),
                "topics":      r.get("topics", [])[:5],
            })
        repo_list = json.dumps(trimmed, indent=2)
        prompt = f"""You are evaluating GitHub repos for their potential to improve the Nexus platform.
You MUST reject repos that are just trending — only recommend ones that improve an EXISTING Nexus module.

{self.NEXUS_CONTEXT}

Evaluation questions to answer for each repo:
{chr(10).join(f'{i+1}. {q}' for i, q in enumerate(NEXUS_IMPROVEMENT_QUESTIONS))}

Here are recently trending repos:
{repo_list}

IMPORTANT: Be strict. If a repo doesn't clearly improve an existing Nexus process, use status "reject_shiny_object".
Only assign "improves_existing_system" or higher if you can name the SPECIFIC Nexus module and HOW it improves it.

Return JSON:
{{
  "evaluated": [
    {{
      "name": "owner/repo",
      "url": "...",
      "stars": 0,
      "category": "one of the research categories",
      "problem_solved": "...",
      "nexus_module_improved": "exact name of the Nexus module this improves, or 'none'",
      "how_it_improves_nexus": "specific description, or 'does not improve existing Nexus system'",
      "install_complexity": "simple | moderate | complex",
      "cost": "free | freemium | paid",
      "security_risk": "low | medium | high",
      "maintenance_risk": "low | medium | high",
      "nexus_improvement_score": 1-10,
      "status": "one of: reject_shiny_object | reject | watch | test_in_sandbox | improves_existing_system | monetization_relevant | reliability_relevant | high_priority_integration",
      "recommended_action": "one sentence on what to do",
      "implementation_prompt": "exact prompt Ray should give Claude/Codex if approved, or empty string"
    }}
  ],
  "top_3_worth_testing": ["owner/repo1", "owner/repo2", "owner/repo3"],
  "rejected_shiny_objects": ["repos rejected as shiny objects"],
  "top_1_recommendation": {{
    "name": "owner/repo",
    "nexus_module_improved": "specific module name",
    "nexus_process_improved": "specific description",
    "why": "...",
    "implementation_prompt": "..."
  }}
}}"""

        raw    = _llm(prompt, system=self.SYSTEM, tier="reasoning")
        parsed = _parse_json(raw, {})

        evaluated = parsed.get("evaluated", []) if isinstance(parsed, dict) else []
        if evaluated:
            evaluated.sort(key=lambda x: x.get("nexus_improvement_score", 0), reverse=True)

        result["candidates"]             = evaluated
        result["top_10"]                 = evaluated[:10]
        result["top_3_worth_testing"]    = parsed.get("top_3_worth_testing", []) if isinstance(parsed, dict) else []
        result["rejected_shiny_objects"] = parsed.get("rejected_shiny_objects", []) if isinstance(parsed, dict) else []
        result["top_1_recommendation"]   = parsed.get("top_1_recommendation", {}) if isinstance(parsed, dict) else {}

        # ── 3. Save artifacts ────────────────────────────────────────────────
        candidates_path = _save(
            TREND_DIR / f"github_trending_candidates_{ts}.json",
            json.dumps({"run_id": run_id, "repos": evaluated}, indent=2, default=str),
        )
        result["artifacts"]["candidates_json"] = str(candidates_path)

        research_md = self._render_research_md(result, repos)
        research_path = _save(TREND_DIR / f"github_trending_research_{ts}.md", research_md)
        result["artifacts"]["research_md"] = str(research_path)

        recs_md = self._render_recs_md(result)
        recs_path = _save(TREND_DIR / f"github_trending_recommendations_{ts}.md", recs_md)
        result["artifacts"]["recommendations_md"] = str(recs_path)

        # CEO filter artifact — shiny objects vs real improvements
        filter_md = self._render_ceo_filter(result, ts)
        filter_path = _save(TREND_DIR / f"github_trend_ceo_filter_{ts}.md", filter_md)
        result["artifacts"]["ceo_filter_md"] = str(filter_path)

        return result

    def _render_ceo_filter(self, result: dict, ts: str) -> str:
        evaluated      = result.get("candidates", [])
        shiny_objects  = [r for r in evaluated if r.get("status") == "reject_shiny_object"]
        real_improvements = [r for r in evaluated if r.get("status") in ("improves_existing_system", "high_priority_integration", "monetization_relevant", "reliability_relevant")]
        lines = [
            f"# GitHub Trend CEO Filter — {result['created'][:10]}",
            f"*Run ID: {result['run_id']} | Total evaluated: {len(evaluated)}*\n",
            f"## Real Nexus Improvements ({len(real_improvements)})\n",
        ]
        for r in real_improvements:
            lines.append(f"### ✅ [{r.get('name','?')}]({r.get('url','')}) — Score: {r.get('nexus_improvement_score',0)}/10")
            lines.append(f"**Module improved:** {r.get('nexus_module_improved', 'unspecified')}")
            lines.append(f"**How:** {r.get('how_it_improves_nexus', '')}")
            lines.append(f"**Status:** `{r.get('status','?')}`\n")
        lines.append(f"\n## Shiny Objects Rejected ({len(shiny_objects)})\n")
        for r in shiny_objects:
            lines.append(f"- ❌ `{r.get('name','?')}` — {r.get('how_it_improves_nexus', 'no clear Nexus improvement')}")
        return "\n".join(lines)

    def _llm_knowledge_repos(self) -> list[dict]:
        """When web access is unavailable, ask the LLM for repos it knows about."""
        prompt = f"""List the top 15 GitHub repositories (that you know about from training data)
that would be most valuable for improving this Nexus AI platform:

{self.NEXUS_CONTEXT}

Focus on repos from 2024-2025 that are well-known in their categories.
Return JSON array of repos with: name, url, stars (estimated), description, topics.
Format: [{{"name": "owner/repo", "url": "https://github.com/...", "stars": 0, "description": "...", "topics": [], "language": "", "created_at": ""}}]"""
        raw  = _llm(prompt, system=self.SYSTEM, tier="reasoning")
        data = _parse_json(raw, [])
        return data if isinstance(data, list) else []

    def _save_unavailable_artifact(self, ts: str, reason: str, context: dict) -> None:
        content = f"""# GitHub Trend Research — Source Unavailable

**Timestamp:** {_now()}
**Error:** {reason}

## What Happened
The GitHub API was unavailable or rate-limited during this research run.

## What's Needed to Fix This
- Set `GITHUB_TOKEN` environment variable (free GitHub personal access token)
  - Get one at: https://github.com/settings/tokens (no special permissions needed for public repos)
- Or wait for rate limit reset (usually 1 hour for unauthenticated requests)

## Current Rate Limit
- Unauthenticated: 10 requests/minute
- Authenticated: 5000 requests/hour

## What Happened Instead
The research engine fell back to LLM knowledge of known repos (training data).
Results marked with `source_status: llm_knowledge_only` may be outdated.

## Recommended Fix
Add to `.env`:
```
GITHUB_TOKEN=ghp_your_token_here
```
"""
        path = TREND_DIR / f"github_source_unavailable_{ts}.md"
        _save(path, content)
        context["artifacts"] = context.get("artifacts", {})
        context["artifacts"]["unavailable_artifact"] = str(path)

    def _render_research_md(self, result: dict, raw_repos: list) -> str:
        lines = [
            f"# GitHub Trending Research — {result['created'][:10]}",
            f"*Run ID: {result['run_id']} | Source: {result['source_status']} | Repos evaluated: {result['repos_fetched']}*\n",
        ]
        if result.get("unavailability_reason"):
            lines.append(f"> ⚠️ **Web source unavailable:** {result['unavailability_reason']}\n")
        lines.append("## Top 10 Candidates for Nexus\n")
        for i, r in enumerate(result.get("top_10", [])[:10], 1):
            status = r.get("status", "?")
            score  = r.get("nexus_improvement_score", 0)
            lines.append(f"### {i}. [{r.get('name','?')}]({r.get('url','')}) — Score: {score}/10 | `{status}`")
            lines.append(f"**Nexus relevance:** {r.get('nexus_relevance', '')}")
            lines.append(f"**Problem solved:** {r.get('problem_solved', '')}")
            lines.append(f"**Cost:** {r.get('cost','?')} | **Install:** {r.get('install_complexity','?')} | **Security risk:** {r.get('security_risk','?')}")
            lines.append(f"**Action:** {r.get('recommended_action', '')}\n")
        return "\n".join(lines)

    def _render_recs_md(self, result: dict) -> str:
        rec = result.get("top_1_recommendation", {})
        top3 = result.get("top_3_worth_testing", [])
        lines = [
            f"# GitHub Trend Recommendations — {result['created'][:10]}\n",
            f"## Top 3 Worth Testing",
        ]
        for r in top3:
            lines.append(f"- `{r}`")
        lines += [
            f"\n## #1 Recommended Integration",
            f"**Repo:** {rec.get('name', 'N/A')}",
            f"**Nexus process improved:** {rec.get('nexus_process_improved', '')}",
            f"**Why:** {rec.get('why', '')}",
            f"\n**Implementation prompt for Claude/Codex:**",
            f"```",
            rec.get("implementation_prompt", ""),
            f"```",
        ]
        return "\n".join(lines)
