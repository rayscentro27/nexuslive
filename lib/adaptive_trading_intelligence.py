from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"
MARKET_STATE_FILE = STATE_DIR / "market_state_intelligence.json"
LOSS_AUTOPSY_FILE = STATE_DIR / "loss_autopsies.json"
STRATEGY_MEMORY_FILE = STATE_DIR / "strategy_dna_memory.json"
SOURCE_TIERS_FILE = STATE_DIR / "strategy_source_tiers.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def classify_market_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    trend = float(snapshot.get("trend_strength") or 0.0)
    vol = float(snapshot.get("volatility") or 0.0)
    liq = float(snapshot.get("liquidity") or 0.0)
    momentum = float(snapshot.get("momentum") or 0.0)
    fakeout = float(snapshot.get("fakeout_risk") or 0.0)
    news = bool(snapshot.get("news_instability", False))
    session = str(snapshot.get("session") or "unknown")

    state = "ranging"
    if news:
        state = "news-driven instability"
    elif fakeout >= 0.75:
        state = "choppy/no-trade environment"
    elif trend >= 0.7 and momentum >= 0.6:
        state = "trend continuation environment"
    elif trend >= 0.6 and vol >= 0.65:
        state = "breakout"
    elif trend <= 0.35 and vol <= 0.45:
        state = "low volatility"
    elif vol >= 0.8:
        state = "high volatility"
    elif trend <= 0.4 and momentum < 0.5:
        state = "mean reversion environment"

    suitability = "no_trade" if state in {"news-driven instability", "choppy/no-trade environment"} else "selective"
    confidence = max(0.0, min(1.0, (trend * 0.35) + (momentum * 0.2) + (liq * 0.2) + ((1 - fakeout) * 0.25)))
    result = {
        "state": state,
        "confidence": round(confidence, 4),
        "volatility": vol,
        "liquidity_conditions": liq,
        "session": session,
        "momentum": momentum,
        "trend_structure": trend,
        "fakeout_risk": fakeout,
        "trade_suitability": suitability,
        "updated_at": _now(),
    }
    _write_json(MARKET_STATE_FILE, result)
    return result


def adaptive_strategy_confidence(strategy: dict[str, Any], market_state: dict[str, Any], perf: dict[str, Any]) -> dict[str, Any]:
    base = float(strategy.get("base_confidence") or 0.5)
    state_fit = 1.0 if str(market_state.get("state") or "") in (strategy.get("market_state_fit") or []) else 0.7
    vol_fit = 1.0 - abs(float(strategy.get("volatility_target") or 0.5) - float(market_state.get("volatility") or 0.5))
    drawdown_penalty = min(0.35, max(0.0, float(perf.get("drawdown") or 0.0) / 10.0))
    fakeout_penalty = min(0.25, max(0.0, float(perf.get("fakeout_frequency") or 0.0)))
    score = (base * 0.45) + (state_fit * 0.2) + (vol_fit * 0.15) + (float(perf.get("stability") or 0.5) * 0.2)
    score = max(0.0, min(1.0, score - drawdown_penalty - fakeout_penalty))
    return {
        "strategy": strategy.get("name") or "unknown",
        "adaptive_confidence": round(score, 4),
        "state_fit": round(state_fit, 4),
        "drawdown_penalty": round(drawdown_penalty, 4),
        "fakeout_penalty": round(fakeout_penalty, 4),
        "explain": "Confidence adapts to market state fit, volatility fit, and recent stability while penalizing drawdown/fakeouts.",
    }


