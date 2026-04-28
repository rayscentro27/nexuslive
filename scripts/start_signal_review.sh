#!/bin/bash
# Start the Nexus Signal Review workflow
# Polls tv_normalized_signals → OpenClaw AI review → risk gate → Telegram alerts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEXUS_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$NEXUS_DIR/logs"

mkdir -p "$LOG_DIR"

echo "Starting Nexus Signal Review poller..."
cd "$NEXUS_DIR/signal_review"
exec python3 signal_poller.py
