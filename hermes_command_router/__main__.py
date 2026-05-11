"""
hermes_command_router — CLI entry point for Hermes structured ops commands.

Usage:
    cd ~/nexus-ai
    python -m hermes_command_router "check backend health"       # deterministic (no AI)
    python -m hermes_command_router "worker status"             # deterministic (no AI)
    python -m hermes_command_router "next best move"            # qwen3:8b reasoning
    python -m hermes_command_router "are we ready for pilot"    # qwen3:8b reasoning
    python -m hermes_command_router "summarize recent activity" # qwen3:8b reasoning

Output: structured Hermes Report to stdout.
Model used is logged to stderr.
"""
from __future__ import annotations

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from hermes_command_router.router import run_command

if __name__ == '__main__':
    query = ' '.join(sys.argv[1:]).strip() if len(sys.argv) > 1 else ''
    if not query:
        print("Usage: python -m hermes_command_router \"<command>\"")
        print("Examples:")
        print("  python -m hermes_command_router \"check backend health\"")
        print("  python -m hermes_command_router \"worker status\"")
        print("  python -m hermes_command_router \"queue status\"")
        print("  python -m hermes_command_router \"next best move\"")
        print("  python -m hermes_command_router \"are we ready for pilot\"")
        print("  python -m hermes_command_router \"summarize recent activity\"")
        sys.exit(0)
    result = run_command(query)
    print(result)
