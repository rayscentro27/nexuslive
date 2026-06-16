"""
Hermes Mobile — local provider adapter (READ-ONLY, local-only).

Wires the conversational bot to a LOCAL model backend only:
  - Ollama at OLLAMA_HOST (default http://localhost:11434)  [preferred: no key]
  - Hermes gateway at HERMES_GATEWAY_URL (default http://localhost:8642) [optional]

Hard rules:
  - Endpoint MUST be localhost / loopback / private LAN. External URLs are BLOCKED
    unless HERMES_MOBILE_ALLOW_EXTERNAL=true (Ray-only override).
  - Paid providers (OpenAI/Anthropic/OpenRouter) are NOT used here. We never read
    or send paid API keys from this module.
  - Cloud-routed Ollama models (name ends with '-cloud') are skipped.
  - If the backend is offline/slow, we return a deterministic fallback (no error).
  - We log provider STATUS only — never prompt contents or secrets.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "proof_automation" / "hermes_mobile_provider.log"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
GATEWAY_URL = os.environ.get("HERMES_GATEWAY_URL", "http://localhost:8642").rstrip("/")
# Prefer the smallest/fastest LOCAL model (CPU-only box); never a *-cloud model.
# Override with HERMES_MOBILE_MODEL.
MODEL = os.environ.get("HERMES_MOBILE_MODEL", "qwen2.5:0.5b")
TIMEOUT = float(os.environ.get("HERMES_MOBILE_TIMEOUT", "60"))
ALLOW_EXTERNAL = os.environ.get("HERMES_MOBILE_ALLOW_EXTERNAL", "false").lower() == "true"

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "::1")
_PRIVATE_PREFIXES = ("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.",
                     "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
                     "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")


def _log(event: str, **fields) -> None:
    """Append a status line. NEVER logs prompt text or secrets."""
    safe = {k: v for k, v in fields.items() if k not in ("prompt", "context", "key", "token", "reply")}
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as fh:
            fh.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(),
                                 "event": event, **safe}) + "\n")
    except Exception:
        pass


def validate_provider_is_local(url: str) -> tuple[bool, str]:
    """True only for loopback / private-LAN endpoints (unless explicitly allowed)."""
    m = re.match(r"^https?://([^:/]+)", url or "")
    host = m.group(1) if m else ""
    if host in _LOCAL_HOSTS or host.endswith(".local"):
        return True, "local"
    if any(host.startswith(p) for p in _PRIVATE_PREFIXES):
        return True, "private_lan"
    if ALLOW_EXTERNAL:
        return True, "external_explicitly_allowed"
    return False, f"blocked_external_host:{host or 'unknown'}"


def _http_json(url: str, payload: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def provider_status() -> dict:
    """Probe local backends read-only. Returns availability + model, no secrets."""
    status = {"ollama_host": OLLAMA_HOST, "gateway_url": GATEWAY_URL, "model": MODEL,
              "ollama_available": False, "gateway_available": False,
              "local_validated": False, "models": [], "external_allowed": ALLOW_EXTERNAL}
    ok_local, reason = validate_provider_is_local(OLLAMA_HOST)
    status["local_validated"] = ok_local
    status["local_reason"] = reason
    if not ok_local:
        _log("provider_status", local_validated=False, reason=reason)
        return status
    # Ollama tags (read-only)
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            tags = json.loads(resp.read().decode())
        names = [m.get("name") for m in tags.get("models", [])]
        # local-only models (skip *-cloud)
        local_models = [n for n in names if n and not n.endswith("-cloud")]
        status["models"] = local_models
        status["ollama_available"] = bool(local_models)
        if MODEL not in local_models and local_models:
            status["model"] = local_models[0]  # fall back to an available local model
    except Exception as e:
        status["ollama_error"] = str(e)[:80]
    # Gateway health (optional)
    try:
        with urllib.request.urlopen(f"{GATEWAY_URL}/health", timeout=4) as resp:
            status["gateway_available"] = resp.status == 200
    except Exception:
        status["gateway_available"] = False
    _log("provider_status", ollama=status["ollama_available"], gateway=status["gateway_available"],
         model=status["model"], n_models=len(status["models"]))
    return status


def fallback_reply(reason: str = "backend_offline") -> dict:
    """Deterministic, safe reply when no local model is available."""
    return {"text": "", "provider": "fallback", "model": None, "used_fallback": True,
            "reason": reason}


def generate_mobile_reply(prompt: str, context: str = "", mode: str = "read_only") -> dict:
    """Generate a conversational reply from a LOCAL model only. Falls back safely.
    Returns {text, provider, model, used_fallback, reason?}. Never raises on backend failure."""
    if mode != "read_only":
        # This module is read-only by contract; refuse any other mode.
        _log("generate_refused", mode=mode)
        return fallback_reply("non_read_only_mode_refused")
    ok_local, reason = validate_provider_is_local(OLLAMA_HOST)
    if not ok_local:
        _log("generate_blocked", reason=reason)
        return fallback_reply(reason)

    st = provider_status()
    if not st["ollama_available"]:
        return fallback_reply("ollama_unavailable")
    model = st["model"]
    full = (context + "\n\n" + prompt).strip() if context else prompt
    try:
        # Cap prompt size — CPU inference cost scales with tokens. Keep it lean.
        full = full[-3000:]
        out = _http_json(f"{OLLAMA_HOST}/api/generate",
                         {"model": model, "prompt": full, "stream": False,
                          "options": {"temperature": 0.4, "num_predict": 220, "num_ctx": 2048}},
                         timeout=TIMEOUT)
        text = (out.get("response") or "").strip()
        if not text:
            return fallback_reply("empty_response")
        _log("generate_ok", model=model, chars=len(text))
        return {"text": text, "provider": "local_ollama", "model": model, "used_fallback": False}
    except (urllib.error.URLError, TimeoutError, Exception) as e:
        _log("generate_error", err=str(e)[:80])
        return fallback_reply("backend_error")


if __name__ == "__main__":
    print(json.dumps(provider_status(), indent=2))
