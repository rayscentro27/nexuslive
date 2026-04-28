"""
db/ai_client.py — Unified AI gateway client.

Tries Hermes first (local, fast), falls back to Hermes.
Both expose an OpenAI-compatible /v1/chat/completions endpoint.
"""
import logging
import os
import requests
from typing import Optional
from urllib.parse import urlparse

from config import settings

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
             temperature: float = 0.3, provider: Optional[str] = None) -> str:
    """
    Generate a completion. Uses AI_PROVIDER setting
    ('hermes', 'openrouter', 'hermes', 'auto').
    Raises RuntimeError if all providers fail.
    """
    pref = provider or settings.AI_PROVIDER

    providers = []
    if pref == 'hermes':
        providers = [('hermes', settings.HERMES_GATEWAY_URL, settings.HERMES_GATEWAY_TOKEN, 'hermes')]
    elif pref == 'openrouter':
        providers = [('openrouter', settings.OPENROUTER_BASE_URL, settings.OPENROUTER_API_KEY, HERMES_MODEL)]
    elif pref == 'hermes':
        providers = [('hermes', settings.HERMES_GATEWAY_URL, settings.HERMES_GATEWAY_TOKEN, HERMES_MODEL)]
    else:  # auto
        providers = [
            ('hermes',   settings.HERMES_GATEWAY_URL,  settings.HERMES_GATEWAY_TOKEN,   'hermes'),
            ('openrouter', settings.OPENROUTER_BASE_URL, settings.OPENROUTER_API_KEY,   HERMES_MODEL),
            ('hermes', settings.HERMES_GATEWAY_URL,         settings.HERMES_GATEWAY_TOKEN,    HERMES_MODEL),
        ]

    for name, url, token, model in providers:
        if not url or not token:
            continue
        result = _chat(url, token, prompt, system=system, model=model,
                       max_tokens=max_tokens, temperature=temperature)
        if result is not None:
            if _is_capacity_response(result):
                logger.warning(f"AI provider {name} returned capacity/rate-limit response; trying next provider")
                continue
            logger.debug(f"AI response via {name}")
            return result

    raise RuntimeError("All AI providers failed or are unconfigured. "
                       "Check HERMES_GATEWAY_TOKEN / OPENROUTER_API_KEY / HERMES_GATEWAY_TOKEN in .env")


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
