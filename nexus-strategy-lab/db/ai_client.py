"""
db/ai_client.py — Unified AI gateway client.

Provider chain (auto mode):
  1. Hermes gateway (local, fast)
  2. OpenRouter (paid, 128K+ context)
  3. Netcup Ollama (SSH tunnel fallback, free)

model_source kwarg:
  "hermes"        → Hermes only
  "netcup_ollama" → Netcup Ollama directly, skip Hermes
  "auto"          → full chain with Netcup as last resort
"""
import logging
import os
import sys
import requests
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from config import settings

# Resolve nexus-ai root so lib/ is importable regardless of cwd
_ROOT = Path(__file__).resolve().parent.parent.parent  # nexus-strategy-lab/../..
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.ollama_fallback import run_ollama_fallback, HERMES_FALLBACK_ENABLED  # noqa: E402

logger = logging.getLogger(__name__)
HERMES_MODEL = os.getenv('HERMES_MODEL', 'hermes')


def _resolve_model(url: str, model: str) -> str:
    """
    Local Hermes gateways only accept `hermes` or `hermes/<agentId>`.
    Preserve explicit gateway-safe ids, but remap external provider ids when
    we're targeting the local daemon.
    """
    host = (urlparse(url).hostname or '').lower()
    if model.startswith('hermes'):
        return model
    if host in ('localhost', '127.0.0.1'):
        logger.info("Remapping model %s -> hermes for local gateway %s", model, url)
        return 'hermes'
    return model


def _is_capacity_response(text: str | None) -> bool:
    t = (text or '').lower()
    return any(marker in t for marker in (
        'rate limit',
        'too many requests',
        'capacity',
        'try again later',
        'free-models-per-min',
    ))


def _completion_endpoint(url: str) -> str:
    base = url.rstrip('/')
    if base.endswith('/v1'):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _chat(url: str, token: str, prompt: str, system: str = '', model: str = 'default',
          max_tokens: int = 1024, temperature: float = 0.3) -> Optional[str]:
    """Call a /v1/chat/completions endpoint; returns text content or None."""
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    resolved_model = _resolve_model(url, model)
    try:
        r = requests.post(
            _completion_endpoint(url),
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
            },
            json={
                'model': resolved_model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature,
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        logger.debug(f"AI call failed ({url}): {e}")
        return None


def complete(prompt: str, system: str = '', max_tokens: int = 1024,
             temperature: float = 0.3, provider: Optional[str] = None,
             model_source: str = 'auto') -> str:
    """
    Generate a completion.

    model_source:
      "hermes"        → Hermes gateway only
      "netcup_ollama" → Netcup Ollama directly (skip Hermes)
      "auto"          → Hermes → OpenRouter → Netcup Ollama

    provider kwarg (legacy): overrides AI_PROVIDER setting, not model_source.
    Raises RuntimeError if all providers fail.
    """
    # ── Direct Netcup path ────────────────────────────────────────────────────
    if model_source == 'netcup_ollama':
        full_prompt = f"{system}\n\n{prompt}".strip() if system else prompt
        result = run_ollama_fallback(full_prompt)
        if result['success']:
            logger.info("AI response via netcup_ollama (direct)")
            return result['response']
        raise RuntimeError(f"Netcup Ollama failed: {result['error']}")

    # ── OpenAI-compatible provider chain ──────────────────────────────────────
    pref = provider or settings.AI_PROVIDER

    if model_source == 'hermes' or pref == 'hermes':
        providers = [('hermes', settings.HERMES_GATEWAY_URL, settings.HERMES_GATEWAY_TOKEN, 'hermes')]
    elif pref == 'openrouter':
        providers = [('openrouter', settings.OPENROUTER_BASE_URL, settings.OPENROUTER_API_KEY, HERMES_MODEL)]
    else:  # auto
        providers = [
            ('hermes',     settings.HERMES_GATEWAY_URL,   settings.HERMES_GATEWAY_TOKEN, 'hermes'),
            ('openrouter', settings.OPENROUTER_BASE_URL,  settings.OPENROUTER_API_KEY,   HERMES_MODEL),
        ]

    for name, url, token, model in providers:
        if not url or not token:
            continue
        result = _chat(url, token, prompt, system=system, model=model,
                       max_tokens=max_tokens, temperature=temperature)
        if result is not None:
            if _is_capacity_response(result):
                logger.warning(f"{name} returned capacity/rate-limit; trying next provider")
                continue
            logger.info(f"AI response via {name}")
            return result

    # ── Netcup Ollama last-resort fallback ────────────────────────────────────
    if HERMES_FALLBACK_ENABLED and model_source != 'hermes':
        logger.warning("All primary providers failed — triggering Netcup Ollama fallback")
        full_prompt = f"{system}\n\n{prompt}".strip() if system else prompt
        fb = run_ollama_fallback(full_prompt)
        if fb['success']:
            logger.info("AI response via netcup_ollama (fallback)")
            return fb['response']
        logger.error("Netcup Ollama fallback also failed: %s", fb['error'])

    raise RuntimeError(
        "All AI providers failed or are unconfigured. "
        "Check HERMES_GATEWAY_TOKEN / OPENROUTER_API_KEY in .env. "
        "Verify SSH tunnel for Netcup fallback: "
        "ssh -N -L 11555:localhost:11434 root@v2202604354135454731.luckysrv.de"
    )


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.DEBUG)
    settings.validate()
    try:
        reply = complete("Say hello in one sentence.", temperature=0.1)
        print(f"AI response: {reply}")
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
