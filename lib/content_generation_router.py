"""
content_generation_router.py — Tiered content generation via OpenRouter.

Three routing tiers:
  LIGHTWEIGHT  — watcher polling, scoring, classification, ranking
               → deepseek/deepseek-chat (fast, cheap)
  REASONING    — analysis, planning, consensus, summaries
               → deepseek/deepseek-r1 or deepseek/deepseek-chat
  PREMIUM      — YouTube scripts, newsletter, SEO articles, affiliate content
               → anthropic/claude-3.5-sonnet (best) or openai/gpt-4o (fallback)

Quality controls:
  - Anti-template detection (unfilled placeholders, template markers)
  - Word count enforcement per content type
  - Filler phrase detection
  - Response quality scoring 0-100

Usage:
    from lib.content_generation_router import generate_content, is_template_output

    result = generate_content(
        prompt="Write a YouTube script about business credit",
        system="You are an expert content creator...",
        tier="premium",
        content_type="youtube_script",
        min_words=500,
    )
    if result["quality_score"] >= 60:
        use(result["response"])
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
import urllib.error
from typing import Optional

_OR_BASE  = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
_OR_KEY   = os.getenv("OPENROUTER_API_KEY", "")

# Tier → ordered model list (first available + healthy wins)
TIER_MODELS: dict[str, list[str]] = {
    "premium": [
        os.getenv("CONTENT_PREMIUM_MODEL", "anthropic/claude-3.5-sonnet"),
        "openai/gpt-4o",
        "deepseek/deepseek-r1",
        "deepseek/deepseek-chat",
    ],
    "reasoning": [
        os.getenv("CONTENT_REASONING_MODEL", "deepseek/deepseek-r1"),
        "deepseek/deepseek-chat",
    ],
    "lightweight": [
        os.getenv("CONTENT_LIGHTWEIGHT_MODEL", "deepseek/deepseek-chat"),
    ],
}

# Minimum word counts by content type
MIN_WORDS: dict[str, int] = {
    "youtube_script": 500,
    "newsletter": 300,
    "seo_article": 900,
    "linkedin_post": 120,
    "x_post": 10,
    "tiktok_hook": 8,
    "affiliate_content": 200,
    "cta_copy": 20,
    "landing_page": 400,
    "executive_summary": 100,
}

# Patterns that flag a response as template/unfilled output
_TEMPLATE_PATTERNS = [
    r"\[TEMPLATE",
    r"LLM unavailable",
    r"requires human completion",
    r"\[H2 Section",
    r"\[Introduction —",
    r"\[HOOK PARAGRAPH\]",
    r"\[MAIN SECTION \d",
    r"\[Article Title\]",
    r"Prompt intent:",
    r"Status: draft — requires",
    r"\[HOOK \(",
    r"\[INTRO \(",
    r"\[MAIN CONTENT",
]

# Filler phrases that reduce quality score
_FILLER_PHRASES = [
    "i'd be happy to",
    "certainly",
    "of course",
    "as an ai",
    "as a language model",
    "i cannot provide",
    "let me know if you",
    "feel free to",
    "please note that",
    "it's important to note",
    "it is worth noting",
    "in conclusion",
    "to summarize",
    "in summary",
    "I hope this helps",
    "hope this was helpful",
    "feel free to ask",
]

# Operational signal patterns that redeem quality
_QUALITY_SIGNALS = [
    r"\$\d+",                    # dollar amounts
    r"\d{1,3}%",                 # percentages
    r"step \d",                  # numbered steps
    r"##\s+\w",                  # markdown headers (H2+)
    r"\bCTA\b",                  # call to action markers
    r"\bSEO\b",                  # SEO markers
    r"https?://",                # actual URLs
    r"HOOK:",                    # script structure markers
    r"TITLE:",
    r"SECTION \d",
    r"[A-Z]{3,}:",               # structured labels
]


def is_template_output(text: str) -> bool:
    """Return True if text looks like an unfilled template."""
    for pattern in _TEMPLATE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def quality_score(text: str, content_type: str = "", min_words: int = 0) -> int:
    """
    Score generated content 0-100.
    Considers: word count, template markers, filler phrases, quality signals.
    """
    if not text or not text.strip():
        return 0

    if is_template_output(text):
        return 5

    words = len(text.split())
    required = min_words or MIN_WORDS.get(content_type, 0)

    # Word count score (0-40 pts)
    if required > 0:
        wc_score = min(40, int((words / required) * 40))
    else:
        wc_score = min(40, words // 5)

    # Filler penalty (up to -20 pts)
    lower = text.lower()
    filler_hits = sum(1 for p in _FILLER_PHRASES if p in lower)
    filler_penalty = min(20, filler_hits * 5)

    # Quality signal bonus (up to +30 pts)
    signal_hits = sum(1 for p in _QUALITY_SIGNALS if re.search(p, text))
    signal_bonus = min(30, signal_hits * 5)

    # Structure bonus (30 pts base)
    structure_score = 30 if required > 0 and words >= required else 15

    total = wc_score + structure_score + signal_bonus - filler_penalty
    return max(0, min(100, total))


def _call_openrouter(
    prompt: str,
    system: str,
    model: str,
    timeout: int = 90,
    max_tokens: int = 4096,
    response_format: Optional[dict] = None,
) -> dict:
    if not _OR_KEY:
        return {"success": False, "error": "OPENROUTER_API_KEY not set", "model": model}

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    data = json.dumps(payload).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_OR_KEY}",
        "HTTP-Referer": "https://nexus-ai-wealth.beehiiv.com",
        "X-Title": "Nexus AI Wealth",
    }

    t0 = time.monotonic()
    try:
        req = urllib.request.Request(
            f"{_OR_BASE}/chat/completions",
            data=data, headers=headers, method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())
        duration = round(time.monotonic() - t0, 2)
        text = (body.get("choices", [{}])[0].get("message", {}).get("content") or "").strip()
        if not text:
            return {"success": False, "error": "Empty response", "model": model, "duration_s": duration}
        return {"success": True, "response": text, "model": model, "duration_s": duration, "provider": "openrouter"}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")[:200]
        return {"success": False, "error": f"HTTP {e.code}: {err_body}", "model": model,
                "duration_s": round(time.monotonic() - t0, 2)}
    except Exception as exc:
        return {"success": False, "error": str(exc), "model": model,
                "duration_s": round(time.monotonic() - t0, 2)}


def _call_local_fallback(prompt: str, system: str, timeout: int = 90) -> dict:
    """Fall back to nexus_model_caller for lightweight/local generation."""
    try:
        from lib.nexus_model_caller import call
        result = call(prompt, task_type="cheap", system=system, timeout=timeout)
        if result.get("success"):
            return {"success": True, "response": result["response"],
                    "model": result.get("model", "local"), "provider": result.get("provider", "local"),
                    "duration_s": result.get("duration_s", 0)}
        return {"success": False, "error": result.get("error", "local call failed")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def generate_content(
    prompt: str,
    system: str = "",
    tier: str = "premium",
    content_type: str = "",
    min_words: int = 0,
    timeout: int = 120,
    max_tokens: int = 4096,
    require_quality: int = 50,
) -> dict:
    """
    Generate content using tiered model routing.

    Args:
        prompt:          The generation prompt.
        system:          System context/persona.
        tier:            "premium" | "reasoning" | "lightweight"
        content_type:    e.g. "youtube_script", "newsletter", "seo_article"
        min_words:       Override minimum word count check.
        timeout:         HTTP timeout per attempt.
        max_tokens:      Token budget for the response.
        require_quality: Minimum quality score to accept (default 50).
                         If not met, tries next model in tier before returning best.

    Returns dict with:
        success, response, model, provider, quality_score, is_template,
        word_count, duration_s, fallback_used, error
    """
    if not _OR_KEY and tier in ("premium", "reasoning"):
        # No OpenRouter key — fall back to local
        result = _call_local_fallback(prompt, system, timeout)
        text = result.get("response") or ""
        score = quality_score(text, content_type, min_words)
        return {**result, "quality_score": score, "is_template": is_template_output(text),
                "word_count": len(text.split()), "fallback_used": True,
                "fallback_reason": "OPENROUTER_API_KEY not set"}

    models = TIER_MODELS.get(tier, TIER_MODELS["premium"])
    best: dict = {}
    best_score = -1

    for i, model in enumerate(models):
        result = _call_openrouter(prompt, system, model, timeout=timeout, max_tokens=max_tokens)
        if not result.get("success"):
            continue

        text = result["response"]
        score = quality_score(text, content_type, min_words)
        result["quality_score"] = score
        result["is_template"] = is_template_output(text)
        result["word_count"] = len(text.split())
        result["fallback_used"] = i > 0

        if score >= require_quality:
            return result  # Good enough — return immediately

        if score > best_score:
            best = result
            best_score = score

    if best:
        return best

    # All OpenRouter attempts failed — try local
    local = _call_local_fallback(prompt, system, timeout)
    text = local.get("response") or ""
    score = quality_score(text, content_type, min_words)
    return {
        **local,
        "quality_score": score,
        "is_template": is_template_output(text),
        "word_count": len(text.split()),
        "fallback_used": True,
        "fallback_reason": f"OpenRouter failed for all {tier} models",
    }


def lightweight(prompt: str, system: str = "", timeout: int = 45) -> str:
    """Quick convenience wrapper for lightweight classification/scoring tasks."""
    result = generate_content(prompt, system=system, tier="lightweight", timeout=timeout,
                               max_tokens=512, require_quality=20)
    return result.get("response") or ""


def reasoning(prompt: str, system: str = "", timeout: int = 60) -> str:
    """Convenience wrapper for medium-tier reasoning/analysis tasks."""
    result = generate_content(prompt, system=system, tier="reasoning", timeout=timeout,
                               max_tokens=2048, require_quality=40)
    return result.get("response") or ""


def check_openrouter_health() -> dict:
    """Verify OpenRouter connectivity and key validity."""
    if not _OR_KEY:
        return {"healthy": False, "reason": "OPENROUTER_API_KEY not set"}
    result = _call_openrouter(
        prompt="Reply with exactly: NEXUS_OK",
        system="",
        model="deepseek/deepseek-chat",
        timeout=15,
        max_tokens=20,
    )
    return {
        "healthy": result.get("success", False),
        "model": result.get("model"),
        "duration_s": result.get("duration_s"),
        "error": result.get("error"),
    }
