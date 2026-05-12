# Hermes Trading Intelligence — Report
**Date:** 2026-05-12 | **Pass:** Trading Demo Platform

## Overview
Extended Hermes internal-first routing system with a full trading analyst capability covering 7 query intents.

## New Keywords Added (hermes_runtime_config.py)
```
trading:
  paper results, paper performance, how did paper
  best session, best time to trade, session performance, when to trade
  active strategy, what strategy, which strategy, strategy running
  is demo safe, is paper safe, safety status
  why paused, why halted, why stopped, what paused
  why is trading paused, why is trading halted, is trading paused
```

## Query Intent Routing (hermes_internal_first.py)

### 1. Paper Results (`is_results_query`)
Reads `nexus-strategy-lab/reports/paper_journal_summary.json` if present; reports total trades, win rate, profit factor, current balance. Falls back to instructional text when no journal exists yet.

### 2. Best Session (`is_session_query`)
Reads `nexus-strategy-lab/reports/session_analysis.json` if present. Falls back to static knowledge: London + Overlap best, Asia worst. Advises pausing Asia-session entries.

### 3. Safety Check (`is_safe_query`)
Reports all 5 safety dimensions:
- NEXUS_DRY_RUN
- LIVE_TRADING
- TRADING_LIVE_EXECUTION_ENABLED
- NEXUS_AUTO_TRADING
- Circuit breaker count
Returns ✅ or ⚠️ verdict.

### 4. Paused Reason (`is_paused_query`)
Calls circuit_breaker.get_status() and names active breakers. Instructs operator on reset path. If no breakers: "Trading is not paused."

### 5. Active Strategy (`is_strategy_query`)
Reports no live execution (dry run), names available platform components, lists 3 approved paper strategies, explains activation path via StrategyApproval UI.

### 6. Generic Trading Status (fallthrough)
Lists platform phase (Phase 2: Paper Trading), all safety flags, all components built, and invites follow-up queries.

## Test Results
```
[PASS] 'trading status' → trading topic
[PASS] 'show me paper results' → trading topic
[PASS] 'what is the best session to trade' → trading topic
[PASS] 'is demo safe' → trading topic (contains NEXUS_DRY_RUN)
[PASS] 'why is trading paused' → trading topic
[PASS] 'what is the active strategy' → trading topic
[PASS] 'circuit breaker status' → circuit_breaker topic
[PASS] 'what is the weather today' → None (fallthrough)
```
All 8 routing tests pass.