def no_trade_decision(market_state: dict[str, Any], behavior: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if str(market_state.get("state") or "") in {"news-driven instability", "choppy/no-trade environment"}:
        reasons.append("market state is no-trade")
    if float(market_state.get("fakeout_risk") or 0.0) >= 0.75:
        reasons.append("fakeout risk elevated")
    if float(market_state.get("liquidity_conditions") or 1.0) <= 0.3:
        reasons.append("low liquidity")
    if float(behavior.get("overtrading_score") or 0.0) >= 0.7:
        reasons.append("overtrading pattern detected")
    if float(behavior.get("revenge_score") or 0.0) >= 0.6:
        reasons.append("revenge-trading condition detected")
    return {
        "no_trade": len(reasons) > 0,
        "reasons": reasons,
        "discipline_quality": "high" if len(reasons) > 0 else "monitor",
        "avoided_drawdown_estimate": round(float(behavior.get("risk_if_traded") or 0.0), 2) if reasons else 0.0,
    }


def record_loss_autopsy(payload: dict[str, Any]) -> dict[str, Any]:
    rows = _read_json(LOSS_AUTOPSY_FILE, [])
    entry = {
        "created_at": _now(),
        "strategy_used": payload.get("strategy_used"),
        "market_state": payload.get("market_state"),
        "entry_reason": payload.get("entry_reason"),
        "confidence_reason": payload.get("confidence_reason"),
        "failure_reason": payload.get("failure_reason"),
        "missed_condition": payload.get("missed_condition"),
        "fakeout_involvement": bool(payload.get("fakeout_involvement", False)),
        "volatility_issue": payload.get("volatility_issue"),
        "timing_issue": payload.get("timing_issue"),
        "behavioral_issue": payload.get("behavioral_issue"),
        "drawdown_impact": float(payload.get("drawdown_impact") or 0.0),
        "should_have_avoided": bool(payload.get("should_have_avoided", False)),
        "lesson_learned": payload.get("lesson_learned") or "Tighten condition filters before next attempt.",
    }
    rows.append(entry)
    _write_json(LOSS_AUTOPSY_FILE, rows[-500:])
    return entry


def market_personality_profile(asset: str) -> dict[str, Any]:
    a = asset.upper()
    if a.startswith("BTC") or a.startswith("ETH"):
        return {"asset": asset, "volatility_behavior": "high", "liquidity_behavior": "medium-high", "session_sensitivity": "lower", "fakeout_tendency": "high", "trend_persistence": "medium", "news_sensitivity": "high", "momentum_personality": "impulsive", "reversal_behavior": "sharp"}
    if a in {"EURUSD", "GBPUSD", "USDJPY"}:
        return {"asset": asset, "volatility_behavior": "medium", "liquidity_behavior": "high", "session_sensitivity": "high", "fakeout_tendency": "medium", "trend_persistence": "medium", "news_sensitivity": "medium-high", "momentum_personality": "structured", "reversal_behavior": "moderate"}
    return {"asset": asset, "volatility_behavior": "variable", "liquidity_behavior": "variable", "session_sensitivity": "medium", "fakeout_tendency": "medium", "trend_persistence": "medium", "news_sensitivity": "medium", "momentum_personality": "mixed", "reversal_behavior": "mixed"}


def mutate_strategies(parent_a: dict[str, Any], parent_b: dict[str, Any], parent_c: dict[str, Any]) -> dict[str, Any]:
    mutation = {
        "name": f"mut_{parent_a.get('name','A')}_{parent_b.get('name','B')}_{parent_c.get('name','C')}",
        "entry_logic": parent_a.get("entry_logic") or parent_a.get("entry_trigger"),
        "volatility_filter": parent_b.get("volatility_filter") or "medium-volatility-only",
        "fakeout_filter": parent_c.get("fakeout_filter") or "wait_confirmation_close",
        "session_filter": parent_b.get("session_filter") or "london_newyork_overlap",
        "risk_rule": "max_1_percent_and_required_sl_tp",
        "status": "testing",
        "safety": {
            "blind_deploy": False,
            "requires_demo_validation": True,
            "requires_human_review": True,
        },
        "created_at": _now(),
    }
    rows = _read_json(STRATEGY_MEMORY_FILE, [])
    rows.append(mutation)
    _write_json(STRATEGY_MEMORY_FILE, rows[-500:])
    return mutation


def source_tier(source_name: str, metrics: dict[str, Any]) -> dict[str, Any]:
    discipline = float(metrics.get("risk_discipline") or 0.0)
    clarity = float(metrics.get("clarity") or 0.0)
    consistency = float(metrics.get("consistency") or 0.0)
    educational = float(metrics.get("educational_value") or 0.0)
    score = (discipline * 0.35) + (clarity * 0.25) + (consistency * 0.25) + (educational * 0.15)
    tier = "C"
    if score >= 0.78:
        tier = "A"
    elif score >= 0.58:
        tier = "B"
    rows = _read_json(SOURCE_TIERS_FILE, [])
    rows.append({"source": source_name, "tier": tier, "score": round(score, 4), "metrics": metrics, "updated_at": _now()})
    _write_json(SOURCE_TIERS_FILE, rows[-500:])
    return {"source": source_name, "tier": tier, "score": round(score, 4)}


def trading_intelligence_summary() -> dict[str, Any]:
    state = _read_json(MARKET_STATE_FILE, {})
    autopsies = _read_json(LOSS_AUTOPSY_FILE, [])
    tiers = _read_json(SOURCE_TIERS_FILE, [])
    mutations = _read_json(STRATEGY_MEMORY_FILE, [])
    latest_loss = autopsies[-1] if autopsies else {}
    return {
        "market_state": state,
        "loss_autopsy_count": len(autopsies),
        "last_loss_lesson": latest_loss.get("lesson_learned"),
        "hall_of_fame_hint": "Only Tier A sources and stable demo performance influence promotion.",
        "source_tier_counts": {
            "A": len([r for r in tiers if r.get("tier") == "A"]),
            "B": len([r for r in tiers if r.get("tier") == "B"]),
            "C": len([r for r in tiers if r.get("tier") == "C"]),
        },
        "strategy_mutations_testing": len([m for m in mutations if m.get("status") == "testing"]),
        "demo_only_label": "DEMO / PAPER TRADING ONLY",
    }
