#!/usr/bin/env bash
set -euo pipefail

cd "${HOME}/nexus-ai"

MODE="check-only"
if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [--check-only|--dry-run|--execute]"
  exit 2
fi
if [[ $# -eq 1 ]]; then
  case "$1" in
    --check-only)
      MODE="check-only"
      ;;
    --dry-run)
      MODE="dry-run"
      ;;
    --execute)
      MODE="execute"
      ;;
    *)
      echo "Usage: $0 [--check-only|--dry-run|--execute]"
      exit 2
      ;;
  esac
fi

echo "============================================================"
echo "NEXUS TRADING PRACTICE CYCLE"
echo "Mode: ${MODE}"
echo "Live trading must remain disabled"
echo "============================================================"

if [[ "${MODE}" == "execute" ]]; then
  echo ""
  echo "WARNING: EXECUTE MODE CAN PLACE CAPPED OANDA PRACTICE ORDERS."
  echo "LIVE_TRADING remains false."
  echo "OANDA practice only."
  echo "Max units: 1."
fi

echo ""
echo "1) Checking trading safety..."
python3 scripts/check_trading_safety.py

echo ""
echo "2) Checking receiver health..."
python3 scripts/trading_receiver_healthcheck.py

echo ""
echo "3) Checking receiver /status..."
curl -sS http://127.0.0.1:5000/status || {
  echo ""
  echo "ERROR: Receiver status endpoint failed."
  exit 1
}

echo ""
echo ""
echo "4) Checking Oanda practice status passively..."
python3 scripts/check_oanda_practice.py --status-only

case "${MODE}" in
  check-only)
    echo ""
    echo "5) Check-only mode: skipping Supabase tournament and execution."
    ;;

  dry-run)
    echo ""
    echo "5) Checking Supabase connectivity..."
    python3 scripts/check_supabase_connectivity.py

    echo ""
    echo "6) Running Supabase-first tournament dry-run..."
    python3 scripts/run_nexus_trading_tournament.py --mode paper --source supabase_first --data-source oanda_practice --symbols EURUSD,USDJPY,GBPUSD --dry-run

    echo ""
    echo "7) Running Nexus demo/paper trading loop dry-run..."
    python3 scripts/run_nexus_demo_trading_loop.py --mode paper --dry-run
    ;;

  execute)
    echo ""
    echo "5) Running Nexus demo/paper trading loop..."
    echo "This is the only step in the normal practice cycle that can place capped Oanda practice orders."
    python3 scripts/run_nexus_demo_trading_loop.py --mode paper
    ;;
esac

echo ""
echo "8) Generating Hermes trading report..."
python3 scripts/send_trading_status_report.py --dry-run

echo ""
echo "9) Showing recent receiver trades..."
curl -sS http://127.0.0.1:5000/trades/recent || true

echo ""
echo ""
echo "============================================================"
echo "NEXUS PRACTICE CYCLE COMPLETE"
echo "Next files to inspect:"
echo "- logs/trading_engine_status.json"
echo "- logs/nexus_trading_telegram_ready_latest.md"
echo "- logs/nexus_trading_tournament_latest.json"
echo "- integrations/oanda_demo/reports/"
echo "============================================================"
