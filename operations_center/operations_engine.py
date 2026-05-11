#!/usr/bin/env python3
"""
Nexus AI Operations Engine
Monitors all system modules and exposes a unified status API.
"""
import os
import sys
import json
import logging
import subprocess
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

# Add parent to path so sibling modules can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger("OperationsEngine")

LLM_BASE_URL = (
    os.getenv("NEXUS_LLM_BASE_URL")
    or os.getenv("OPENROUTER_BASE_URL")
    or os.getenv("OPENAI_BASE_URL")
    or "https://openrouter.ai/api/v1"
).rstrip("/")
LLM_API_KEY = (
    os.getenv("NEXUS_LLM_API_KEY")
    or os.getenv("OPENROUTER_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or ""
)
NEXUS_DASH_URL = os.getenv("NEXUS_API_URL", "http://localhost:3000")
SIGNAL_ROUTER_URL = "http://localhost:8000"
CONTROL_CENTER_URL = "http://localhost:4000"


def _check_port(url: str, timeout: float = 2.0) -> bool:
    try:
        r = requests.get(url, timeout=timeout)
        return r.status_code < 500
    except Exception:
        return False


def _check_http(url: str, timeout: float = 2.0, headers: Optional[Dict[str, str]] = None) -> tuple[bool, Optional[int]]:
    try:
        r = requests.get(url, timeout=timeout, headers=headers or {})
        return r.status_code < 500, r.status_code
    except Exception:
        return False, None


def _models_url(base_url: str) -> str:
    root = (base_url or "").rstrip("/")
    if root.endswith("/v1") or root.endswith("/api/v1"):
        return f"{root}/models"
    return f"{root}/v1/models"


def _pgrep(pattern: str) -> Optional[int]:
    try:
        r = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
        if r.returncode == 0:
            return int(r.stdout.strip().splitlines()[0])
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────
# Module status checks
# ─────────────────────────────────────────────

def check_gateway() -> Dict[str, Any]:
    pid = _pgrep("hermes_cli.main gateway run") or _pgrep("ai.hermes.gateway")
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"} if LLM_API_KEY else None
    up, code = _check_http(_models_url(LLM_BASE_URL), headers=headers)
    parsed = urlparse(LLM_BASE_URL)
    return {
        "name": "Hermes / LLM Gateway",
        "port": parsed.port,
        "running": up or pid is not None,
        "pid": pid,
        "url": LLM_BASE_URL,
        "http_status": code,
        "transport": "local_hermes" if pid is not None else "remote_api",
    }


def check_dashboard() -> Dict[str, Any]:
    up = _check_port(NEXUS_DASH_URL)
    pid = _pgrep("dashboard.py")
    return {"name": "AI Dashboard", "port": 3000, "running": up, "pid": pid, "url": NEXUS_DASH_URL}


def check_signal_router() -> Dict[str, Any]:
    up = _check_port(f"{SIGNAL_ROUTER_URL}/health")
    pid = _pgrep("tradingview_router.py")
    return {"name": "Signal Router", "port": 8000, "running": up or pid is not None, "pid": pid}


def check_telegram() -> Dict[str, Any]:
    pid = _pgrep("telegram_bot.py --monitor")
    return {"name": "Telegram Monitor", "running": pid is not None, "pid": pid}


def check_control_center() -> Dict[str, Any]:
    up = _check_port(CONTROL_CENTER_URL)
    pid = _pgrep("control_center_server.py")
    return {"name": "Control Center", "port": 4000, "running": up, "pid": pid}


def check_research_brain() -> Dict[str, Any]:
    brain_state = Path(__file__).parent.parent / "research" / "brain_state.json"
    if brain_state.exists():
        try:
            state = json.loads(brain_state.read_text())
            return {
                "name": "Research Brain",
                "last_run": state.get("last_run"),
                "status": state.get("pipeline_status", "unknown"),
                "transcripts": state.get("transcript_count", 0),
                "summaries": state.get("summary_count", 0),
                "strategies": state.get("strategy_count", 0),
            }
        except Exception:
            pass
    # Fallback: count files directly
    base = Path(__file__).parent.parent / "research-engine"
    return {
        "name": "Research Brain",
        "last_run": None,
        "status": "idle",
        "transcripts": len(list((base / "transcripts").glob("*.vtt"))) if (base / "transcripts").exists() else 0,
        "summaries": len(list((base / "summaries").glob("*.summary"))) if (base / "summaries").exists() else 0,
        "strategies": len(list((base / "strategies").glob("*.summary"))) if (base / "strategies").exists() else 0,
    }


def get_system_health() -> Dict[str, Any]:
    return {
        "timestamp": datetime.now().isoformat(),
        "services": {
            "gateway":        check_gateway(),
            "dashboard":      check_dashboard(),
            "signal_router":  check_signal_router(),
            "telegram":       check_telegram(),
            "control_center": check_control_center(),
        },
        "research": check_research_brain(),
    }


# ─────────────────────────────────────────────
# Panel aggregators
# ─────────────────────────────────────────────

def get_hedge_fund_data() -> Dict[str, Any]:
    try:
        from operations_center.hedge_fund_panel import get_panel_data
        return get_panel_data()
    except Exception as e:
        return {"error": str(e)}


def get_marketing_data() -> Dict[str, Any]:
    try:
        from marketing_automation.marketing_engine import get_marketing_summary
        return get_marketing_summary()
    except Exception as e:
        return {"error": str(e)}


def get_lead_data() -> Dict[str, Any]:
    try:
        from lead_intelligence.lead_scoring_engine import get_lead_summary
        return get_lead_summary()
    except Exception as e:
        return {"error": str(e)}


def get_reputation_data() -> Dict[str, Any]:
    try:
        from reputation_engine.review_analyzer import get_reputation_summary
        return get_reputation_summary()
    except Exception as e:
        return {"error": str(e)}


def get_full_ops_report() -> Dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(),
        "system_health": get_system_health(),
        "hedge_fund": get_hedge_fund_data(),
        "marketing": get_marketing_data(),
        "leads": get_lead_data(),
        "reputation": get_reputation_data(),
        "research": check_research_brain(),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--health", action="store_true")
    p.add_argument("--full", action="store_true")
    args = p.parse_args()
    data = get_full_ops_report() if args.full else get_system_health()
    print(json.dumps(data, indent=2, default=str))
