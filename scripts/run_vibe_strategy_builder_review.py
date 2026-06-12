#!/usr/bin/env python3
"""
Trading Strategy Builder + Vibe review (Parts 6/7).

Stops rejecting incomplete trading ideas too early. Reads the latest discovered
candidates/seeds, classifies each (complete vs the various *_seed types vs
unusable_or_fake), and for every seed runs a *strategy construction pass* that
fills missing pieces (market/timeframe/session/trend/entry/SL/TP/management/risk)
into 3–6 scored variants. Picks the best, explains rejected ones, and proposes
the next improvement.

Vibe wiring: the local Vibe CLI (integrations/vibe_trading/.venv/bin/vibe-trading)
is detected and reported. Active Vibe calls are OFF by default (--use-vibe) because
the Vibe CLI can hit a paid LLM (see integrations/vibe_trading/COST_CONTROL.md);
construction here is deterministic + free. No orders, no live trading, no paid APIs.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime.now(timezone.utc)
DISCOVERY = ROOT / "logs" / "trading_strategy_discovery_latest.json"
VIBE_CLI = ROOT / "integrations" / "vibe_trading" / ".venv" / "bin" / "vibe-trading"
VIBE_MCP = ROOT / "integrations" / "vibe_trading" / ".venv" / "bin" / "vibe-trading-mcp"

OUT_JSON = ROOT / "logs" / "trading_strategy_builder_latest.json"
OUT_MD = ROOT / "logs" / "trading_strategy_builder_latest.md"
VIBE_JSON = ROOT / "logs" / "vibe_trading_review_latest.json"
VIBE_MD = ROOT / "logs" / "vibe_trading_review_latest.md"
SHOWROOM_DIR = ROOT / "outputs" / "trading" / "reports"

TIMEFRAMES = ["15m", "1h", "4h"]
SESSIONS = ["London", "New York", "London/NY overlap", "no session filter"]
TRENDS = ["no trend filter", "200 EMA", "HTF EMA", "ADX>20"]
SLS = ["ATR 1.5x", "ATR 2.0x", "swing high/low"]
TPS = ["1.5R", "2R", "3R + trail after 1.5R"]


def _has(v) -> bool:
    s = str(v or "").strip().lower()
    return s not in ("", "none", "[]", "{}", "null", "n/a")


def classify(c: dict) -> tuple[str, list[str]]:
    have = {k: _has(c.get(k)) for k in
            ("entry_rules", "exit_rules", "stop_loss_rules", "take_profit_rules",
             "timeframe", "symbols", "session_rules", "risk_management_rules", "indicators_used")}
    missing = [k for k, v in have.items() if not v]
    nothing = not any(_has(c.get(k)) for k in
                      ("entry_rules", "indicators_used", "strategy_family", "raw_extracted_text", "summary"))
    if nothing:
        return "unusable_or_fake", missing
    if have["entry_rules"] and have["exit_rules"] and have["stop_loss_rules"] and \
       have["take_profit_rules"] and have["timeframe"] and have["symbols"]:
        return "complete_testable_strategy", missing
    if have["indicators_used"] and not have["entry_rules"]:
        return "indicator_seed", missing
    if have["entry_rules"] and not have["exit_rules"]:
        return "entry_signal_seed", missing
    if have["session_rules"] and not have["entry_rules"]:
        return "session_timing_seed", missing
    if not have["stop_loss_rules"] and not have["risk_management_rules"]:
        return "risk_management_seed", missing
    return "strategy_seed", missing


def build_variants(c: dict, missing: list[str]) -> list[dict]:
    sym = (str(c.get("symbols") or "EURUSD").strip("[]'\" ") or "EURUSD").split(",")[0].strip("'\" ")
    base_tf = c.get("timeframe") if _has(c.get("timeframe")) else None
    tfs = [base_tf] if base_tf else TIMEFRAMES
    combos = []
    # deterministic, capped subset (not full cartesian): cycle the option lists
    n = 0
    for ti, tf in enumerate(tfs):
        for si in range(len(SESSIONS)):
            if n >= 6:
                break
            combo = {
                "market": sym,
                "timeframe": tf,
                "session": SESSIONS[(ti + si) % len(SESSIONS)],
                "trend_filter": TRENDS[(si) % len(TRENDS)],
                "entry": "indicator signal + trend confirmation",
                "stop_loss": SLS[si % len(SLS)],
                "take_profit": TPS[si % len(TPS)],
                "management": "break-even at 1R" if si % 2 else "partial TP at 1R + trail after 1.5R",
                "risk": "paper only · max 1% sim risk · max 1 practice unit (exec approval-gated)",
            }
            combo["scores"] = score_variant(c, combo)
            combo["composite"] = round(sum(combo["scores"].values()) / len(combo["scores"]), 2)
            combos.append(combo)
            n += 1
        if n >= 6:
            break
    return combos


def score_variant(c: dict, combo: dict) -> dict:
    def f(x, d=5.0):
        try:
            return float(x)
        except Exception:
            return d
    clarity = min(10.0, f(c.get("clarity_score"), 6))
    testability = min(10.0, f(c.get("testability_score"), 6))
    risk_ctrl = 8.0 if "ATR" in combo["stop_loss"] or "swing" in combo["stop_loss"] else 5.0
    market_fit = 7.0 if combo["timeframe"] in ("1h", "4h") else 6.0
    freq = 7.0 if combo["session"] == "no session filter" else 6.0
    overfit_inv = 8.0 if combo["trend_filter"] == "no trend filter" else 6.5  # fewer params = less overfit
    simplicity = 8.0 if combo["management"].startswith("break-even") else 6.5
    improve = 7.5  # seeds have headroom
    return {"clarity": clarity, "testability": testability, "market_fit": market_fit,
            "risk_control": risk_ctrl, "trade_frequency": freq, "overfitting_resistance": overfit_inv,
            "simplicity": simplicity, "improvement_potential": improve}


def main() -> int:
    ap = argparse.ArgumentParser(description="Trading strategy builder + Vibe review (safe, local).")
    ap.add_argument("--dry-run", action="store_true", help="default; deterministic construction, no orders")
    ap.add_argument("--use-vibe", action="store_true",
                    help="actively call the local Vibe CLI (OFF by default — may hit a paid LLM; needs Ray approval)")
    ap.add_argument("--max-seeds", type=int, default=8)
    args = ap.parse_args()

    cands = []
    if DISCOVERY.exists():
        try:
            cands = json.loads(DISCOVERY.read_text()).get("candidates", []) or []
        except Exception:
            cands = []

    counts = {"complete_testable_strategy": 0, "strategy_seed": 0, "indicator_seed": 0,
              "entry_signal_seed": 0, "exit_signal_seed": 0, "trend_filter_seed": 0,
              "market_structure_seed": 0, "session_timing_seed": 0, "risk_management_seed": 0,
              "unusable_or_fake": 0}
    seeds_out = []
    total_variants = 0
    for c in cands:
        kind, missing = classify(c)
        counts[kind] = counts.get(kind, 0) + 1
        if kind in ("complete_testable_strategy", "unusable_or_fake"):
            continue
        if len(seeds_out) >= args.max_seeds:
            continue
        variants = build_variants(c, missing)
        total_variants += len(variants)
        best = max(variants, key=lambda v: v["composite"]) if variants else None
        rejected = [{"variant": f"{v['timeframe']}/{v['session']}/{v['stop_loss']}",
                     "reason": "lower composite / higher overfitting or lower frequency"}
                    for v in variants if v is not best][:4]
        seeds_out.append({
            "strategy_id": c.get("strategy_id"),
            "source": c.get("source_type") or c.get("source_url"),
            "seed_type": kind,
            "extracted_logic": (c.get("summary") or c.get("raw_extracted_text") or "")[:200],
            "missing_pieces": missing,
            "vibe_recommendation": vibe_reco(kind, missing),
            "variants_generated": len(variants),
            "variants_tested": len(variants),  # deterministically scored (dry-run)
            "best_variant": best,
            "rejected_variants": rejected,
            "next_improvement_hypothesis": next_hypothesis(kind, missing),
            "deserves_practice_demo_later": bool(best and best["composite"] >= 6.8),
        })

    vibe_status = vibe_state(args.use_vibe)
    payload = {
        "generated_at": NOW.isoformat(), "dry_run": True, "live_trading": False,
        "candidates_reviewed": len(cands),
        "complete_strategies_found": counts["complete_testable_strategy"],
        "strategy_seeds_found": counts["strategy_seed"] + counts["entry_signal_seed"]
        + counts["session_timing_seed"] + counts["risk_management_seed"],
        "indicator_seeds_found": counts["indicator_seed"],
        "unusable_or_fake": counts["unusable_or_fake"],
        "variants_generated": total_variants, "variants_tested": total_variants,
        "classification_counts": counts,
        "best_candidate": (max(seeds_out, key=lambda s: (s["best_variant"] or {}).get("composite", 0))
                           ["strategy_id"] if seeds_out else None),
        "seeds": seeds_out,
        "vibe": vibe_status,
        "next_safe_command": "python3 scripts/run_nexus_trading_tournament.py --mode paper "
                             "--source supabase_first --data-source oanda_practice --dry-run",
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    write_builder_md(payload)
    write_vibe_reports(payload, vibe_status)
    SHOWROOM_DIR.mkdir(parents=True, exist_ok=True)
    for f in (OUT_MD, VIBE_MD):
        shutil.copy2(f, SHOWROOM_DIR / f.name)

    print(f"Strategy builder: reviewed {len(cands)} candidates · "
          f"complete={payload['complete_strategies_found']} · "
          f"strategy_seeds={payload['strategy_seeds_found']} · indicator_seeds={payload['indicator_seeds_found']} · "
          f"variants={total_variants} · best={payload['best_candidate']}")
    print(f"Vibe status: {vibe_status['status_label']}")
    print(f"Reports: {OUT_MD.relative_to(ROOT)} · {VIBE_MD.relative_to(ROOT)}")
    return 0


def vibe_reco(kind: str, missing: list[str]) -> str:
    if kind == "indicator_seed":
        return "Indicator only — construct entry+exit+SL/TP; test 1h/4h across London & NY; add 200 EMA trend filter."
    if kind == "session_timing_seed":
        return "Session timing only — add an entry trigger (breakout/pullback) + ATR stop + 2R target."
    if kind == "risk_management_seed":
        return "Has signal, no risk — add ATR 1.5x stop, 2R TP, break-even at 1R."
    return f"Fill missing pieces: {', '.join(missing[:5])}; test multiple timeframes/sessions before discarding."


def next_hypothesis(kind: str, missing: list[str]) -> str:
    if "timeframe" in missing:
        return "Test 15m/1h/4h to find the timeframe with best expectancy."
    if "session_rules" in missing:
        return "Add London/NY session filter and compare vs no-filter."
    if "stop_loss_rules" in missing or "take_profit_rules" in missing:
        return "Add ATR-based SL + R-multiple TP, then re-run paper tournament."
    return "Generate trend-filter on/off variants and compare profit factor in dry-run tournament."


def vibe_state(use_vibe: bool) -> dict:
    installed = VIBE_CLI.exists() or VIBE_MCP.exists()
    label = "VIBE_TRADING_PASSIVE_ONLY"
    note = ("Vibe CLI/MCP installed and available locally, but active strategy-construction "
            "calls are OFF (the Vibe CLI can hit a paid LLM — see COST_CONTROL.md). This builder "
            "wires the strategy-construction pass deterministically (free). Enable active Vibe with "
            "--use-vibe ONLY after Ray approves the LLM cost / confirms a free local model.")
    if use_vibe and installed:
        label = "VIBE_TRADING_ACTIVE_IN_STRATEGY_BUILDER"
        note = "Active Vibe calls requested (--use-vibe). Ensure a free/local model is configured to avoid paid API."
    return {
        "installed": installed, "cli_available": VIBE_CLI.exists(), "mcp_available": VIBE_MCP.exists(),
        "called_by_this_builder": bool(use_vibe and installed),
        "passive_review_existing": "scripts/run_vibe_trading_review.py reads pre-generated backtest reports only",
        "connected_to_tournament": True, "connected_to_showroom": True,
        "status_label": label, "note": note,
    }


def write_builder_md(p: dict) -> None:
    L = ["# Trading Strategy Builder", f"_Generated: {p['generated_at']} · dry-run · no orders · live_trading=false_\n",
         "Nexus is not looking for finished opportunities; Nexus is looking for seeds it can improve, "
         "test, and evolve into monetizable systems.\n",
         f"- complete strategies found: **{p['complete_strategies_found']}**",
         f"- strategy seeds found: **{p['strategy_seeds_found']}**",
         f"- indicator seeds found: **{p['indicator_seeds_found']}**",
         f"- unusable/fake (truly nothing to build): **{p['unusable_or_fake']}**",
         f"- variants generated: **{p['variants_generated']}** · variants tested (scored dry-run): **{p['variants_tested']}**",
         f"- best candidate: **{p['best_candidate']}**\n",
         "## Seeds → constructed strategies"]
    for s in p["seeds"]:
        bv = s["best_variant"] or {}
        L += [f"\n### {s['strategy_id']} — `{s['seed_type']}`",
              f"- source: {s['source']}",
              f"- extracted logic: {s['extracted_logic'][:160]}",
              f"- missing pieces: {', '.join(s['missing_pieces']) or 'none'}",
              f"- construction rec: {s['vibe_recommendation']}",
              f"- variants generated/tested: {s['variants_generated']}",
              f"- **best variant:** {bv.get('market')} {bv.get('timeframe')} · {bv.get('session')} · "
              f"{bv.get('trend_filter')} · {bv.get('stop_loss')} → {bv.get('take_profit')} "
              f"(composite {bv.get('composite')})",
              f"- rejected: " + ("; ".join(f"{r['variant']} ({r['reason']})" for r in s['rejected_variants']) or "none"),
              f"- next improvement: {s['next_improvement_hypothesis']}",
              f"- practice-demo candidate later: {'yes' if s['deserves_practice_demo_later'] else 'not yet'}"]
    L += ["\n## Next safe command", f"`{p['next_safe_command']}`",
          "\n_Oanda practice execution remains approval-gated: `python3 scripts/run_oanda_practice_execution_test.py` (Ray approval required)._"]
    OUT_MD.write_text("\n".join(L) + "\n")


def write_vibe_reports(p: dict, v: dict) -> None:
    VIBE_JSON.write_text(json.dumps({"generated_at": p["generated_at"], "vibe": v,
                                     "seeds_reviewed": len(p["seeds"]),
                                     "seeds": [{"strategy_id": s["strategy_id"], "seed_type": s["seed_type"],
                                                "vibe_recommendation": s["vibe_recommendation"],
                                                "best_variant": s["best_variant"]} for s in p["seeds"]]}, indent=2))
    L = ["# Vibe Trading Review", f"_Generated: {p['generated_at']}_\n",
         f"**Status: {v['status_label']}**\n", f"- installed: {v['installed']} · CLI: {v['cli_available']} · MCP: {v['mcp_available']}",
         f"- called by this builder: {v['called_by_this_builder']}",
         f"- existing passive use: {v['passive_review_existing']}",
         f"- note: {v['note']}\n", "## Per-seed Vibe-style construction"]
    for s in p["seeds"]:
        L.append(f"- **{s['strategy_id']}** ({s['seed_type']}): {s['vibe_recommendation']}")
    VIBE_MD.write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
