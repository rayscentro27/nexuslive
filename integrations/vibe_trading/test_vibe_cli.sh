#!/usr/bin/env bash
# test_vibe_cli.sh — Smoke-test the vibe-trading CLI.
# Run from nexus-ai: bash integrations/vibe_trading/test_vibe_cli.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
VIBE="$VENV/bin/vibe-trading"

if [ ! -f "$VIBE" ]; then
    echo "ERROR: vibe-trading not found at $VIBE"
    echo "Run: bash integrations/vibe_trading/install_vibe_trading.sh"
    exit 1
fi

# shellcheck disable=SC1090
source "$VENV/bin/activate"

echo "=== Vibe-Trading CLI Test ==="
echo "Binary: $VIBE"
echo ""

echo "--- vibe-trading --help ---"
"$VIBE" --help 2>&1 | head -30 || true
echo ""

echo "--- vibe-trading --skills (if supported) ---"
"$VIBE" --skills 2>&1 | head -20 || true
echo ""

echo "--- Research prompt (education-only, no live data required) ---"
VIBE_TRADING_ENABLE_SHELL_TOOLS=0 \
"$VIBE" run -p \
  "[EDUCATION-ONLY TEST] Research EUR/USD at a high level using free or simulated data if available. Describe RSI mean-reversion theory only. Do not trade. Do not connect brokers." \
  2>&1 | head -60 || true

echo ""
echo "=== CLI test complete ==="
