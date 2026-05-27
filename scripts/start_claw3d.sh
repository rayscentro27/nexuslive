#!/usr/bin/env bash
# start_claw3d.sh — Launch Claw3D 3D office with Nexus Hermes adapter
# Usage: bash scripts/start_claw3d.sh [--dev | --prod]
# Requires: node, npm, Hermes gateway running on port 8642

set -e

CLAW_DIR="$HOME/nexus-claw3d"
MODE="${1:---dev}"

if [ ! -d "$CLAW_DIR" ]; then
  echo "❌ Claw3D not found at $CLAW_DIR"
  echo "   Run: git clone https://github.com/iamlukethedev/Claw3D.git ~/nexus-claw3d"
  exit 1
fi

echo "🧠 Nexus Claw3D Launcher"
echo "========================"
echo "  Directory:  $CLAW_DIR"
echo "  Mode:       $MODE"
echo "  Hermes:     http://127.0.0.1:8642"
echo "  Adapter:    ws://localhost:18789"
echo "  App:        http://localhost:3000"
echo ""

# Install deps if needed
if [ ! -d "$CLAW_DIR/node_modules" ]; then
  echo "Installing npm dependencies..."
  cd "$CLAW_DIR" && npm install
fi

# Start Hermes adapter in background
echo "Starting Hermes WebSocket adapter (port 18789)..."
cd "$CLAW_DIR"
npm run hermes-adapter &
ADAPTER_PID=$!
echo "  Adapter PID: $ADAPTER_PID"

sleep 2

# Start Claw3D app server
if [ "$MODE" = "--prod" ]; then
  echo "Building Claw3D for production..."
  npm run build
  echo "Starting production server..."
  npm run start
else
  echo "Starting Claw3D dev server..."
  npm run dev
fi

# Cleanup on exit
trap "kill $ADAPTER_PID 2>/dev/null; echo 'Claw3D stopped.'" EXIT
