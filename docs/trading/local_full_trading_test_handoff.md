# Local Full Trading Test Handoff

Run these outside the Codex sandbox from `/Users/raymonddavis/nexus-ai`.

Safety must stay locked:

- `LIVE_TRADING=false`
- `PAPER_ONLY=true`
- `DRY_RUN=true` unless intentionally using `--execute`
- Oanda must remain `practice/demo` only
- Max Oanda units: `1`

## Fast Path

Default safe gate:

```bash
./scripts/run_local_full_trading_test_handoff.sh
```

Run through dry-run:

```bash
./scripts/run_local_full_trading_test_handoff.sh --dry-run
```

Run through execute only after check-only and dry-run are clean:

```bash
./scripts/run_local_full_trading_test_handoff.sh --execute
```

## Exact Commands

### 1. Check-only

```bash
python3 scripts/run_nexus_full_trading_test_cycle.py --check-only
```

Verifies:

- safety gate
- receiver health on `127.0.0.1:5000`
- passive Oanda practice status
- passive Supabase connectivity
- full phase verification artifact generation

Inspect after:

- `logs/full_trading_test_cycle_latest.json`
- `logs/full_trading_test_cycle_latest.md`
- `logs/trading_engine_phase_status_latest.json`
- `logs/trading_engine_phase_status_latest.md`

Success means:

- `status=TEST_CYCLE_CHECKS_OK`
- `phase_overall_status=ALL_TEST_PHASES_ACTIVE` or only known non-critical partials
- receiver reachable
- Oanda practice reachable
- Supabase reachable

Failure means:

- `status=TEST_CYCLE_BLOCKED`
- blocked steps will identify `receiver_health`, `oanda_practice_status`, `supabase_connectivity`, or `verify_trading_phases`

### 2. Dry-run

```bash
python3 scripts/run_nexus_full_trading_test_cycle.py --dry-run
```

Verifies:

- all check-only gates
- strategy discovery
- Supabase strategy search
- intelligence packet build
- tournament ranking
- London open watch
- New York open refresh watch
- replay generation
- demo loop in passive mode
- practice memory analysis
- Hermes report generation

Inspect after:

- `logs/full_trading_test_cycle_latest.json`
- `logs/trading_intelligence_packet_latest.json`
- `logs/nexus_trading_tournament_latest.json`
- `logs/live_watch/trading_watch_session_latest.json`
- `logs/charts/live_watch_dashboard_latest.html`
- `logs/charts/trade_replay_latest.html`
- `logs/charts/trading_dashboard_latest.html`
- `logs/practice_trade_memory_latest.json`
- `logs/nexus_trading_telegram_ready_latest.md`

Success means:

- `status=TEST_CYCLE_DRY_RUN_OK`
- watch artifacts generated
- replay artifact generated
- Hermes report generated
- no execute-only action taken

Failure means:

- `status=TEST_CYCLE_BLOCKED`
- inspect the first required failed step in `logs/full_trading_test_cycle_latest.json`

### 3. Execute

Only run this after clean check-only and clean dry-run:

```bash
python3 scripts/run_nexus_full_trading_test_cycle.py --execute --max-oanda-trades 5 --max-units 1
```

Verifies:

- all prior gates still pass
- practice trading cycle can run in execute mode
- capped Oanda practice orders can be placed only if all safety gates pass
- local_paper fallback remains available

Inspect after:

- `logs/full_trading_test_cycle_latest.json`
- `logs/nexus_demo_trading_loop_latest.json`
- `logs/practice_trade_memory_latest.json`
- `logs/charts/trade_replay_latest.html`
- `logs/nexus_trading_telegram_ready_latest.md`
- today’s `logs/nexus_paper_trades_YYYYMMDD.jsonl`
- today’s `logs/nexus_trading_reports_YYYYMMDD.jsonl`

Success means:

- `status=TEST_CYCLE_EXECUTE_OK`
- no live-trading blocker triggered
- any broker execution is clearly labeled `oanda_practice`
- unit size is `1`

