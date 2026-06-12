#!/usr/bin/env python3
"""Test the local provider adapter: local-only validation, status probe, and a
real local generation (with safe fallback). No paid APIs, no secrets printed."""
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import hermes_mobile_provider as MP  # noqa: E402


def main() -> int:
    print("=== local-only validation ===")
    for url, expect in [("http://localhost:11434", True), ("http://127.0.0.1:8642", True),
                        ("https://api.openai.com", False), ("http://openrouter.ai", False)]:
        ok, reason = MP.validate_provider_is_local(url)
        flag = "✓" if ok == expect else "✗FAIL"
        print(f"  {flag} {url} -> local={ok} ({reason})")
        assert ok == expect, f"local validation wrong for {url}"

    print("\n=== provider status (local probe) ===")
    st = MP.provider_status()
    print(f"  ollama_available={st['ollama_available']} gateway={st['gateway_available']} "
          f"model={st['model']} local_validated={st['local_validated']} models={st['models']}")
    assert st["local_validated"], "provider must validate as local"

    print("\n=== generation (read-only) ===")
    res = MP.generate_mobile_reply(
        "In one sentence, what should Ray focus on first in Nexus?",
        context="Nexus has credit + funding tracks; credit is strongest.",
        mode="read_only")
    print(f"  provider={res['provider']} model={res.get('model')} used_fallback={res['used_fallback']}")
    print(f"  reply: {(res.get('text') or '(fallback — handled by conversation layer)')[:240]}")

    print("\n=== non-read-only mode is refused ===")
    refused = MP.generate_mobile_reply("x", mode="write")
    assert refused["used_fallback"] and refused["provider"] == "fallback"
    print("  ✓ write mode refused -> fallback")

    print("\n=== secret-scan: log file must not contain prompt/secret material ===")
    log = ROOT / "logs" / "proof_automation" / "hermes_mobile_provider.log"
    if log.exists():
        txt = log.read_text()
        assert "focus on first" not in txt, "prompt content leaked into log"
        print("  ✓ no prompt text in provider log")
    print("\n=== provider test OK ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
