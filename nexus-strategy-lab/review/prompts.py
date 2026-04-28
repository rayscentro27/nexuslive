"""
review/prompts.py — AI prompt builders for strategy review.

All prompts request structured JSON output so the response can be
parsed deterministically without NLP post-processing.
"""

import json


SYSTEM_PROMPT = """\
You are Hermes, a rigorous trading strategy analyst for the Nexus AI hedge fund.
Your job is to evaluate educational trading strategy content and produce a
structured quality review.

Rules:
- Be critical and specific. Generic praise is useless.
- Flag red flags (execution instructions, guaranteed profit claims, vague rules).
- Score 0–100 where 100 = publication-ready, institutional quality.
- Always respond with valid JSON only. No markdown, no prose outside JSON.
"""


def build_review_prompt(strategy: dict, scores: dict) -> str:
    """
    Build a structured review prompt for a strategy_library entry.

    Args:
        strategy: strategy_library row
        scores:   strategy_scores row
    """
    name     = strategy.get('strategy_name') or strategy.get('title') or 'Unknown'
    market   = strategy.get('market') or 'unknown'
    setup    = strategy.get('setup_type') or 'general'
    summary  = strategy.get('summary') or ''
    entry    = json.dumps(strategy.get('entry_rules') or {}, indent=2)
    exit_    = json.dumps(strategy.get('exit_rules') or {}, indent=2)
    risk     = json.dumps(strategy.get('risk_rules') or {}, indent=2)
    inv      = json.dumps(strategy.get('invalidation_rules') or {}, indent=2)
    pitfalls = json.dumps(strategy.get('pitfalls') or {}, indent=2)
    inds     = json.dumps(strategy.get('indicators') or [])

    det_score  = scores.get('total_score', 0)
    clarity    = scores.get('clarity_score', 0)
    risk_def   = scores.get('risk_definition_score', 0)
    testable   = scores.get('testability_score', 0)
    det_notes  = scores.get('reasoning') or ''

    return f"""\
Evaluate this trading strategy and return a JSON object with exactly these fields:

{{
  "review_score": <integer 0-100>,
  "recommendation": "<approve|review|reject>",
  "review_text": "<2-4 sentence qualitative assessment>",
  "strengths": ["<strength 1>", "<strength 2>"],
  "weaknesses": ["<weakness 1>", "<weakness 2>"],
  "missing_elements": ["<what is missing>"],
  "risk_assessment": "<one sentence on risk management quality>",
  "enhanced_summary": "<improved 1-2 sentence summary suitable for the portal>",
  "when_it_works": "<one sentence on ideal market conditions>",
  "when_it_fails": "<one sentence on conditions to avoid>",
  "recommendations": ["<action 1>", "<action 2>"]
}}

=== STRATEGY ===
Name: {name}
Market: {market}
Setup type: {setup}
Indicators: {inds}

Summary:
{summary[:600]}

Entry rules:
{entry[:400]}

Exit rules:
{exit_[:400]}

Risk rules:
{risk[:400]}

Invalidation rules:
{inv[:300]}

Pitfalls:
{pitfalls[:300]}

=== DETERMINISTIC PRE-SCORE (0-100) ===
Total: {det_score}
Clarity: {clarity} | Risk definition: {risk_def} | Testability: {testable}
Notes: {det_notes[:200]}

Return ONLY the JSON object. No explanation, no markdown fences."""


def build_batch_summary_prompt(reviews: list[dict]) -> str:
    """
    Build a prompt for a batch summary of reviewed strategies.
    Used for the founder Telegram digest.
    """
    lines = []
    for r in reviews[:10]:
        lines.append(
            f"- {r.get('strategy_name','?')[:50]}: score={r.get('review_score')} "
            f"rec={r.get('recommendation')}"
        )
    strategies_text = '\n'.join(lines)

    return f"""\
Summarize these strategy review results for a fund manager in 3-4 sentences.
Focus on what was approved, what needs work, and the overall pipeline health.

{strategies_text}

Return ONLY a JSON object:
{{
  "digest": "<3-4 sentence summary>",
  "top_strategy": "<name of best scoring strategy or null>",
  "action_required": "<yes|no>",
  "action_note": "<what action to take or null>"
}}"""
