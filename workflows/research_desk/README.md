# Phase 6 — Nexus Research Desk

> **RESEARCH ONLY — No live trading. No broker execution. No order placement.**

## Purpose

The Research Desk synthesizes outputs from Phases 3–5 into actionable research intelligence:
- Clusters related research artifacts and claims into themes
- Generates novel trading hypotheses from patterns
- Detects coverage gaps in research and strategy data
- Produces concise research briefs for human review

## Input Sources

| Table | Used For |
|---|---|
| `research_artifacts` | Source material for clustering |
| `research_claims` | Supporting evidence |
| `strategy_library` | Strategy link validation |
| `strategy_performance` | Strategy effectiveness context |
| `options_strategy_performance` | Options context |
| `agent_scorecards` | AI agent performance snapshot |
| `replay_results` | Outcome data for hypothesis generation |
| `confidence_calibration` | Calibration gap detection |
| `strategy_optimizations` | Optimization signal for hypotheses |
| `strategy_variants` | Variant context |

## Output Tables (apply SQL docs before first run)

| Table | Purpose |
|---|---|
| `research_clusters` | Themed research groups |
| `research_hypotheses` | Generated hypotheses |
| `coverage_gaps` | Detected research gaps |
| `research_briefs` | Concise summaries |

## Run Commands

```bash
cd ~/nexus-ai/workflows/research_desk

# Full pipeline once
node research_desk_runner.js --once

# Full pipeline, limit input to 20 artifacts
node research_desk_runner.js --limit 20

# Briefs only
node research_desk_runner.js --briefs

# Gap detection only
node research_desk_runner.js --gaps

# Hypotheses only
node research_desk_runner.js --hypotheses
```

## Clustering Workflow

Artifacts and claims are matched against theme keywords:
- `breakout_behavior` — breakout, momentum, range break
- `spread_sensitivity` — spread, bid/ask, slippage
- `iv_crush` — IV crush, implied volatility, expiry
- `mean_reversion` — mean reversion, revert, oversold, overbought
- `trend_continuation` — trend, continuation, follow-through
- `covered_call_stability` — covered call, wheel, premium
- `options_structure_weakness` — options structure, legs, risk reversal
- `confidence_calibration_issue` — confidence, calibration, accuracy
- `risk_threshold_adjustment` — risk threshold, approval, penalty
- `volatility_regime` — volatility, VIX, regime

## Hypothesis Generation

Hypotheses are generated from:
1. Research clusters with >= 1 source
2. Confidence calibration bands with gap > 0.2
3. Optimization suggestions with improvement_score >= 30
4. Replay result extremes (100% win or 100% loss rates)

Each hypothesis is scored on:
- `novelty_score` — how new/unexplored the idea is
- `plausibility_score` — how likely it is to be valid
- `priority_score` — composite priority for human review

## Coverage Gap Detection

Gaps detected automatically:
- No options hypotheses generated
- Weak confidence calibration (gap > 0.3)
- No replay data available
- Low scorecard coverage (< 5 scorecards)
- No optimization data
- Underresearched themes (< 2 sources)

## Validation SQL

```sql
-- Research clusters
SELECT cluster_name, theme, source_count, confidence FROM public.research_clusters ORDER BY created_at DESC;

-- Hypotheses by priority
SELECT hypothesis_title, asset_type, priority_score, status FROM public.research_hypotheses ORDER BY priority_score DESC LIMIT 10;

-- Coverage gaps
SELECT gap_type, severity, description FROM public.coverage_gaps ORDER BY severity DESC;

-- Research briefs
SELECT title, brief_type, priority FROM public.research_briefs ORDER BY priority DESC;
```

## Safety Statement

This lab performs **research and analysis only**.
- No live trading
- No broker execution
- No order placement
- No OANDA API calls
- No Webull API calls
- All outputs require human review before any action
