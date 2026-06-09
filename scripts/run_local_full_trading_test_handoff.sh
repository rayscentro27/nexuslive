#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/raymonddavis/nexus-ai"
cd "$ROOT"

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
echo "NEXUS LOCAL FULL TRADING TEST HANDOFF"
echo "Mode: ${MODE}"
echo "LIVE_TRADING must remain false"
echo "PAPER_ONLY must remain true"
echo "Oanda must remain practice/demo only"
echo "Max Oanda units must remain 1"
echo "============================================================"

echo
echo "1) Running check-only gate..."
python3 scripts/run_nexus_full_trading_test_cycle.py --check-only

if [[ "${MODE}" == "check-only" ]]; then
  echo
  echo "Check-only complete."
  echo "Inspect: logs/full_trading_test_cycle_latest.json"
  echo "Inspect: logs/trading_engine_phase_status_latest.json"
  exit 0
fi

echo
echo "2) Running dry-run gate..."
python3 scripts/run_nexus_full_trading_test_cycle.py --dry-run

if [[ "${MODE}" == "dry-run" ]]; then
  echo
  echo "Dry-run complete."
  echo "Inspect: logs/full_trading_test_cycle_latest.json"
  echo "Inspect: logs/trading_engine_phase_status_latest.json"
  echo "Inspect: logs/trading_intelligence_packet_latest.json"
  echo "Inspect: logs/practice_trade_memory_latest.json"
  exit 0
fi

echo
echo "3) Execute requested. Running only after check-only and dry-run passed."
echo "WARNING: EXECUTE MODE CAN PLACE CAPPED OANDA PRACTICE ORDERS."
echo "LIVE_TRADING remains false."
echo "OANDA practice/demo only."
echo "Max units: 1."
echo "local_paper fallback active."
echo "No live-money trading allowed."
python3 scripts/run_nexus_full_trading_test_cycle.py --execute --max-oanda-trades 5 --max-units 1

echo
echo "Execute complete."
echo "Inspect: logs/full_trading_test_cycle_latest.json"
echo "Inspect: logs/practice_trade_memory_latest.json"
echo "Inspect: logs/nexus_trading_telegram_ready_latest.md"
