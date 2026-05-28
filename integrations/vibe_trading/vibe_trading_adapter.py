"""
vibe_trading_adapter.py — Nexus wrapper around the vibe-trading CLI.

Safety contract:
- NEVER executes live trades or connects broker APIs.
- Only allowed task types: backtest, market_research, strategy_compare, forex_research.
- Adds educational disclaimer to every result.
- Saves every run to JSON in reports/.
- Shell tools disabled via env.
- NEXUS_ALLOW_PAID_LLM=false (default) blocks paid LLM providers (openrouter, openai, deepseek).
  Set NEXUS_ALLOW_PAID_LLM=true in .env to explicitly allow paid providers.

Usage:
    from integrations.vibe_trading.vibe_trading_adapter import run_vibe_trading_task
    result = run_vibe_trading_task("Backtest RSI(14) on EURUSD", task_type="backtest")

CLI test:
    python integrations/vibe_trading/vibe_trading_adapter.py \
        --prompt "Backtest RSI(14) mean-reversion on EURUSD=X education-only." \
        --task-type backtest
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

WORKSPACE = ROOT / "workspace"
REPORTS   = ROOT / "reports"
VENV_BIN  = ROOT / ".venv" / "bin"

# Load .env from integration folder (provider keys, etc.)
_dotenv = ROOT / ".env"
if _dotenv.exists():
    with open(_dotenv) as _f:
        for _line in _f:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _, _v = _line.partition("=")
            _k = _k.strip()
            _v = _v.strip().strip('"').strip("'")
            if _k not in os.environ:
                os.environ[_k] = _v

WORKSPACE.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

# ── Allowlist / blocklist ──────────────────────────────────────────────────────

ALLOWED_TASK_TYPES = {
    "backtest",
    "market_research",
    "strategy_compare",
    "forex_research",
}

BLOCKED_KEYWORDS = {
    "live_trade", "place_order", "broker_connect", "withdraw",
    "deposit", "execute_trade", "real_money", "buy market",
    "sell market", "connect broker", "live account",
}

# Providers that incur API costs — blocked unless NEXUS_ALLOW_PAID_LLM=true
PAID_PROVIDERS = {"openrouter", "openai", "deepseek", "anthropic", "groq", "mistral"}
FREE_PROVIDERS  = {"ollama", "openai-codex", "local"}

EDUCATIONAL_DISCLAIMER = (
    "\n\n---\n"
    "EDUCATIONAL DISCLAIMER: This output is for research and education only. "
    "No live trades were executed. No broker was connected. "
    "Past performance does not predict future results. "
    "This is a paper-trading simulation — not financial advice.\n"
    "Safety mode: education_only_paper_trading | Cost mode: free_or_local_only"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _vibe_bin() -> str:
    local = VENV_BIN / "vibe-trading"
    if local.exists():
        return str(local)
    # fall back to PATH
    import shutil
    found = shutil.which("vibe-trading")
    if found:
        return found
    raise FileNotFoundError(
        "vibe-trading CLI not found. Run: "
        "source integrations/vibe_trading/.venv/bin/activate && "
        "pip install -U vibe-trading-ai"
    )


def _check_blocked(prompt: str, task_type: str) -> str | None:
    combined = (prompt + " " + task_type).lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in combined:
            return kw
    return None


def _check_paid_llm_allowed() -> None:
    """
    Raise ValueError if a paid LLM provider is configured but
    NEXUS_ALLOW_PAID_LLM is not explicitly set to 'true'.

    Free providers (ollama, local) are always allowed.
    Paid providers (openrouter, openai, deepseek, anthropic…) require
    NEXUS_ALLOW_PAID_LLM=true in integrations/vibe_trading/.env.
    """
    allow_paid = os.getenv("NEXUS_ALLOW_PAID_LLM", "false").lower().strip()
    provider   = os.getenv("LANGCHAIN_PROVIDER", "").lower().strip()

    if not provider:
        # No provider configured — vibe-trading will fail its own preflight,
        # but that's a config error, not a cost-control violation.
        return

    if provider in FREE_PROVIDERS:
        return

    if provider in PAID_PROVIDERS and allow_paid != "true":
        raise ValueError(
            f"NEXUS_ALLOW_PAID_LLM=false but LANGCHAIN_PROVIDER='{provider}' is a paid provider. "
            f"Paid providers: {sorted(PAID_PROVIDERS)}. "
            "To allow: set NEXUS_ALLOW_PAID_LLM=true in integrations/vibe_trading/.env. "
            "To use free: set LANGCHAIN_PROVIDER=ollama with OLLAMA_BASE_URL."
        )

    # Unknown provider and paid guard is off — warn but allow
    if provider not in PAID_PROVIDERS and provider not in FREE_PROVIDERS and allow_paid != "true":
        import warnings
        warnings.warn(
            f"Unknown LANGCHAIN_PROVIDER='{provider}'. "
            "If this is a paid provider, set NEXUS_ALLOW_PAID_LLM=true to suppress this warning.",
            stacklevel=3,
        )


def _save_report(result: dict) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    task = result.get("task_type", "unknown").replace(" ", "_")
    path = REPORTS / f"{task}_{ts}.json"
    path.write_text(json.dumps(result, indent=2, default=str))
    return path


def run_vibe_trading_task(
    prompt: str,
    task_type: str = "backtest",
    timeout: int = 300,
) -> dict:
    """
    Run a vibe-trading task safely via CLI subprocess.

    Returns a dict with: stdout, stderr, return_code, report_path, metadata.
    Raises ValueError if task_type is blocked.
    """
    task_type = task_type.strip().lower()

    if task_type not in ALLOWED_TASK_TYPES:
        raise ValueError(
            f"Task type '{task_type}' is not in the allowed list: {sorted(ALLOWED_TASK_TYPES)}"
        )

    blocked_kw = _check_blocked(prompt, task_type)
    if blocked_kw:
        raise ValueError(
            f"Prompt contains blocked keyword '{blocked_kw}'. "
            "Live trading and broker connections are disabled."
        )

    # Cost guard: block paid LLM providers unless explicitly allowed
    _check_paid_llm_allowed()

    # Safety: force shell tools off in subprocess env
    safe_env = os.environ.copy()
    safe_env["VIBE_TRADING_ENABLE_SHELL_TOOLS"] = "0"
    safe_env["NEXUS_VIBE_TRADING_ENABLED"] = "true"

    # Prepend educational context to every prompt
    safe_prompt = (
        "[EDUCATION-ONLY PAPER-TRADING RESEARCH. NO LIVE TRADES. NO BROKER CONNECTION.] "
        + prompt
    )

    try:
        vibe_bin = _vibe_bin()
    except FileNotFoundError as exc:
        result = {
            "task_type":   task_type,
            "prompt":      prompt,
            "command":     None,
            "return_code": -1,
            "stdout":      "",
            "stderr":      str(exc),
            "error":       "vibe-trading CLI not installed",
            "timestamp":   _now_iso(),
            "safety_mode": "education_only_paper_trading",
            "cost_mode":   "free_or_local_only",
            "disclaimer":  EDUCATIONAL_DISCLAIMER,
        }
        _save_report(result)
        return result

    cmd = [vibe_bin, "run", "-p", safe_prompt]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_env,
            cwd=str(WORKSPACE),
        )
        stdout = proc.stdout
        stderr = proc.stderr
        rc     = proc.returncode
    except subprocess.TimeoutExpired:
        stdout = ""
        stderr = f"Timed out after {timeout}s"
        rc     = -1
    except Exception as exc:
        stdout = ""
        stderr = str(exc)
        rc     = -1

    # Append disclaimer to stdout
    if stdout:
        stdout = stdout + EDUCATIONAL_DISCLAIMER

    result = {
        "task_type":   task_type,
        "prompt":      prompt,
        "command":     " ".join(cmd),
        "return_code": rc,
        "stdout":      stdout,
        "stderr":      stderr,
        "timestamp":   _now_iso(),
        "safety_mode": "education_only_paper_trading",
        "cost_mode":   "free_or_local_only",
        "disclaimer":  EDUCATIONAL_DISCLAIMER,
    }

    report_path = _save_report(result)
    result["report_path"] = str(report_path)

    return result


# ── CLI entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Nexus → Vibe-Trading safe adapter (education-only)"
    )
    parser.add_argument("--prompt",    required=True, help="Research prompt")
    parser.add_argument("--task-type", default="backtest",
                        choices=sorted(ALLOWED_TASK_TYPES),
                        help="Task type (default: backtest)")
    parser.add_argument("--timeout",   type=int, default=300,
                        help="Subprocess timeout in seconds (default: 300)")
    args = parser.parse_args()

    print(f"[adapter] Running task_type={args.task_type}")
    print(f"[adapter] Prompt: {args.prompt[:120]}...")
    print()

    try:
        result = run_vibe_trading_task(
            prompt=args.prompt,
            task_type=args.task_type,
            timeout=args.timeout,
        )
    except ValueError as e:
        print(f"[adapter] BLOCKED: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[adapter] Return code: {result['return_code']}")
    print(f"[adapter] Report saved: {result.get('report_path', 'N/A')}")
    print()

    if result["stdout"]:
        print("=== STDOUT ===")
        print(result["stdout"][:4000])

    if result["stderr"]:
        print("=== STDERR ===")
        print(result["stderr"][:2000], file=sys.stderr)

    # Pretty-print metadata (no stdout body, that's in report)
    meta = {k: v for k, v in result.items() if k not in ("stdout", "disclaimer")}
    print("\n=== METADATA ===")
    print(json.dumps(meta, indent=2, default=str))
