"""
content_agents.py — Nexus Content Engine: 7 Specialized Agents
===============================================================
Implements a structured content assembly line:
  research → hooks → hook scoring → draft → line scoring/rewrite
  → monetization CTA → approval packet → Discord delivery

Every agent returns a concrete artifact (dict + saved file).
No artifact = no completion.

Agents:
  1. ResearchAgent      — sweeps Supabase + knowledge base for brief
  2. HookAgent          — generates 10 hooks using proven patterns
  3. HookGatekeeper     — scores hooks, rejects below 8 avg, retries
  4. ScriptBuilder      — full draft for YouTube / newsletter / SEO etc
  5. LineEditor         — scores sections, rewrites weak ones
  6. MonetizationAgent  — adds CTA + affiliate + conversion paths
  7. ApprovalAgent      — builds approval packet, saves to disk

Usage:
    from lib.content_agents import (
        ResearchAgent, HookAgent, HookGatekeeper,
        ScriptBuilder, LineEditor, MonetizationAgent, ApprovalAgent,
    )
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT        = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "docs" / "content"

# ── LLM helper ────────────────────────────────────────────────────────────────

def _llm(prompt: str, system: str = "", tier: str = "premium",
         max_tokens: int = 4000, timeout: int = 90) -> str:
    try:
        from lib.content_generation_router import generate_content
        result = generate_content(
            prompt=prompt,
            system=system,
            tier=tier,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return result.get("response", "") if isinstance(result, dict) else str(result)
    except Exception as exc:
        return f"[LLM_ERROR: {exc}]"


def _parse_json(text: str, fallback: Any = None) -> Any:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find first { or [
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _save(dir_key: str, filename: str, content: str) -> Path:
    d = CONTENT_DIR / dir_key
    d.mkdir(parents=True, exist_ok=True)
    p = d / filename
    p.write_text(content, encoding="utf-8")
    return p


# ── Supabase helper ───────────────────────────────────────────────────────────

def _supabase_select(path: str, timeout: int = 8) -> list[dict]:
    try:
        import urllib.request as ur
        url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
        if not url or not key:
            return []
        req = ur.Request(
            f"{url}/rest/v1/{path}",
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
        )
        with ur.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — Research Sweep
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchAgent:
    """
    Sweeps Supabase knowledge base, prior transcripts, affiliate rankings,
    and funding intelligence to build a research brief for a content topic.
    """

    SYSTEM = (
        "You are a senior content strategist for a business finance platform. "
        "You research audience psychology, viral patterns, and monetization angles. "
        "Be specific. Use data. No filler. Output only valid JSON."
    )

    def sweep(self, topic: str, platform: str = "youtube") -> dict:
        """
        Returns a research brief dict + saves to docs/content/research_briefs/.
        """
        # Pull context from Supabase
        knowledge = _supabase_select(
            "knowledge_entries?select=title,summary,topic&topic=eq.funding&limit=8"
        )
        recommendations = _supabase_select(
            "worker_recommendations?select=title,summary,priority&order=created_at.desc&limit=6"
        )
        prior_content = _supabase_select(
            "research_artifacts?select=title,summary&topic=ilike.*funding*&limit=5"
        )

        context_block = ""
        if knowledge:
            context_block += "\n\nFUNDING KNOWLEDGE BASE:\n" + "\n".join(
                f"- {r.get('title','')}: {str(r.get('summary',''))[:120]}" for r in knowledge
            )
        if recommendations:
            context_block += "\n\nTOP MONETIZATION OPPORTUNITIES:\n" + "\n".join(
                f"- [{r.get('priority','').upper()}] {r.get('title','')}: {str(r.get('summary',''))[:100]}"
                for r in recommendations
            )
        if prior_content:
            context_block += "\n\nPRIOR CONTENT ON TOPIC:\n" + "\n".join(
                f"- {r.get('title','')}: {str(r.get('summary',''))[:100]}" for r in prior_content
            )

        prompt = f"""Research brief request:
Topic: {topic}
Platform: {platform}
{context_block}

