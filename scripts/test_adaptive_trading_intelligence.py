#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.adaptive_trading_intelligence import (
    adaptive_strategy_confidence,
    classify_market_state,
    market_personality_profile,
    mutate_strategies,
    no_trade_decision,
    record_loss_autopsy,
    source_tier,
)
from lib.hermes_supabase_first import nexus_knowledge_reply


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    st = classify_market_state({"trend_strength": 0.75, "volatility": 0.62, "liquidity": 0.7, "session": "new york", "momentum": 0.68, "fakeout_risk": 0.2})
    ok &= check("market state classification", bool(st.get("state")) and "trade_suitability" in st)

    conf = adaptive_strategy_confidence(
        {"name": "Trend Pullback", "base_confidence": 0.65, "market_state_fit": [st.get("state")], "volatility_target": 0.6},
        st,
        {"drawdown": 1.2, "fakeout_frequency": 0.1, "stability": 0.7},
    )
    ok &= check("adaptive confidence logic", float(conf.get("adaptive_confidence") or 0) > 0)

    nt = no_trade_decision({"state": "choppy/no-trade environment", "fakeout_risk": 0.9, "liquidity_conditions": 0.2}, {"overtrading_score": 0.8, "revenge_score": 0.7, "risk_if_traded": 30})
    ok &= check("no-trade logic", nt.get("no_trade") is True and len(nt.get("reasons") or []) >= 1)

    aut = record_loss_autopsy({"strategy_used": "SB", "market_state": "news-driven instability", "drawdown_impact": 1.0, "should_have_avoided": True})
    ok &= check("loss autopsy generation", bool(aut.get("lesson_learned")))

    mp = market_personality_profile("BTCUSD")
    ok &= check("market personality profile", mp.get("asset") == "BTCUSD")

    mut = mutate_strategies({"name": "A", "entry_logic": "x"}, {"name": "B", "volatility_filter": "y"}, {"name": "C", "fakeout_filter": "z"})
    ok &= check("strategy mutation safety", mut.get("safety", {}).get("blind_deploy") is False)

    tier = source_tier("Disciplined Educator", {"risk_discipline": 0.9, "clarity": 0.8, "consistency": 0.8, "educational_value": 0.85})
    ok &= check("source-tier filtering", tier.get("tier") in {"A", "B", "C"})

    cmd = nexus_knowledge_reply("What market state are we in?")
    ok &= check("conversational trading command", isinstance(cmd, str) and len(cmd) > 0)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
