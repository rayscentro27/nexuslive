"""
OANDA Practice-Environment Demo Adapter
Safety: practice only, max 1 unit, max 3 daily orders, OANDA_ALLOW_LIVE=false enforced.
"""
from __future__ import annotations

import json
import os
import ssl
from datetime import datetime, date
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    _env = Path(__file__).parent / ".env"
    if _env.exists():
        load_dotenv(_env)
except ImportError:
    pass

REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

PRACTICE_API_BASE = "https://api-fxpractice.oanda.com/v3"
# LIVE endpoint is hardcoded-blocked — never referenced
_LIVE_URL_BLOCKED = "BLOCKED_DO_NOT_USE"

MAX_UNITS        = int(os.getenv("OANDA_MAX_UNITS", "1"))
MAX_DAILY_ORDERS = int(os.getenv("OANDA_MAX_DAILY_ORDERS", "3"))


class OandaSafetyError(Exception):
    pass


class OandaDemoAdapter:
    """
    Thin wrapper around OANDA v20 REST API — practice account only.
    All safety checks run before any network call.
    """

    def __init__(self) -> None:
        self._enforce_safety_env()
        self._account_id = os.getenv("OANDA_ACCOUNT_ID", "")
        # Token loaded from env — never logged
        self._token = os.getenv("OANDA_ACCESS_TOKEN", "") or os.getenv("OANDA_API_KEY", "")

    # ── Public API ─────────────────────────────────────────────────────────────

    def connection_status(self) -> dict[str, Any]:
        """Return practice account status without placing any order."""
        self._enforce_safety_env()
        if not self._account_id or not self._token:
            return {"ok": False, "error": "OANDA_ACCOUNT_ID or OANDA_ACCESS_TOKEN/OANDA_API_KEY not set", "environment": "practice"}
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{PRACTICE_API_BASE}/accounts/{self._account_id}",
                headers=self._headers(),
            )
            with urllib.request.urlopen(req, timeout=10, context=self._ssl_context()) as resp:
                data = json.loads(resp.read())
            return {
                "ok": True,
                "environment": "practice",
                "account_id": self._account_id,
                "currency": data.get("account", {}).get("currency", ""),
                "balance": data.get("account", {}).get("balance", ""),
                "nav": data.get("account", {}).get("NAV", ""),
            }
        except Exception as e:
            return {"ok": False, "environment": "practice", "error": str(e)}

    def place_demo_order(
        self,
        instrument: str,
        side: str,
        units: int = 1,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Place a single market order on the practice account.
        Enforces: max 1 unit, max 3 daily orders, practice only.
        """
        self._enforce_safety_env()
        self._enforce_demo_enabled()
        self._enforce_units(units)
        self._enforce_daily_limit()
        if not self._account_id or not self._token:
            return self._fail("OANDA_ACCOUNT_ID or OANDA_ACCESS_TOKEN/OANDA_API_KEY not set")

        signed_units = units if side.lower() == "buy" else -units
        order_body = json.dumps({
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(signed_units),
            }
        }).encode()

        try:
            import urllib.request
            req = urllib.request.Request(
                f"{PRACTICE_API_BASE}/accounts/{self._account_id}/orders",
                data=order_body,
                headers={**self._headers(), "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15, context=self._ssl_context()) as resp:
                data = json.loads(resp.read())
            result = {
                "ok": True,
                "environment": "practice",
                "instrument": instrument,
                "side": side,
                "units": units,
                "reason": reason,
                "order_fill": data.get("orderFillTransaction", {}),
                "placed_at": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            result = self._fail(str(e), instrument=instrument, side=side, units=units)

        self._log_order(result, reason)
        return result

    def recent_orders(self, n: int = 10) -> list[dict]:
        log_file = REPORTS_DIR / f"demo_orders_{date.today().isoformat()}.jsonl"
        if not log_file.exists():
            return []
        lines = log_file.read_text().strip().splitlines()
        return [json.loads(l) for l in lines[-n:] if l.strip()]

    def daily_order_count(self) -> int:
        return len(self.recent_orders(n=999))

    # ── Safety enforcement ─────────────────────────────────────────────────────

    def _enforce_safety_env(self) -> None:
        env_val = os.getenv("OANDA_ENVIRONMENT", "practice").lower()
        if env_val == "live":
            raise OandaSafetyError(
                "[OANDA BLOCKED] OANDA_ENVIRONMENT=live is not allowed. "
                "This adapter is practice-only."
            )
        allow_live = os.getenv("OANDA_ALLOW_LIVE", "false").lower()
        if allow_live in ("true", "1", "yes"):
            raise OandaSafetyError(
                "[OANDA BLOCKED] OANDA_ALLOW_LIVE=true is not allowed. "
                "Set OANDA_ALLOW_LIVE=false."
            )

    def _enforce_demo_enabled(self) -> None:
        enabled = os.getenv("OANDA_DEMO_ENABLED", "false").lower()
        if enabled not in ("true", "1", "yes"):
            raise OandaSafetyError(
                "[OANDA BLOCKED] OANDA_DEMO_ENABLED is not set to true. "
                "Ray approval required before placing demo orders."
            )

    def _enforce_units(self, units: int) -> None:
        if abs(units) > MAX_UNITS:
            raise OandaSafetyError(
                f"[OANDA BLOCKED] units={units} exceeds OANDA_MAX_UNITS={MAX_UNITS}. "
                "Max 1 unit per order."
            )

    def _enforce_daily_limit(self) -> None:
        count = self.daily_order_count()
        if count >= MAX_DAILY_ORDERS:
            raise OandaSafetyError(
                f"[OANDA BLOCKED] Daily order limit reached ({count}/{MAX_DAILY_ORDERS}). "
                "No more demo orders today."
            )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        # Token never logged
        return {"Authorization": f"Bearer {self._token}"}

    def _ssl_context(self):
        cert_file = os.getenv("SSL_CERT_FILE", "")
        if not cert_file:
            try:
                import certifi
                cert_file = certifi.where()
            except Exception:
                cert_file = ""
        if cert_file:
            return ssl.create_default_context(cafile=cert_file)
        return None

    def _log_order(self, result: dict, reason: str) -> None:
        record = {**result, "reason": reason, "logged_at": datetime.utcnow().isoformat() + "Z"}
        log_file = REPORTS_DIR / f"demo_orders_{date.today().isoformat()}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(record) + "\n")

    def _fail(self, error: str, **extra) -> dict[str, Any]:
        return {"ok": False, "environment": "practice", "error": error, **extra}