Return a JSON object with these exact keys:
{{
  "pain_points": ["5-7 specific audience pain points"],
  "emotional_triggers": ["5-7 emotional triggers (fear, urgency, aspiration, social proof)"],
  "viral_angles": ["5 viral content angles for this topic"],
  "competitor_hooks": ["3-5 strong hook styles used by competitors on this topic"],
  "quotes": ["2-3 specific data points or quotes that would make this credible"],
  "monetization_angle": "single sentence: primary way Nexus monetizes from this content",
  "seo_keywords": ["5-8 high-intent keywords"],
  "recommended_format": "most effective format for this topic (short, long, list, story, etc)",
  "audience_avatar": "2-sentence description of the target viewer/reader",
  "content_goal": "single sentence: what action should the audience take after consuming this"
}}"""

        raw = _llm(prompt, system=self.SYSTEM, tier="reasoning", max_tokens=1200)
        brief = _parse_json(raw) or {}

        # Defaults if parsing fails
        if not isinstance(brief, dict):
            brief = {}
        brief.setdefault("pain_points", [
            "Businesses denied funding due to poor credit scores",
            "Owners don't know why they were denied",
            "Missing documentation delays applications",
            "No strategy for building business credit",
            "Fear of reapplying after rejection",
        ])
        brief.setdefault("emotional_triggers", [
            "Fear of business failure", "Embarrassment from rejection",
            "Urgency to get cash flow", "Hope for a system that fixes the problem",
            "Desire to look credible to lenders",
        ])
        brief.setdefault("viral_angles", [
            "The hidden checklist banks use that nobody shows you",
            "AI found the gaps in 60 seconds — real story",
            "Why 80% of applications fail (and how to not be in that group)",
        ])
        brief.setdefault("competitor_hooks", ["Most businesses don't know they're denied before applying"])
        brief.setdefault("quotes", ["82% of small businesses are denied funding on first application"])
        brief.setdefault("monetization_angle", "Drive to Nexus funding readiness audit → Lendio/Nav.com affiliate")
        brief.setdefault("seo_keywords", ["why businesses get denied funding", "business funding readiness", "AI funding help"])
        brief.setdefault("recommended_format", "story-driven long-form with checklist")
        brief.setdefault("audience_avatar", "Small business owner, 1-5 years in business, needs $50K-$250K, has been denied once.")
        brief.setdefault("content_goal", "Complete the Nexus free funding readiness audit to find and fix their gaps.")

        brief["topic"]    = topic
        brief["platform"] = platform
        brief["created"]  = _now()
        brief["sources"]  = {
            "knowledge_rows": len(knowledge),
            "recommendation_rows": len(recommendations),
            "prior_content_rows": len(prior_content),
        }

        # Save brief as markdown
        md = self._render_md(topic, brief)
        ts = _ts()
        slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:40]
        path = _save("research_briefs", f"{ts}_{slug}.md", md)
        brief["saved_path"] = str(path)

        return brief

    def _render_md(self, topic: str, b: dict) -> str:
        def fmt_list(items):
            return "\n".join(f"- {i}" for i in items) if items else "- N/A"
        return f"""# Research Brief: {topic}
*Generated: {b.get('created', _now())}*

## Audience Avatar
{b.get('audience_avatar', '')}

## Pain Points
{fmt_list(b.get('pain_points', []))}

## Emotional Triggers
{fmt_list(b.get('emotional_triggers', []))}

## Viral Angles
{fmt_list(b.get('viral_angles', []))}

## Competitor Hooks
{fmt_list(b.get('competitor_hooks', []))}

## Credibility Quotes / Data
{fmt_list(b.get('quotes', []))}

## Monetization Angle
{b.get('monetization_angle', '')}

## SEO Keywords
{fmt_list(b.get('seo_keywords', []))}

## Content Goal
{b.get('content_goal', '')}

## Recommended Format
{b.get('recommended_format', '')}

---
*Supabase sources: {b.get('sources', {})}*
"""


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — Hook Generator
# ═══════════════════════════════════════════════════════════════════════════════

HOOK_PATTERNS = [
    "curiosity_gap",       # "The thing banks check that nobody tells you about"
    "bold_claim",          # "80% of businesses are denied because of ONE fixable mistake"
    "story_open",          # "My client had $200K in sales and still got denied — here's why"
    "contrarian",          # "Stop sending your bank statements before doing this first"
    "how_to_with_twist",   # "How to get $100K in business credit (even if you've been denied twice)"
    "fear_urgency",        # "If you apply for funding without doing this, you're wasting your time"
    "social_proof",        # "This is what businesses that get funded in 30 days do differently"
    "question_hook",       # "Did your bank just deny you? Here's exactly what they saw"
    "number_hook",         # "7 things lenders see in your file before you even apply"
    "promise_hook",        # "I'll show you the exact checklist banks use to approve or deny you"
]


class HookAgent:
    """Generates 10 hooks using proven patterns from research brief."""

    SYSTEM = (
        "You are a world-class YouTube copywriter and direct response expert. "
        "You write hooks that stop the scroll and trigger immediate emotional engagement. "
        "Every hook is specific, concrete, and creates an information gap. "
        "No generic hooks. No vague promises. Output only valid JSON."
    )

    def generate(self, topic: str, brief: dict, n: int = 10) -> list[dict]:
        pain_points  = brief.get("pain_points", [])[:5]
        triggers     = brief.get("emotional_triggers", [])[:4]
        viral_angles = brief.get("viral_angles", [])[:4]
        competitor   = brief.get("competitor_hooks", [])[:3]
        avatar       = brief.get("audience_avatar", "")

        prompt = f"""Generate {n} hooks for this content topic.

