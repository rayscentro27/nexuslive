#!/usr/bin/env python3
"""
Research Summarizer
Primary: generic OpenAI-compatible gateway (Hermes/OpenRouter/OpenAI-style)
Fallback: Gemini API
"""
import os
import json
import urllib.request
import urllib.error

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(usecwd=False) or os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass

LLM_BASE_URL = (
    os.getenv("NEXUS_LLM_BASE_URL")
    or os.getenv("OPENROUTER_BASE_URL")
    or os.getenv("OPENAI_BASE_URL")
    or "https://openrouter.ai/api/v1"
).rstrip("/")
LLM_API_KEY = (
    os.getenv("NEXUS_LLM_API_KEY")
    or os.getenv("OPENROUTER_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or ""
)
LLM_MODEL = (
    os.getenv("NEXUS_LLM_MODEL")
    or os.getenv("OPENROUTER_MODEL")
    or os.getenv("OPENAI_MODEL")
    or "meta-llama/llama-3.3-70b-instruct"
)

GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL       = "gemini-2.0-flash"

TRANSCRIPTS = "./transcripts"
SUMMARIES   = "./summaries"

os.makedirs(SUMMARIES, exist_ok=True)

SYSTEM_PROMPT = (
    "You are a trading research analyst. Extract structured insights from trading transcripts. "
    "Be specific, actionable, and well-organized."
)

USER_PROMPT = """\
Analyze this trading transcript and extract structured insights.

Provide a summary with these sections:
**Strategies**: Specific trading strategies, entry/exit rules, setups
**Indicators**: Technical indicators and how they're used
**Risk Management**: Position sizing, stop loss rules, risk/reward ratios
**Trade Setups**: Specific patterns or conditions for entering trades
**Psychology**: Mental framework, discipline, and mindset advice

Transcript:
{text}"""


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(url, data=data, headers={**headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _chat_completions_url(base_url: str) -> str:
    if base_url.endswith("/v1") or base_url.endswith("/api/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def summarize_via_llm(text: str) -> str:
    truncated = text[:15000] + ("\n\n[Transcript truncated]" if len(text) > 15000 else "")
    result = _post_json(
        _chat_completions_url(LLM_BASE_URL),
        {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": USER_PROMPT.format(text=truncated)},
            ],
            "max_tokens": 2048,
        },
        {"Authorization": f"Bearer {LLM_API_KEY}"},
    )
    return result["choices"][0]["message"]["content"]


def summarize_via_gemini(text: str) -> str:
    truncated = text[:15000] + ("\n\n[Transcript truncated]" if len(text) > 15000 else "")
    prompt    = f"{SYSTEM_PROMPT}\n\n{USER_PROMPT.format(text=truncated)}"
    url       = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    result    = _post_json(url, {"contents": [{"parts": [{"text": prompt}]}]}, {})
    return result["candidates"][0]["content"]["parts"][0]["text"]


def summarize_transcript(text: str) -> tuple[str, str]:
    """Returns (summary_text, provider_used)."""
    # Try configured AI gateway first
    if LLM_API_KEY:
        try:
            return summarize_via_llm(text), "llm_gateway"
        except Exception as e:
            print(f"    ⚠️  LLM gateway unavailable ({type(e).__name__}), falling back to Gemini...")

    # Gemini fallback
    if GEMINI_API_KEY:
        return summarize_via_gemini(text), "gemini"

    raise RuntimeError("No AI provider available — set NEXUS_LLM_API_KEY/OPENROUTER_API_KEY or GEMINI_API_KEY_1 in .env")


def main():
    if not LLM_API_KEY and not GEMINI_API_KEY:
        print("ERROR: No AI provider configured. Set NEXUS_LLM_API_KEY/OPENROUTER_API_KEY or GEMINI_API_KEY_1 in .env")
        return

    if not os.path.isdir(TRANSCRIPTS):
        print(f"ERROR: Transcripts folder not found: {TRANSCRIPTS}\nRun collector.py first.")
        return

    files = [f for f in os.listdir(TRANSCRIPTS) if f.endswith(('.vtt', '.srt'))]
    if not files:
        print(f"No transcript files found in {TRANSCRIPTS}/")
        return

    print(f"📄 Found {len(files)} transcripts to summarize")
    done = skipped = errors = 0

    for file in sorted(files):
        summary_file = os.path.join(SUMMARIES, file + ".summary")
        if os.path.exists(summary_file):
            skipped += 1
            continue

        path = os.path.join(TRANSCRIPTS, file)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except Exception as e:
            print(f"  ⚠️  Could not read {file}: {e}")
            errors += 1
            continue

        print(f"  🧠 Summarizing: {file}")
        try:
            summary, provider = summarize_transcript(text)
        except Exception as e:
            print(f"  ❌ Error summarizing {file}: {e}")
            errors += 1
            continue

        with open(summary_file, "w", encoding='utf-8') as f:
            f.write(summary)

        done += 1
        print(f"  ✅ Summarized via {provider}: {file}")

    print(f"\n✅ Done — {done} new summaries, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