Failure means:

- execute path was blocked by safety, receiver, Oanda ambiguity, or downstream runner failure

## How To Tell Each Subsystem Is Working

### Receiver

Working:

- `check-only` passes
- `receiver_health` step is `ok=true`
- phase status shows `receiver_health=active`

Not working:

- `receiver_health` blocked or unreachable
- do not run execute

### Oanda Practice

Working:

- `check_oanda_practice.py --status-only` returns `OANDA_PRACTICE_READY`
- phase status shows `oanda_practice_status=active`
- any execute-mode broker activity is labeled practice/demo only

Not working:

- any ambiguity about account, endpoint, or environment
- any DNS/auth/connectivity failure
- do not run execute

### Supabase

Working:

- `check_supabase_connectivity.py` passes
- phase status shows `supabase_connectivity=active`
- strategy search and memory writes can use Supabase instead of local fallback only

Not working:

- DNS/HTTPS/auth/query failure
- local fallback may still work, but treat Supabase-native phases as degraded

### Tournament

Working:

- `logs/nexus_trading_tournament_latest.json` exists
- `top_strategy` is present
- `strategies` list is populated

Not working:

- file missing
- zero strategies ranked
- top strategy absent

### Replay

Working:

- `logs/charts/trade_replay_latest.html` exists
- chart shows candle context and metadata
- `logs/charts/trading_dashboard_latest.html` also updates

Not working:

- replay file missing
- stale timestamp
- no chart metadata for latest session/trade

### Hermes

Working:

- `logs/nexus_trading_telegram_ready_latest.md` exists
- it references current watch/replay/tournament state
- chart/replay paths are included

Not working:

- report missing
- stale state
- no current artifact references

## What To Do If Check-only Passes But Dry-run Fails

1. Open `logs/full_trading_test_cycle_latest.json`
2. Find the first required failed step after the safety/connectivity gates
3. Use the matching artifact to isolate the failure:
   - discovery: `logs/trading_strategy_discovery_latest.json`
   - strategy search: `logs/hermes_supabase_strategy_candidates_latest.json`
   - packet: `logs/trading_intelligence_packet_latest.json`
   - tournament: `logs/nexus_trading_tournament_latest.json`
   - watch: `logs/live_watch/trading_watch_session_latest.json`
   - replay: `logs/charts/trade_replay_latest.html`
   - memory: `logs/practice_trade_memory_latest.json`
4. Fix the failing phase
5. Re-run:

```bash
python3 scripts/run_nexus_full_trading_test_cycle.py --dry-run
```

Do not run execute until dry-run is clean.

## What To Do If Dry-run Passes But Execute Fails

1. Open:
   - `logs/full_trading_test_cycle_latest.json`
   - `logs/nexus_demo_trading_loop_latest.json`
   - `logs/practice_trade_memory_latest.json`
   - today’s `logs/nexus_trading_reports_YYYYMMDD.jsonl`
2. Check for:
   - safety gate flip
   - receiver failure
   - Oanda practice ambiguity
   - repeated broker errors
   - duplicate/reject storms
3. If Oanda execute failed but safety is still intact:
   - keep practice mode active
   - use local_paper fallback
   - do not increase units
   - do not bypass the execute gate
4. Re-run only after the execute blocker is clearly resolved:

```bash
python3 scripts/run_nexus_full_trading_test_cycle.py --execute --max-oanda-trades 5 --max-units 1
```

## Recommended Local Run Order

```bash
python3 scripts/run_nexus_full_trading_test_cycle.py --check-only
python3 scripts/run_nexus_full_trading_test_cycle.py --dry-run
python3 scripts/run_nexus_full_trading_test_cycle.py --execute --max-oanda-trades 5 --max-units 1
```

Or use the wrapper:

```bash
./scripts/run_local_full_trading_test_handoff.sh
./scripts/run_local_full_trading_test_handoff.sh --dry-run
./scripts/run_local_full_trading_test_handoff.sh --execute
```