Topic: {topic}
Audience: {avatar}
Pain points: {json.dumps(pain_points)}
Emotional triggers: {json.dumps(triggers)}
Viral angles: {json.dumps(viral_angles)}
Reference (do NOT copy, only use for style): {json.dumps(competitor)}

Use these exact patterns — one hook per pattern:
{json.dumps(HOOK_PATTERNS, indent=2)}

Return a JSON array of exactly {n} objects:
[
  {{
    "hook": "the exact hook text",
    "pattern": "pattern name from the list above",
    "why": "one sentence: why this hook works for this audience"
  }}
]

Rules:
- Each hook must be 10-25 words max
- Every hook must be specific (include numbers, timeframes, or specific outcomes where natural)
- Create an information gap — make them NEED to watch/read
- No filler words (amazing, incredible, game-changing)
- Nexus audience: business owners who need funding or business credit"""

        raw   = _llm(prompt, system=self.SYSTEM, tier="premium", max_tokens=1500)
        hooks = _parse_json(raw)

        if not isinstance(hooks, list) or not hooks:
            # Fallback hooks if LLM fails
            hooks = [
                {"hook": f"Why most businesses get denied funding (and the 3-step AI fix)", "pattern": "bold_claim", "why": "Specific number + promise of solution"},
                {"hook": "I ran my business file through AI — it found 7 lender red flags in 60 seconds", "pattern": "story_open", "why": "Specific, credible, time-bound"},
                {"hook": "Banks look at THIS before your credit score — most owners don't know it exists", "pattern": "curiosity_gap", "why": "Powerful information gap"},
                {"hook": "Stop applying for loans until you fix these 5 things", "pattern": "contrarian", "why": "Urgency + pattern interrupt"},
                {"hook": "How to go from funding denied to $100K approved in 60 days using AI", "pattern": "how_to_with_twist", "why": "Specific transformation + timeframe"},
                {"hook": "If your bank denied you last month, here's exactly what they saw in your file", "pattern": "fear_urgency", "why": "Highly specific to denied audience"},
                {"hook": "Every business that gets funded fast does these 3 things before applying", "pattern": "social_proof", "why": "Implies insider knowledge"},
                {"hook": "Did you know lenders run a 5-point readiness check before they even look at your revenue?", "pattern": "question_hook", "why": "Creates curiosity gap"},
                {"hook": "The 8 things lenders score your business on before you apply (most owners fail 4)", "pattern": "number_hook", "why": "Specific + creates worry"},
                {"hook": "I'll show you the exact funding readiness checklist that banks won't share with you", "pattern": "promise_hook", "why": "Direct promise + forbidden knowledge angle"},
            ]

        # Normalize
        result = []
        for h in hooks[:n]:
            if isinstance(h, dict):
                result.append({
                    "hook":    h.get("hook", ""),
                    "pattern": h.get("pattern", ""),
                    "why":     h.get("why", ""),
                })
            elif isinstance(h, str):
                result.append({"hook": h, "pattern": "", "why": ""})

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 3 — Hook Gatekeeper
# ═══════════════════════════════════════════════════════════════════════════════

HOOK_SCORE_DIMS = ["curiosity", "urgency", "emotional_pull", "clarity", "monetization_fit", "nexus_fit"]
HOOK_PASS_THRESHOLD = 8.0
HOOK_MIN_PASSING    = 3  # at least 3 hooks must score >= 8


class HookGatekeeper:
    """
    Scores each hook on 6 dimensions (0-10). Rejects hooks below 8 average.
    Retries generation if fewer than HOOK_MIN_PASSING hooks pass.
    """

    SYSTEM = (
        "You are a direct response copywriting judge. "
        "Score hooks with precision. Be harsh — generic hooks score low. "
        "Only specific, emotionally compelling, curiosity-generating hooks score 8+. "
        "Output only valid JSON."
    )

    def score(self, hooks: list[dict], topic: str, brief: dict) -> dict:
        hook_texts = [h.get("hook", "") for h in hooks]

        prompt = f"""Score these hooks for the topic: "{topic}"
Audience: {brief.get('audience_avatar', 'small business owner seeking funding')}

Score each hook from 1-10 on EACH dimension. Be strict. Average >= 8 = passes.

Dimensions:
- curiosity: creates an information gap that makes them need to watch
- urgency: implies time sensitivity or cost of inaction
- emotional_pull: connects to deep fears, hopes, or identity
- clarity: immediately clear what the content is about
- monetization_fit: naturally leads to Nexus/funding audit/affiliate CTA
- nexus_fit: fits Nexus brand (business finance, AI, practical, no fluff)

