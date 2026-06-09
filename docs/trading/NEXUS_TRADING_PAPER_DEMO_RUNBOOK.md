# Nexus Trading Paper/Demo Runbook

## Safety locks

- `LIVE_TRADING=false`
- `PAPER_ONLY=true`
- `NEXUS_DRY_RUN=true`
- Oanda practice orders capped at `1` unit
- Oanda practice daily cap remains enforced
- Local paper fallback must stay enabled

## Check receiver

```bash
cd ~/nexus-ai
python3 scripts/trading_receiver_healthcheck.py
curl -sS http://127.0.0.1:5000/status
```

## Verify Oanda practice

```bash
cd ~/nexus-ai
python3 scripts/check_oanda_practice.py
```

## Run Supabase strategy search

```bash
cd ~/nexus-ai
python3 scripts/hermes_supabase_strategy_search.py --asset-class forex --limit 20
```

## Replay fallback logs

Dry run:

```bash
cd ~/nexus-ai
python3 scripts/replay_trading_fallback_logs_to_supabase.py
```

Apply:

```bash
cd ~/nexus-ai
python3 scripts/replay_trading_fallback_logs_to_supabase.py --apply
```

## Run tournament

```bash
cd ~/nexus-ai
python3 scripts/run_nexus_trading_tournament.py --mode paper --source supabase_first
```

Dry run only:

```bash
cd ~/nexus-ai
python3 scripts/run_nexus_trading_tournament.py --mode paper --source supabase_first --dry-run
```

## Run demo trading loop

```bash
cd ~/nexus-ai
python3 scripts/run_nexus_demo_trading_loop.py --mode paper --dry-run
```

Non-dry-run:

```bash
cd ~/nexus-ai
python3 scripts/run_nexus_demo_trading_loop.py --mode paper --max-oanda-trades 1
```

## Generate Hermes report

```bash
cd ~/nexus-ai
python3 scripts/send_trading_status_report.py --dry-run
cat logs/nexus_trading_telegram_ready_latest.md
```

## Stop receiver/service

```bash
launchctl kickstart -k gui/501/com.nexus.trading-engine
```

## Troubleshoot Supabase DNS

- Run `python3 scripts/check_supabase_connectivity.py`
- If DNS/HTTPS is blocked, keep local fallback active
- Use `python3 scripts/replay_trading_fallback_logs_to_supabase.py` once connectivity returns

## Troubleshoot Oanda cap

- Review `integrations/oanda_demo/reports/demo_orders_YYYY-MM-DD.jsonl`
- Wait until next daily window or keep using `local_paper` fallback
- Do not raise the cap without explicit approval
