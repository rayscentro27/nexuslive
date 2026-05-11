"""
nexus_model_caller.py — Unified model caller for nexus-ai.

Combines provider selection (model_router) with the actual HTTP call.
Supports all provider formats: openai, ollama_generate, anthropic.

Usage:
    from lib.nexus_model_caller import call

    result = call("Summarize recent activity", task_type="cheap")
    if result["success"]:
        print(result["response"])

Returns:
    {
        "success":      bool,
        "response":     str | None,
        "provider":     str,
        "model":        str,
        "cost_tier":    str,
        "duration_s":   float,
        "fallback_used": bool,
        "fallback_reason": str,
        "error":        str | None,
    }
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger("NexusModelCaller")

_DEFAULT_TIMEOUT   = 90
_DEFAULT_MAX_TOKENS = 2048


def call(
    prompt:     str,
    task_type:  str = "draft",
    system:     str = "",
    timeout:    int = _DEFAULT_TIMEOUT,
    max_tokens: int = _DEFAULT_MAX_TOKENS,
    min_context: int = 0,
    model_source: str = "auto",
) -> dict:
    """
    Select a provider via model_router and make the API call.

    On provider failure, falls back to the next provider in the chain
    (one automatic retry, then returns the error).
    """
    from lib.model_router import get_provider, ModelRoutingError

    attempts: list[str] = []

    for attempt in range(2):
        try:
            provider = get_provider(
                task_type=task_type,
                model_source=model_source,
                min_context=min_context,
            )
        except ModelRoutingError as e:
            return _fail("(none)", "(none)", "free", str(e), attempts)

        name      = provider["name"]
        fmt       = provider["format"]
        attempts.append(name)

        result = _dispatch(
            provider=provider,
            prompt=prompt,
            system=system,
            timeout=timeout,
            max_tokens=max_tokens,
        )

        if result["success"]:
            result["fallback_used"]   = attempt > 0
            result["fallback_reason"] = f"Primary provider(s) failed: {', '.join(attempts[:-1])}" if attempt > 0 else ""
            return result

        logger.warning(
            "Provider %s failed (%s) — %s",
            name, result.get("error"), "retrying" if attempt == 0 else "exhausted",
        )

    return _fail(
        provider=attempts[-1] if attempts else "(none)",
        model="(unknown)",
        cost_tier="free",
        error=f"All providers failed: {', '.join(attempts)}",
        attempts=attempts,
    )


def _dispatch(
    provider:   dict,
    prompt:     str,
    system:     str,
    timeout:    int,
    max_tokens: int,
) -> dict:
    fmt  = provider["format"]
    name = provider["name"]

    if fmt == "ollama_generate":
        return _call_ollama(provider, prompt, system, timeout)
    if fmt == "anthropic":
        return _call_anthropic(provider, prompt, system, timeout, max_tokens)
    if fmt == "openai":
        return _call_openai(provider, prompt, system, timeout, max_tokens)

    return _fail(name, provider.get("model", "?"), provider.get("cost_tier", "?"),
                 f"Unknown format: {fmt}")


# ── OpenAI-compatible caller (covers Hermes, OpenRouter, Groq, Nvidia, Gemini, OpenClaw, ChatGPT, Oracle Ollama) ──

def _call_openai(
    provider:   dict,
    prompt:     str,
    system:     str,
    timeout:    int,
    max_tokens: int,
) -> dict:
    name  = provider["name"]
    url   = provider["url"].rstrip("/") + "/chat/completions"
    key   = provider.get("key") or ""
    model = provider["model"]

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model":      model,
        "messages":   messages,
        "max_tokens": max_tokens,
    }).encode()

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    # OpenClaw uses its own auth header format
    if name == "openclaw":
        oc_token = os.getenv("OPENCLAW_AUTH_TOKEN", key)
        if oc_token:
            headers["Authorization"] = f"Bearer {oc_token}"

    return _http_post(url, payload, headers, name, model, provider.get("cost_tier", "medium"), timeout)


# ── Ollama /api/generate caller (Netcup SSH-tunnel path) ──────────────────────

def _call_ollama(
    provider:   dict,
    prompt:     str,
    system:     str,
    timeout:    int,
) -> dict:
    name  = provider["name"]
    url   = provider["url"]   # already the full /api/generate URL
    model = provider["model"]

    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    payload = json.dumps({
        "model":  model,
        "prompt": full_prompt,
        "stream": False,
    }).encode()

    headers = {"Content-Type": "application/json"}
    t0 = time.monotonic()
    try:
        req  = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        duration = round(time.monotonic() - t0, 2)
        text = (data.get("response") or "").strip()
        if not text:
            return _fail(name, model, provider.get("cost_tier", "free"), "Empty response", duration=duration)
        return _ok(name, model, provider.get("cost_tier", "free"), text, duration)
    except Exception as e:
        return _fail(name, model, provider.get("cost_tier", "free"), str(e),
                     duration=round(time.monotonic() - t0, 2))


# ── Anthropic caller ──────────────────────────────────────────────────────────

def _call_anthropic(
    provider:   dict,
    prompt:     str,
    system:     str,
    timeout:    int,
    max_tokens: int,
) -> dict:
    name  = provider["name"]
    url   = provider["url"].rstrip("/") + "/messages"
    key   = provider.get("key") or ""
    model = provider["model"]

    body: dict = {
        "model":      model,
        "max_tokens": max_tokens,
        "messages":   [{"role": "user", "content": prompt}],
    }
    if system:
        body["system"] = system

    payload = json.dumps(body).encode()
    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         key,
        "anthropic-version": "2023-06-01",
    }
    return _http_post(url, payload, headers, name, model, provider.get("cost_tier", "high"), timeout,
                      response_extractor=_extract_anthropic)


# ── HTTP primitives ───────────────────────────────────────────────────────────

def _http_post(
    url:         str,
    payload:     bytes,
    headers:     dict,
    name:        str,
    model:       str,
    cost_tier:   str,
    timeout:     int,
    response_extractor=None,
) -> dict:
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        duration = round(time.monotonic() - t0, 2)
        extractor = response_extractor or _extract_openai
        text = extractor(data)
        if not text:
            return _fail(name, model, cost_tier, "Empty response from API", duration=duration)
        return _ok(name, model, cost_tier, text, duration)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:200]
        return _fail(name, model, cost_tier, f"HTTP {e.code}: {body}",
                     duration=round(time.monotonic() - t0, 2))
    except urllib.error.URLError as e:
        return _fail(name, model, cost_tier, f"Connection failed: {e}",
                     duration=round(time.monotonic() - t0, 2))
    except Exception as e:
        return _fail(name, model, cost_tier, str(e),
                     duration=round(time.monotonic() - t0, 2))


def _extract_openai(data: dict) -> str:
    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError):
        return ""


def _extract_anthropic(data: dict) -> str:
    try:
        return (data["content"][0]["text"] or "").strip()
    except (KeyError, IndexError):
        return ""


def _ok(provider: str, model: str, cost_tier: str, response: str, duration: float = 0.0) -> dict:
    logger.info("Call OK — provider=%s model=%s cost=%s %.1fs", provider, model, cost_tier, duration)
    return {
        "success":        True,
        "response":       response,
        "provider":       provider,
        "model":          model,
        "cost_tier":      cost_tier,
        "duration_s":     duration,
        "fallback_used":  False,
        "fallback_reason": "",
        "error":          None,
    }


def _fail(
    provider:  str,
    model:     str,
    cost_tier: str,
    error:     str,
    attempts:  Optional[list] = None,
    duration:  float = 0.0,
) -> dict:
    logger.warning("Call FAIL — provider=%s error=%s", provider, error)
    return {
        "success":        False,
        "response":       None,
        "provider":       provider,
        "model":          model,
        "cost_tier":      cost_tier,
        "duration_s":     duration,
        "fallback_used":  bool(attempts and len(attempts) > 1),
        "fallback_reason": f"Tried: {', '.join(attempts)}" if attempts else "",
        "error":          error,
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    from lib.model_router import provider_summary
    print("Provider summary:")
    for p in provider_summary():
        status = "OK " if p["configured"] else "---"
        print(f"  [{status}] {p['name']:<18} {p['cost_tier']:<8}  {p['url']}")
    print()

    task = sys.argv[1] if len(sys.argv) > 1 else "cheap"
    print(f"Testing task_type={task!r} …")
    result = call("Reply with exactly three words: NEXUS_ROUTING_OK", task_type=task, timeout=30)
    if result["success"]:
        print(f"  OK  provider={result['provider']} model={result['model']} cost={result['cost_tier']} ({result['duration_s']}s)")
        print(f"  Response: {result['response'][:100]}")
    else:
        print(f"  FAIL  {result['error']}")
        print(f"  Tried: {result.get('fallback_reason', '')}")
        sys.exit(1)