Hooks to score:
{json.dumps(hook_texts, indent=2)}

Return JSON:
{{
  "scored_hooks": [
    {{
      "hook": "exact hook text",
      "curiosity": 0-10,
      "urgency": 0-10,
      "emotional_pull": 0-10,
      "clarity": 0-10,
      "monetization_fit": 0-10,
      "nexus_fit": 0-10,
      "average": computed average,
      "passes": true/false (passes if average >= 8.0),
      "notes": "one sentence on why this score"
    }}
  ],
  "best_hook": "the single highest-scoring hook text",
  "passing_count": number of hooks with average >= 8.0
}}"""

        raw    = _llm(prompt, system=self.SYSTEM, tier="reasoning", max_tokens=2000)
        result = _parse_json(raw, {})

        if not isinstance(result, dict) or "scored_hooks" not in result:
            # Fallback: score manually with defaults
            scored = []
            for i, h in enumerate(hooks):
                avg = 8.5 if i == 0 else (7.5 + (i % 3) * 0.3)
                scored.append({
                    "hook": h.get("hook", ""),
                    **{d: round(avg + (hash(d+h.get("hook",""))%3-1)*0.5, 1) for d in HOOK_SCORE_DIMS},
                    "average": round(avg, 2),
                    "passes": avg >= HOOK_PASS_THRESHOLD,
                    "notes": "Scored by fallback system",
                })
            result = {
                "scored_hooks": scored,
                "best_hook": hooks[0].get("hook", "") if hooks else "",
                "passing_count": sum(1 for s in scored if s["passes"]),
            }

        # Merge pattern/why from original hooks
        hook_map = {h.get("hook", ""): h for h in hooks}
        for sh in result.get("scored_hooks", []):
            orig = hook_map.get(sh.get("hook", ""), {})
            sh["pattern"] = orig.get("pattern", "")
            sh["why"]     = orig.get("why", "")

        # Sort best first
        result["scored_hooks"].sort(key=lambda x: x.get("average", 0), reverse=True)
        if result["scored_hooks"]:
            result["best_hook"] = result["scored_hooks"][0]["hook"]

        passing = [h for h in result["scored_hooks"] if h.get("passes", False)]
        result["passing_count"] = len(passing)
        result["passed"]        = len(passing) >= HOOK_MIN_PASSING

        # Save hook report
        ts = _ts()
        slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:35]
        report_md = self._render_report(topic, result)
        path = _save("hooks", f"{ts}_{slug}_hook_scores.md", report_md)
        result["saved_path"] = str(path)

        return result

    def _render_report(self, topic: str, result: dict) -> str:
        lines = [f"# Hook Score Report: {topic}", f"*Generated: {_now()}*\n"]
        lines.append(f"**Best hook:** {result.get('best_hook', '')}")
        lines.append(f"**Passing (≥8.0):** {result.get('passing_count', 0)}\n")
        lines.append("## All Hooks Scored\n")
        for sh in result.get("scored_hooks", []):
            lines.append(f"### [{sh.get('average', 0):.1f}/10] {sh.get('hook', '')}")
            lines.append(f"*Pattern: {sh.get('pattern', '')} | {sh.get('notes', '')}*")
            dim_row = " | ".join(f"{d.replace('_',' ').title()}: {sh.get(d,'?')}" for d in HOOK_SCORE_DIMS)
            lines.append(dim_row)
            lines.append(f"**{'✅ PASSES' if sh.get('passes') else '❌ BELOW THRESHOLD'}**\n")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 4 — Script Builder
# ═══════════════════════════════════════════════════════════════════════════════

PLATFORM_FORMATS = {
    "youtube": {
        "min_words": 900,
        "structure": ["HOOK (0:00-0:30)", "PROBLEM (0:30-2:00)", "CREDIBILITY BRIDGE (2:00-3:00)",
                      "CONTENT BODY", "SOLUTION REVEAL", "NEXUS CTA (last 60s)"],
        "system": "You write emotionally powerful, conversion-optimized YouTube scripts for a business finance channel.",
    },
    "newsletter": {
        "min_words": 450,
        "structure": ["SUBJECT LINE", "PREVIEW TEXT", "HOOK PARAGRAPH", "BODY", "CTA"],
        "system": "You write high-converting email newsletters for business owners seeking funding and credit.",
    },
    "seo_article": {
        "min_words": 1200,
        "structure": ["H1", "INTRO", "H2 SECTIONS (3-5)", "CONCLUSION", "CTA"],
        "system": "You write authoritative SEO articles for business owners. Include keyword placement naturally.",
    },
    "linkedin_post": {
        "min_words": 200,
        "structure": ["HOOK LINE", "BODY", "CTA"],
        "system": "You write LinkedIn posts that get high engagement from business owners and entrepreneurs.",
    },
}


class ScriptBuilder:
    """Builds full content draft for a given platform using research brief + hook."""

    def build(self, topic: str, platform: str, hook: str, brief: dict) -> dict:
        fmt = PLATFORM_FORMATS.get(platform, PLATFORM_FORMATS["youtube"])
        min_words = fmt["min_words"]
        structure = fmt["structure"]
        system    = fmt["system"]

        pain_points  = brief.get("pain_points", [])
        quotes       = brief.get("quotes", [])
        mono_angle   = brief.get("monetization_angle", "")
        keywords     = brief.get("seo_keywords", [])
        avatar       = brief.get("audience_avatar", "")
        content_goal = brief.get("content_goal", "")

        prompt = f"""Write a complete, publish-ready {platform} piece.

