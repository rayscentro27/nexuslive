#!/usr/bin/env bash
# test_vibe_mcp.sh — Check MCP server availability and print OpenClaw config.
# Run from nexus-ai: bash integrations/vibe_trading/test_vibe_mcp.sh
# NOTE: Does NOT modify any existing config automatically.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/.venv"
MCP_BIN="$VENV/bin/vibe-trading-mcp"
VIBE_BIN="$VENV/bin/vibe-trading"

echo "=== Vibe-Trading MCP Server Check ==="
echo ""

if [ -f "$MCP_BIN" ]; then
    echo "✅ vibe-trading-mcp: FOUND at $MCP_BIN"
    echo ""
    echo "--- vibe-trading-mcp --help ---"
    "$MCP_BIN" --help 2>&1 | head -20 || true
elif [ -f "$VIBE_BIN" ]; then
    echo "⚠️  vibe-trading-mcp not found as separate binary."
    echo "   Checking if vibe-trading itself serves MCP..."
    "$VIBE_BIN" --help 2>&1 | grep -i mcp || echo "   No MCP flag found in --help."
    echo ""
    echo "   The MCP server may be launched with: vibe-trading mcp"
    MCP_BIN="$VIBE_BIN mcp"
else
    echo "❌ Neither vibe-trading nor vibe-trading-mcp found."
    echo "   Run: bash integrations/vibe_trading/install_vibe_trading.sh"
    exit 1
fi

echo ""
echo "============================================================"
echo "SUGGESTED OpenClaw / Hermes MCP Config Block"
echo "(DO NOT apply automatically — review and add manually)"
echo "============================================================"
echo ""
cat <<'EOF'
# Add to your openclaw.yaml or hermes MCP skills config:
skills:
  - name: vibe-trading
    command: /Users/raymonddavis/nexus-ai/integrations/vibe_trading/.venv/bin/vibe-trading-mcp
    # If MCP is a subcommand:
    # command: /Users/raymonddavis/nexus-ai/integrations/vibe_trading/.venv/bin/vibe-trading
    # args: ["mcp"]
    env:
      VIBE_TRADING_ENABLE_SHELL_TOOLS: "0"
      NEXUS_VIBE_TRADING_MODE: "local_cli"

# Safety reminder: always keep VIBE_TRADING_ENABLE_SHELL_TOOLS=0
# Do NOT expose on a public port.
EOF

echo ""
echo "=== MCP check complete ==="
echo "To apply this config, manually edit your openclaw.yaml and restart OpenClaw."
