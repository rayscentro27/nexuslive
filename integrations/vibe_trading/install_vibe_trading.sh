#!/usr/bin/env bash
# install_vibe_trading.sh — Install vibe-trading-ai into an isolated venv.
# Run from nexus-ai project root: bash integrations/vibe_trading/install_vibe_trading.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

echo "=== Nexus Vibe-Trading Installer ==="
echo "Target venv: $VENV"
echo ""

# Create venv if needed
if [ ! -d "$VENV" ]; then
    echo "[1/4] Creating Python venv..."
    python3 -m venv "$VENV"
else
    echo "[1/4] Venv already exists, skipping create."
fi

# Activate
# shellcheck disable=SC1090
source "$VENV/bin/activate"

echo "[2/4] Upgrading pip..."
pip install --upgrade pip --quiet

echo "[3/4] Installing vibe-trading-ai..."
pip install -U vibe-trading-ai

echo "[4/4] Verifying install..."
echo ""
echo "--- vibe-trading --help ---"
"$VENV/bin/vibe-trading" --help 2>&1 | head -20 || echo "(help output above)"

echo ""
if [ -f "$VENV/bin/vibe-trading-mcp" ]; then
    echo "--- vibe-trading-mcp: FOUND at $VENV/bin/vibe-trading-mcp ---"
    "$VENV/bin/vibe-trading-mcp" --help 2>&1 | head -10 || true
else
    echo "--- vibe-trading-mcp: NOT FOUND (may be part of vibe-trading binary) ---"
fi

echo ""
echo "=== Install complete ==="
echo "To activate: source integrations/vibe_trading/.venv/bin/activate"
echo "To test CLI:  bash integrations/vibe_trading/test_vibe_cli.sh"
echo "To run forex: python integrations/vibe_trading/test_forex_backtest.py"