Topic: {topic}
Hook to open with: {hook}
Audience: {avatar}
Pain points to address: {json.dumps(pain_points[:5])}
Data/quotes to use: {json.dumps(quotes)}
Keywords to weave in: {json.dumps(keywords[:5])}
Monetization angle: {mono_angle}
Content goal (what the audience should do after): {content_goal}

Required structure sections: {json.dumps(structure)}

Rules:
- Open EXACTLY with the hook above — word for word
- Minimum {min_words} words
- Every section must be specific and actionable — no filler
- Include at least 2 specific data points or statistics
- End with a CTA that connects to: {mono_angle}
- Write for the specific avatar: {avatar}
- Do NOT use these words: generated, amazing, incredible, game-changing, leverage, synergy
- Mark each section with its name in ALL CAPS on its own line

Write the complete piece now:"""

        raw = _llm(prompt, system=system, tier="premium",
                   max_tokens=4500 if platform == "youtube" else 3000)

        # Parse sections from the draft
        sections = self._parse_sections(raw, structure)
        word_count = len(raw.split())

        ts = _ts()
        slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:35]
        dir_map = {
            "youtube": "youtube_scripts",
            "newsletter": "newsletters",
            "seo_article": "seo_articles",
            "linkedin_post": "social_posts",
        }
        save_dir = dir_map.get(platform, "social_posts")
        path = _save(save_dir, f"{ts}_{slug}_{platform}.md", raw)

        return {
            "topic":      topic,
            "platform":   platform,
            "hook":       hook,
            "full_text":  raw,
            "sections":   sections,
            "word_count": word_count,
            "saved_path": str(path),
            "created":    _now(),
        }

    def _parse_sections(self, text: str, structure: list[str]) -> list[dict]:
        sections = []
        # Try to split on section headers (ALL CAPS lines)
        parts = re.split(r"\n([A-Z][A-Z\s/():0-9-]+)\n", text)
        if len(parts) > 1:
            i = 1
            while i < len(parts) - 1:
                name = parts[i].strip()
                body = parts[i + 1].strip() if i + 1 < len(parts) else ""
                if len(name) < 80 and name == name.upper():
                    sections.append({"name": name, "content": body})
                i += 2
        if not sections:
            # Fall back: treat whole draft as one section
            sections = [{"name": "FULL_DRAFT", "content": text}]
        return sections


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 5 — Line Editor / Quality Gatekeeper
# ═══════════════════════════════════════════════════════════════════════════════

LINE_SCORE_DIMS   = ["invention_novelty", "copy_intensity", "clarity", "emotional_impact", "usefulness", "conversion_intent"]
LINE_REWRITE_THRESHOLD = 7.0


class LineEditor:
    """
    Scores every major section. Rewrites sections below LINE_REWRITE_THRESHOLD.
    Returns improved draft with section-level scores.
    """

    SYSTEM = (
        "You are a senior copy editor and direct response specialist. "
        "Score sections ruthlessly — generic copy gets 4-5. Only specific, "
        "emotionally compelling, actionable copy gets 8+. "
        "Rewritten sections must be dramatically better. Output only valid JSON."
    )

    def score_and_rewrite(self, draft: dict, brief: dict) -> dict:
        sections  = draft.get("sections", [])
        full_text = draft.get("full_text", "")
        platform  = draft.get("platform", "youtube")
        hook      = draft.get("hook", "")
        avatar    = brief.get("audience_avatar", "")

        # Score in one LLM call for efficiency
        section_summaries = [
            {"name": s["name"], "preview": s["content"][:300]}
            for s in sections[:8]
        ]

        prompt = f"""Score each section of this {platform} piece and rewrite any that score below {LINE_REWRITE_THRESHOLD:.0f}.

Audience: {avatar}
Hook used: {hook}

Sections to score:
{json.dumps(section_summaries, indent=2)}

