"""
hermes_ollama_client.py — Hermes Ollama API client.

Calls the Netcup Ollama server (via SSH tunnel on Mac mini) or any Ollama endpoint.
Supports explicit model selection so callers can choose default vs reasoning model.

ENV:
  OLLAMA_BASE_URL          Base URL without path  (default: http://localhost:11555)
  HERMES_DEFAULT_MODEL     Lightweight model       (default: llama3.2:3b)
  HERMES_REASONING_MODEL   Hard-reasoning model    (default: qwen3:8b)

The tunnel must be open on the Mac mini:
  ssh -N -L 11555:localhost:11434 root@YOUR_NETCUP_IP
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger("HermesOllamaClient")

# Never log secrets — these are local model names, not tokens.
OLLAMA_BASE_URL        = os.getenv("OLLAMA_BASE_URL",        "http://localhost:11555")
HERMES_DEFAULT_MODEL   = os.getenv("HERMES_DEFAULT_MODEL",   "llama3.2:3b")
HERMES_REASONING_MODEL = os.getenv("HERMES_REASONING_MODEL", "qwen3:8b")

_DEFAULT_TIMEOUT = 90   # seconds — qwen3:8b needs headroom on cold start
_PING_TIMEOUT    = 4    # seconds — fast reachability check


def _generate_url() -> str:
    base = OLLAMA_BASE_URL.rstrip("/")
    return f"{base}/api/generate"


def _tags_url() -> str:
    base = OLLAMA_BASE_URL.rstrip("/")
    return f"{base}/api/tags"


def call(
    prompt:  str,
    model:   Optional[str] = None,
    timeout: int = _DEFAULT_TIMEOUT,
    system:  str = "",
) -> dict:
    """
    POST to Ollama /api/generate and return a structured result.

    Args:
        prompt:  The user prompt text.
        model:   Ollama model name. Defaults to HERMES_DEFAULT_MODEL.
        timeout: HTTP timeout in seconds.
        system:  Optional system prompt (prepended to prompt via Ollama's format).

    Returns:
        {
            "success":    bool,
            "response":   str | None,
            "model":      str,
            "duration_s": float,
            "source":     "netcup_ollama",
            "error":      str | None,
            "fallback_used": bool,
        }
    """
    resolved_model = model or HERMES_DEFAULT_MODEL
    url = _generate_url()

    full_prompt = f"{system}\n\n{prompt}" if system else prompt
    payload = json.dumps({
        "model":  resolved_model,
        "prompt": full_prompt,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.monotonic()
    try:
        logger.info("Ollama call → model=%s timeout=%ds", resolved_model, timeout)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())

        duration = round(time.monotonic() - t0, 2)
        response_text = (data.get("response") or "").strip()

        if not response_text:
            logger.warning("Ollama model=%s returned empty response (%.1fs)", resolved_model, duration)
            return _err(resolved_model, "Empty response from model", duration)

        logger.info("Ollama model=%s OK — %d chars in %.1fs", resolved_model, len(response_text), duration)
        return {
            "success":      True,
            "response":     response_text,
            "model":        resolved_model,
            "duration_s":   duration,
            "source":       "netcup_ollama",
            "error":        None,
            "fallback_used": False,
        }

    except urllib.error.URLError as e:
        duration = round(time.monotonic() - t0, 2)
        logger.error("Ollama model=%s unreachable (tunnel down?): %s", resolved_model, e)
        return _err(resolved_model, f"Connection failed: {e}", duration)

    except TimeoutError:
        duration = round(time.monotonic() - t0, 2)
        logger.error("Ollama model=%s timed out after %ds", resolved_model, timeout)
        return _err(resolved_model, f"Timeout after {timeout}s", duration)

    except Exception as e:
        duration = round(time.monotonic() - t0, 2)
        logger.error("Ollama model=%s unexpected error: %s", resolved_model, e)
        return _err(resolved_model, str(e), duration)


def call_with_fallback(
    prompt:           str,
    primary_model:    Optional[str] = None,
    fallback_model:   Optional[str] = None,
    timeout:          int = _DEFAULT_TIMEOUT,
    system:           str = "",
) -> dict:
    """
    Try primary_model; if it fails, silently retry with fallback_model.

    primary_model  defaults to HERMES_REASONING_MODEL  (qwen3:8b)
    fallback_model defaults to HERMES_DEFAULT_MODEL     (llama3.2:3b)

    The returned dict includes "fallback_used": True if the primary failed.
    """
    p = primary_model  or HERMES_REASONING_MODEL
    f = fallback_model or HERMES_DEFAULT_MODEL

    result = call(prompt, model=p, timeout=timeout, system=system)
    if result["success"]:
        return result

    logger.warning(
        "Primary model %s failed (%s) — retrying with %s",
        p, result.get("error", "?"), f,
    )
    fallback = call(prompt, model=f, timeout=timeout, system=system)
    fallback["fallback_used"] = True
    fallback["fallback_reason"] = f"Primary model {p} unavailable: {result.get('error', '?')}"
    return fallback


def is_reachable(timeout: float = _PING_TIMEOUT) -> bool:
    """Quick ping — True if the Ollama endpoint responds to /api/tags."""
    try:
        req = urllib.request.Request(_tags_url(), method="GET")
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False


def list_models(timeout: float = 6.0) -> list[str]:
    """Return names of models currently loaded on the Ollama server."""
    try:
        req = urllib.request.Request(_tags_url(), method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


# ── Helpers ────────────────────────────────────────────────────────────────────

def _err(model: str, error: str, duration: float = 0.0) -> dict:
    return {
        "success":      False,
        "response":     None,
        "model":        model,
        "duration_s":   duration,
        "source":       "netcup_ollama",
        "error":        error,
        "fallback_used": False,
    }


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    print(f"Ollama base URL : {OLLAMA_BASE_URL}")
    print(f"Default model   : {HERMES_DEFAULT_MODEL}")
    print(f"Reasoning model : {HERMES_REASONING_MODEL}")
    print(f"Reachable       : {is_reachable()}")
    print(f"Models loaded   : {list_models()}")
    print()

    test_model = sys.argv[1] if len(sys.argv) > 1 else HERMES_DEFAULT_MODEL
    print(f"Testing {test_model}...")
    result = call("Reply with exactly: OLLAMA_OK", model=test_model, timeout=30)
    if result["success"]:
        print(f"  OK — {result['response'][:80]} ({result['duration_s']}s)")
    else:
        print(f"  FAIL — {result['error']}")
        sys.exit(1)
