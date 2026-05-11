"""
ollama_fallback.py — Netcup Ollama fallback for nexus-ai workers.

Calls the Netcup ARM64 server via SSH tunnel (localhost:11555 → remote:11434).
Used when Hermes/OpenRouter are unavailable, rate-limited, or returning empty.

SSH tunnel setup (run once per session or via launchd):
    ssh -N -L 11555:localhost:11434 root@v2202604354135454731.luckysrv.de

Environment variables:
    OLLAMA_FALLBACK_URL    default: http://localhost:11555/api/generate
    OLLAMA_FALLBACK_MODEL  default: llama3.2:3b
    HERMES_FALLBACK_ENABLED default: true

Usage:
    from lib.ollama_fallback import run_ollama_fallback

    result = run_ollama_fallback("Summarize this text: ...")
    if result["success"]:
        text = result["response"]
    else:
        print(result["error"])
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger("OllamaFallback")

OLLAMA_FALLBACK_URL     = os.getenv("OLLAMA_FALLBACK_URL",    "http://localhost:11555/api/generate")
OLLAMA_FALLBACK_MODEL   = os.getenv("OLLAMA_FALLBACK_MODEL",  "llama3.2:3b")
HERMES_FALLBACK_ENABLED = os.getenv("HERMES_FALLBACK_ENABLED", "true").lower() not in ("false", "0", "no")

_TIMEOUT = 60  # seconds — 3B model on ARM is fast but allow headroom


def _disabled_result(reason: str) -> dict:
    return {
        "source":        "netcup_ollama",
        "model":         OLLAMA_FALLBACK_MODEL,
        "response":      None,
        "fallback_used": True,
        "success":       False,
        "error":         reason,
    }


def run_ollama_fallback(prompt: str, timeout: int = _TIMEOUT) -> dict:
    """
    POST to the Netcup Ollama instance and return a structured result.

    Returns:
        {
            "source":        "netcup_ollama",
            "model":         str,
            "response":      str | None,
            "fallback_used": True,
            "success":       bool,
            "error":         str | None,
        }
    """
    if not HERMES_FALLBACK_ENABLED:
        logger.debug("Netcup fallback skipped — HERMES_FALLBACK_ENABLED=false")
        return _disabled_result("HERMES_FALLBACK_ENABLED=false")

    payload = json.dumps({
        "model":  OLLAMA_FALLBACK_MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        OLLAMA_FALLBACK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        logger.info("Netcup Ollama fallback triggered → %s", OLLAMA_FALLBACK_URL)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())

        response_text = (data.get("response") or "").strip()
        if not response_text:
            logger.warning("Netcup Ollama returned empty response")
            return _disabled_result("Empty response from model")

        logger.info("Netcup Ollama fallback succeeded (%d chars)", len(response_text))
        return {
            "source":        "netcup_ollama",
            "model":         OLLAMA_FALLBACK_MODEL,
            "response":      response_text,
            "fallback_used": True,
            "success":       True,
            "error":         None,
        }

    except urllib.error.URLError as e:
        logger.error("Netcup Ollama unreachable (tunnel down?): %s", e)
        return _disabled_result(f"Connection failed: {e}")

    except TimeoutError:
        logger.error("Netcup Ollama timed out after %ds", timeout)
        return _disabled_result(f"Timeout after {timeout}s")

    except Exception as e:
        logger.error("Netcup Ollama unexpected error: %s", e)
        return _disabled_result(str(e))


def is_available(timeout: float = 3.0) -> bool:
    """Quick health check — True if the tunnel endpoint is reachable."""
    base = OLLAMA_FALLBACK_URL.rsplit("/api/", 1)[0]
    try:
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not HERMES_FALLBACK_ENABLED:
        print("HERMES_FALLBACK_ENABLED=false — fallback is disabled")
        sys.exit(0)

    print(f"Testing Netcup Ollama at {OLLAMA_FALLBACK_URL} (model={OLLAMA_FALLBACK_MODEL})")
    print(f"Reachable: {is_available()}")

    result = run_ollama_fallback("Reply with exactly: NETCUP_OK")
    if result["success"]:
        print(f"Response: {result['response'][:200]}")
    else:
        print(f"FAILED: {result['error']}")
        sys.exit(1)