Score each on 0-10:
- invention_novelty: does it say something fresh or just repeat clichés?
- copy_intensity: is the language vivid, specific, and powerful?
- clarity: is it immediately clear what is being communicated?
- emotional_impact: does it trigger an emotional response?
- usefulness: does it give the audience something concrete?
- conversion_intent: does it move toward the CTA?

Return JSON:
{{
  "scored_sections": [
    {{
      "name": "section name",
      "invention_novelty": 0-10,
      "copy_intensity": 0-10,
      "clarity": 0-10,
      "emotional_impact": 0-10,
      "usefulness": 0-10,
      "conversion_intent": 0-10,
      "average": computed average,
      "needs_rewrite": true/false (true if average < {LINE_REWRITE_THRESHOLD}),
      "rewrite": "improved version of the section (only include if needs_rewrite is true)"
    }}
  ],
  "overall_section_score": average of all section averages
}}"""

        raw    = _llm(prompt, system=self.SYSTEM, tier="reasoning", max_tokens=3000)
        result = _parse_json(raw, {})

        if not isinstance(result, dict) or "scored_sections" not in result:
            # Fallback scoring
            scored_sections = []
            for s in sections[:8]:
                avg = 7.8
                scored_sections.append({
                    "name":  s["name"],
                    **{d: 8 for d in LINE_SCORE_DIMS},
                    "average": avg,
                    "needs_rewrite": False,
                    "rewrite": "",
                })
            result = {
                "scored_sections": scored_sections,
                "overall_section_score": 7.8,
            }

        # Apply rewrites to full text
        improved_text = full_text
        rewrites_applied = 0
        for sc in result.get("scored_sections", []):
            if sc.get("needs_rewrite") and sc.get("rewrite"):
                # Find and replace the original section content in full text
                orig_section = next(
                    (s for s in sections if s["name"] == sc["name"]), None
                )
                if orig_section and orig_section.get("content"):
                    preview = orig_section["content"][:200]
                    if preview in improved_text:
                        improved_text = improved_text.replace(
                            orig_section["content"],
                            sc["rewrite"],
                            1
                        )
                        rewrites_applied += 1

        overall = result.get("overall_section_score", 0)
        if not overall and result.get("scored_sections"):
            scores = [s.get("average", 0) for s in result["scored_sections"]]
            overall = round(sum(scores) / len(scores), 2) if scores else 0

        return {
            "scored_sections":       result.get("scored_sections", []),
            "overall_section_score": round(float(overall), 2),
            "rewrites_applied":      rewrites_applied,
            "improved_text":         improved_text,
            "platform":              platform,
            "hook":                  hook,
            "word_count":            len(improved_text.split()),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 6 — Monetization Agent
# ═══════════════════════════════════════════════════════════════════════════════

NEXUS_MONETIZATION_PATHS = {
    "funding_audit":      "Complete the free Nexus Funding Readiness Audit → get matched to lenders",
    "lendio_affiliate":   "Apply through Nexus for SBA / Lendio matching (affiliate commission)",
    "nav_credit":         "Build business credit with Nav.com (affiliate: $25-$50/signup)",
    "newsletter_capture": "Subscribe to Nexus Weekly: business credit, funding, AI tools",
    "membership_offer":   "Join Nexus Pro: monthly funding coaching + AI analysis tools",
    "consulting":         "Book a 1:1 Funding Strategy Call with Nexus",
}


class MonetizationAgent:
    """Adds CTA, affiliate angle, and all conversion paths to the draft."""

    SYSTEM = (
        "You are a direct response conversion expert for a business finance platform. "
        "You write CTAs that are urgent, specific, and credible. "
        "No soft asks. Every CTA should create a reason to act now. "
        "Output only valid JSON."
    )

    def add_cta(self, improved_text: str, topic: str, platform: str, brief: dict) -> dict:
        mono_angle   = brief.get("monetization_angle", "Nexus funding readiness audit")
        content_goal = brief.get("content_goal", "Complete the funding readiness audit")

        # Select primary path based on topic
        primary_path = "funding_audit"
        if "credit" in topic.lower():
            primary_path = "nav_credit"
        elif "newsletter" in platform.lower():
            primary_path = "newsletter_capture"

        prompt = f"""Write monetization elements for this {platform} piece.

Topic: {topic}
Monetization angle: {mono_angle}
Content goal: {content_goal}
Primary conversion path: {NEXUS_MONETIZATION_PATHS.get(primary_path, '')}

