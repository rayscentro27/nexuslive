#!/usr/bin/env python3
"""
nexus_headroom_status.py — read-only cost / rate-limit awareness (headroom-style).

A local, free adapter inspired by the "headroom" tool idea: summarizes which AI
providers Nexus is configured to use, their cost tier, and recommends cheap-first
routing — WITHOUT calling any paid provider. No keys printed, no network calls to
paid APIs. Pure read of the local provider registry + routing rules.

SAFETY: read-only. No paid API calls. No secrets printed (env-var names only).
"""
from __future__ import annotations
import os, json, requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def creds():
    u = os.environ.get("SUPABASE_URL"); k = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not (u and k):
        for line in (ROOT/".env").read_text(errors="ignore").splitlines():
            if line.startswith("SUPABASE_URL=") and not u: u=line.split("=",1)[1].strip().strip('"')
            if line.startswith("SUPABASE_SERVICE_ROLE_KEY=") and not k: k=line.split("=",1)[1].strip().strip('"')
    return u, k

def main():
    u, k = creds()
    h = {"apikey": k, "Authorization": f"Bearer {k}"}
    order = {"free":0,"low":1,"medium":2,"high":3}
    providers = []
    try:
        resp = requests.get(f"{u}/rest/v1/model_providers", headers=h,
            params={"select":"name,cost_tier,is_healthy,priority"}, timeout=20).json()
        providers = [p for p in resp if isinstance(p, dict)] if isinstance(resp, list) else []
        if not providers and resp:
            print("(model_providers returned no usable rows)")
    except Exception as e:
        print("(could not read model_providers:", str(e)[:80], ")")
    ranked = sorted(providers, key=lambda p:(order.get(p.get("cost_tier") or "",9), p.get("priority") or 99))
    print("=== Nexus cost / rate-limit status (headroom-style, read-only) ===")
    print(f"providers configured: {len(providers)}")
    for p in ranked:
        flag = "" if p.get("is_healthy") is not False else "  (unhealthy)"
        print(f"  {p.get('name'):16} cost={p.get('cost_tier') or '?':6} priority={p.get('priority')}{flag}")
    # env-var NAMES only (presence)
    names = [n for n in os.environ if any(x in n for x in ("OPENROUTER","GROQ","GEMINI","OLLAMA","NVIDIA","COHERE")) and "KEY" in n or n in ("OLLAMA_URL",)]
    print("\nprovider key env-vars present (names only):", sorted(set(names)) or "(none in shell env)")
    cheapest = ranked[0]["name"] if ranked else "Ollama (local)"
    print("\nRecommended routing (cheap-first):")
    print(f"  • cheap classification / short tasks  -> {cheapest} (local/free preferred: Ollama)")
    print("  • fast small tasks                    -> Groq (low) if configured")
    print("  • coding                              -> Claude / Codex / OpenCode")
    print("  • high reasoning                      -> Hermes gateway / selected provider")
    print("\ncost_approval_needed: only for paid providers (medium/high tier). Local Ollama = no approval.")
    print("No paid API calls were made. No secrets printed.")

if __name__ == "__main__":
    main()
