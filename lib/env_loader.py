"""
env_loader.py — Centralized .env loader for all nexus-ai Python workers.

Usage:
    from lib.env_loader import load_nexus_env
    load_nexus_env()   # call before any os.getenv()

Loads nexus-ai/.env (the root source of truth), then optionally a local
override file for workflow-specific vars. Safe to call multiple times.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent  # nexus-ai/


def load_nexus_env(override: Path | str | None = None) -> None:
    """Load root .env, then an optional local override."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return  # dotenv not installed — rely on shell environment

    load_dotenv(_ROOT / ".env")
    if override:
        p = Path(override)
        if p.exists():
            load_dotenv(p, override=True)
