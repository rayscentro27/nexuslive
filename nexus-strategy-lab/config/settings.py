"""
config/settings.py — Runtime config loader with validation.

Loads from ~/nexus-ai/.env (the project-wide source of truth).
All strategy-lab workers import from here instead of os.environ directly.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Resolve .env ──────────────────────────────────────────────────────────────
# Priority: local .env > parent nexus-ai/.env
_HERE = Path(__file__).resolve().parent.parent          # nexus-strategy-lab/
_ROOT = _HERE.parent                                    # nexus-ai/

for _env_path in (_HERE / '.env', _ROOT / '.env'):
    if _env_path.exists():
        load_dotenv(_env_path)
        break

# ── Required fields ───────────────────────────────────────────────────────────
_REQUIRED = [
    'SUPABASE_URL',
    'SUPABASE_KEY',
]

def validate():
    """Raise EnvironmentError if any required variable is missing."""
    missing = [k for k in _REQUIRED if not os.getenv(k)]
    if missing:
        raise EnvironmentError(
            f"nexus-strategy-lab: missing required env vars: {', '.join(missing)}\n"
            f"Check {_ROOT / '.env'}"
        )

# ── Supabase ──────────────────────────────────────────────────────────────────
SUPABASE_URL: str           = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY: str           = os.getenv('SUPABASE_KEY', '')
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv('SUPABASE_SERVICE_ROLE_KEY', SUPABASE_KEY)

# ── AI Gateways ───────────────────────────────────────────────────────────────
HERMES_GATEWAY_URL: str     = os.getenv('HERMES_GATEWAY_URL', 'http://localhost:8642')
HERMES_GATEWAY_TOKEN: str   = os.getenv('HERMES_GATEWAY_TOKEN', '')
HERMES_GATEWAY_URL: str           = os.getenv('HERMES_GATEWAY_URL', 'http://localhost:8642')
HERMES_GATEWAY_TOKEN: str    = os.getenv('HERMES_GATEWAY_TOKEN', '')
OPENROUTER_BASE_URL: str    = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
OPENROUTER_API_KEY: str     = os.getenv('OPENROUTER_API_KEY', '')

# ── Telegram ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str     = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID: str       = os.getenv('TELEGRAM_CHAT_ID', '')

# ── Demo trading ──────────────────────────────────────────────────────────────
DEMO_ACCOUNT_ID: str        = os.getenv('DEMO_ACCOUNT_ID', '')
DEMO_STARTING_BALANCE: float = float(os.getenv('DEMO_STARTING_BALANCE', '10000.00'))
DRY_RUN: bool               = os.getenv('DRY_RUN', 'true').lower() not in ('false', '0', 'no')

# ── Research paths ────────────────────────────────────────────────────────────
RESEARCH_OUTPUT_DIR: Path   = Path(os.getenv('RESEARCH_OUTPUT_DIR',
    str(_ROOT / 'research-engine' / 'summaries')))
STRATEGIES_DIR: Path        = Path(os.getenv('STRATEGIES_DIR',
    str(_ROOT / 'research-engine' / 'strategies')))

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_LEVEL: str              = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_DIR: Path               = Path(os.getenv('LOG_DIR', str(_HERE / 'logs')))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── AI provider preference ────────────────────────────────────────────────────
# 'hermes' | 'openrouter' | 'hermes' | 'auto'
# auto tries Hermes first, then OpenRouter, then local Hermes.
AI_PROVIDER: str            = os.getenv('AI_PROVIDER', 'auto')