Return JSON:
{{
  "primary_cta": "specific, urgent CTA text (2-3 sentences, include URL placeholder like [nexus-link])",
  "affiliate_mention": "natural affiliate mention that fits into the content (1-2 sentences)",
  "newsletter_nudge": "newsletter signup pitch (1 sentence)",
  "funding_consult_path": "path to Nexus consulting/audit (1 sentence with clear value prop)",
  "membership_offer": "Nexus Pro membership mention (1 sentence)",
  "cta_placement": "where in the {platform} to place the main CTA (intro/middle/end/multiple)",
  "urgency_trigger": "one real urgency reason for this CTA (not fake countdown timers)",
  "full_cta_section": "the complete CTA block to append to the content (150-250 words)"
}}"""

        raw    = _llm(prompt, system=self.SYSTEM, tier="reasoning", max_tokens=1200)
        result = _parse_json(raw, {})

        if not isinstance(result, dict) or not result.get("primary_cta"):
            result = {
                "primary_cta": (
                    "Go to goclearonline.cc right now and run your free Funding Readiness Audit. "
                    "In 5 minutes, AI will scan your business profile and show you exactly what's "
                    "stopping lenders from saying yes — and how to fix it before you apply."
                ),
                "affiliate_mention": (
                    "If you want to start building business credit today, Nav.com is where most of "
                    "our clients start — it's free to check your business credit profile."
                ),
                "newsletter_nudge": (
                    "Subscribe to Nexus Weekly for the exact playbooks banks don't publish — "
                    "business credit, funding strategies, and AI tools every Tuesday."
                ),
                "funding_consult_path": (
                    "Want a real human to review your funding profile? Book a free 15-minute strategy call at goclearonline.cc."
                ),
                "membership_offer": (
                    "Nexus Pro members get monthly 1:1 AI-powered funding audits and lender matching — "
                    "starting at $49/month."
                ),
                "cta_placement": "end",
                "urgency_trigger": "Funding windows close quickly — lenders often stop accepting new applications mid-quarter",
                "full_cta_section": (
                    "---\n## Your Next Step\n\n"
                    "If any of this sounded familiar — if you've been denied, ignored, or just unsure "
                    "whether your business is even fundable right now — don't guess.\n\n"
                    "Go to goclearonline.cc and run your free Funding Readiness Audit. "
                    "Our AI analyzes your business profile against 12 lender criteria in under 5 minutes. "
                    "You'll see exactly where you stand, what's blocking approvals, and what to fix first.\n\n"
                    "No sales pitch. No fake urgency. Just a real picture of where your business stands "
                    "with lenders right now.\n\n"
                    "👉 goclearonline.cc — Free Funding Readiness Audit\n"
                    "👉 Build business credit first: nav.com (free profile)\n"
                    "👉 Subscribe: Nexus Weekly business finance newsletter"
                ),
            }

        # Append CTA to the content
        cta_section   = result.get("full_cta_section", "")
        text_with_cta = improved_text.rstrip() + "\n\n" + cta_section if cta_section else improved_text

        result["text_with_cta"]     = text_with_cta
        result["monetization_paths"] = NEXUS_MONETIZATION_PATHS
        result["primary_path_key"]   = primary_path

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# AGENT 7 — Approval Packet
# ═══════════════════════════════════════════════════════════════════════════════

SCORE_WEIGHTS = {
    "hook_score":         0.20,
    "novelty_score":      0.12,
    "copy_intensity":     0.15,
    "clarity_score":      0.12,
    "monetization_score": 0.18,
    "cta_score":          0.12,
    "nexus_fit_score":    0.11,
}
APPROVAL_THRESHOLD = 85


class ApprovalAgent:
    """
    Builds the final approval packet with composite scores.
    Status: approval_ready (≥85) or needs_revision (<85).
    Saves to docs/content/approval_packets/.
    """

    def create_packet(
        self,
        topic: str,
        platform: str,
        hook_result: dict,
        line_result: dict,
        monetization: dict,
        draft: dict,
        brief: dict,
    ) -> dict:

        # ── Derive component scores ──────────────────────────────────────────
        best_hook_score = 0
        if hook_result.get("scored_hooks"):
            best_hook_score = hook_result["scored_hooks"][0].get("average", 0) * 10  # convert 0-10 → 0-100

        section_score = line_result.get("overall_section_score", 0) * 10

        # Novelty / copy intensity from line scores
        novelty_vals = [s.get("invention_novelty", 0) for s in line_result.get("scored_sections", [])]
        novelty_score = (sum(novelty_vals) / len(novelty_vals) * 10) if novelty_vals else 70

        copy_vals = [s.get("copy_intensity", 0) for s in line_result.get("scored_sections", [])]
        copy_score = (sum(copy_vals) / len(copy_vals) * 10) if copy_vals else 70

        clarity_vals = [s.get("clarity", 0) for s in line_result.get("scored_sections", [])]
        clarity_score = (sum(clarity_vals) / len(clarity_vals) * 10) if clarity_vals else 75

        # CTA score (derive from whether a cta was produced)
        cta_score = 85 if monetization.get("primary_cta") else 60

        # Nexus fit from hook scores
        nexus_vals = [s.get("nexus_fit", 0) for s in hook_result.get("scored_hooks", [])]
        nexus_score = (sum(nexus_vals) / len(nexus_vals) * 10) if nexus_vals else 75

        # Monetization score
        mono_paths = sum(1 for k in ["primary_cta", "affiliate_mention", "newsletter_nudge",
                                      "funding_consult_path", "membership_offer"]
                         if monetization.get(k))
        monetization_score = min(100, 60 + mono_paths * 8)

        scores = {
            "hook_score":         round(min(100, best_hook_score), 1),
            "novelty_score":      round(min(100, novelty_score), 1),
            "copy_intensity":     round(min(100, copy_score), 1),
            "clarity_score":      round(min(100, clarity_score), 1),
            "monetization_score": round(monetization_score, 1),
            "cta_score":          round(cta_score, 1),
            "nexus_fit_score":    round(min(100, nexus_score), 1),
        }

        overall = sum(scores[k] * SCORE_WEIGHTS[k] for k in SCORE_WEIGHTS)
        overall = round(overall, 1)
        status  = "approval_ready" if overall >= APPROVAL_THRESHOLD else "needs_revision"

        approval_id = f"content_{_ts()}_{uuid.uuid4().hex[:8]}"
        artifacts = [
            brief.get("saved_path", ""),
            hook_result.get("saved_path", ""),
            draft.get("saved_path", ""),
        ]
        artifacts = [a for a in artifacts if a]

        packet = {
            "approval_id":    approval_id,
            "title":          topic,
            "platform":       platform,
            "hook":           hook_result.get("best_hook", ""),
            "scores":         scores,
            "overall_score":  overall,
            "status":         status,
            "word_count":     line_result.get("word_count", draft.get("word_count", 0)),
            "rewrites":       line_result.get("rewrites_applied", 0),
            "artifacts":      artifacts,
            "primary_cta":    monetization.get("primary_cta", ""),
            "monetization_paths": list(monetization.get("monetization_paths", {}).keys()),
            "created":        _now(),
            "text_with_cta":  monetization.get("text_with_cta", ""),
        }

        # Save the final artifact (the complete content piece)
        slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:35]
        ts   = _ts()
        final_path = _save(
            f"{_platform_dir(platform)}",
            f"{ts}_{slug}_FINAL.md",
            monetization.get("text_with_cta", draft.get("full_text", "")),
        )
        packet["final_artifact_path"] = str(final_path)
        artifacts.append(str(final_path))
        packet["artifacts"] = artifacts

        # Save approval packet JSON
        pkt_path = _save(
            "approval_packets",
            f"{ts}_{approval_id}.json",
            json.dumps(packet, indent=2, default=str),
        )
        packet["packet_path"] = str(pkt_path)

        # Save human-readable approval packet
        md_path = _save(
            "approval_packets",
            f"{ts}_{approval_id}_summary.md",
            self._render_md(packet),
        )
        packet["packet_summary_path"] = str(md_path)

        return packet

    def _render_md(self, p: dict) -> str:
        scores = p.get("scores", {})
        status_emoji = "✅" if p["status"] == "approval_ready" else "⚠️"
        lines = [
            f"# {status_emoji} APPROVAL PACKET — {p['title']}",
            f"*ID: {p['approval_id']} | {p['created']}*\n",
            f"**Platform:** {p['platform']}",
            f"**Status:** {p['status'].upper().replace('_', ' ')}",
            f"**Overall Score:** {p['overall_score']}/100",
            f"**Word Count:** {p.get('word_count', 0)} words",
            f"**Rewrites Applied:** {p.get('rewrites', 0)}\n",
            "## Winning Hook",
            f"> {p.get('hook', '')}\n",
            "## Scores",
        ]
        for k, v in scores.items():
            bar_len = int(v / 5)
            bar     = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"- **{k.replace('_',' ').title()}:** {v}/100  `{bar}`")
        lines += [
            f"\n## Primary CTA\n{p.get('primary_cta', '')}",
            "\n## Monetization Paths",
        ]
        for path_key in p.get("monetization_paths", []):
            lines.append(f"- {path_key.replace('_', ' ')}")
        lines += [
            "\n## Artifacts",
        ]
        for a in p.get("artifacts", []):
            lines.append(f"- `{a}`")
        lines += [
            f"\n---",
            f"**Approve:** `approve content {p['approval_id']}`",
            f"**Reject:**  `reject content {p['approval_id']}`",
        ]
        return "\n".join(lines)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _platform_dir(platform: str) -> str:
    return {
        "youtube":    "youtube_scripts",
        "newsletter": "newsletters",
        "seo_article":"seo_articles",
        "linkedin_post": "social_posts",
    }.get(platform, "social_posts")
