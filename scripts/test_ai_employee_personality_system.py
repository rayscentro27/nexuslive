#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.ai_employee_prompt_loader import (
    get_employee_decision_framework,
    get_employee_prompt,
    get_employee_voice,
)
from lib.ai_employee_registry import get_role, list_roles, role_routing_preview
from lib.ai_employee_knowledge_router import route_query
from lib.strategy_intelligence import extract_strategy_dna, promotion_decision, strategy_record


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    prompt = get_employee_prompt("trading_analyst")
    ok &= check("prompt loader returns Sage prompt", "Sage" in prompt or "trading" in prompt.lower())
    ok &= check("voice loader returns value", bool(get_employee_voice("hermes")))
    ok &= check("decision framework returns value", bool(get_employee_decision_framework("hermes")))

    ok &= check("registry list_roles shape", isinstance(list_roles(), list) and len(list_roles()) >= 8)
    ok &= check("registry get_role works", get_role("hermes") is not None)
    ok &= check("routing preview shape", isinstance(role_routing_preview(), list) and len(role_routing_preview()) >= 8)

    # Supabase-first routing smoke: should return structured result without exceptions
    routed = route_query("system_monitor", "provider latency")
    ok &= check("router result has confidence", isinstance(getattr(routed, "confidence", None), int))

    dna = extract_strategy_dna({"setup_name": "London Breakout", "market_type": "forex", "entry_trigger": "range break"})
    ok &= check("strategy DNA extraction", dna.get("setup_name") == "London Breakout" and bool(dna.get("failure_pattern")))

    rec = strategy_record({
        "category": "forex",
        "setup_name": "London Breakout",
        "paper_trading_results": {"win_rate": 62, "max_drawdown": 2.1, "avg_rr": 1.8, "repeatable_setup": True},
    })
    decision = promotion_decision(rec)
    ok &= check("hall of fame decision path", decision.get("promotion_status") in {"hall_of_fame", "watchlist"})

    # Tone guardrails
    unsafe_terms = ["guaranteed approval", "guaranteed profit", "risk free"]
    ok &= check("unsafe promise terms absent from Hermes prompt", not any(t in get_employee_prompt("hermes").lower() for t in unsafe_terms))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
