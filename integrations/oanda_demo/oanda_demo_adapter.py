"""
OANDA Practice-Environment Demo Adapter
Safety: practice only, max 1 unit, max 3 daily orders, OANDA_ALLOW_LIVE=false enforced.
"""
from __future__ import annotations

import json
import os
import socket
import ssl
import time
import urllib.parse
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
        self._api_base = self._practice_api_base()

    # ── Public API ─────────────────────────────────────────────────────────────

    def connection_status(self) -> dict[str, Any]:
        """Return practice account status without placing any order."""
        self._enforce_safety_env()
        if not self._account_id or not self._token:
            return {"ok": False, "error": "OANDA_ACCOUNT_ID or OANDA_ACCESS_TOKEN/OANDA_API_KEY not set", "environment": "practice"}
        try:
            data = self._request_json(f"/accounts/{self._account_id}")
            return {
                "ok": True,
                "environment": "practice",
                "account_id": self._account_id,
                "api_base": self._api_base,
                "endpoint_host": urllib.parse.urlparse(self._api_base).hostname,
                "currency": data.get("account", {}).get("currency", ""),
                "balance": data.get("account", {}).get("balance", ""),
                "nav": data.get("account", {}).get("NAV", ""),
            }
        except Exception as e:
            return {
                "ok": False,
                "environment": "practice",
                "api_base": self._api_base,
                "endpoint_host": urllib.parse.urlparse(self._api_base).hostname,
                "dns_preflight": self.dns_preflight(),
                "error": str(e),
            }

    def practice_endpoint_info(self) -> dict[str, Any]:
        parsed = urllib.parse.urlparse(self._api_base)
        return {
            "api_base": self._api_base,
            "hostname": parsed.hostname,
            "scheme": parsed.scheme,
            "path": parsed.path,
            "dns_preflight": self.dns_preflight(),
        }

    def dns_preflight(self) -> dict[str, Any]:
        host = urllib.parse.urlparse(self._api_base).hostname or ""
        if not host:
            return {"ok": False, "hostname": host, "error": "missing_hostname"}
        try:
            infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            ips = sorted({row[4][0] for row in infos})
            return {"ok": True, "hostname": host, "ip_count": len(ips), "ips": ips[:6]}
        except Exception as exc:
            return {"ok": False, "hostname": host, "error": str(exc)}

    def account_summary(self) -> dict[str, Any]:
        self._enforce_safety_env()
        return self._request_json(f"/accounts/{self._account_id}/summary")

    def available_instruments(self) -> dict[str, Any]:
        self._enforce_safety_env()
        return self._request_json(f"/accounts/{self._account_id}/instruments")

    def get_pricing(self, instrument: str) -> dict[str, Any]:
        self._enforce_safety_env()
        query = urllib.parse.urlencode({"instruments": instrument})
        return self._request_json(f"/accounts/{self._account_id}/pricing?{query}")

    def order_payload(
        self,
        *,
        instrument: str,
        side: str,
        units: int,
        stop_loss: float,
        take_profit: float,
        client_tag: str = "",
    ) -> dict[str, Any]:
        self._enforce_safety_env()
        self._enforce_units(units)
        signed_units = units if side.lower() == "buy" else -units
        order: dict[str, Any] = {
            "type": "MARKET",
            "instrument": instrument,
            "units": str(signed_units),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {
                "timeInForce": "GTC",
                "price": self._format_price(stop_loss),
            },
            "takeProfitOnFill": {
                "timeInForce": "GTC",
                "price": self._format_price(take_profit),
            },
        }
        if client_tag:
            order["clientExtensions"] = {
                "tag": client_tag[:128],
                "comment": "nexus_practice_demo_test"[:128],
            }
        return {"order": order}

    def place_demo_order(
        self,
        instrument: str,
        side: str,
        units: int = 1,
        stop_loss: float | None = None,
        take_profit: float | None = None,
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
        if stop_loss in (None, "", 0) or take_profit in (None, "", 0):
            return self._fail("stop_loss and take_profit are required for demo execution tests")
        order_payload = self.order_payload(
            instrument=instrument,
            side=side,
            units=units,
            stop_loss=float(stop_loss),
            take_profit=float(take_profit),
            client_tag=reason,
        )
        order_body = json.dumps(order_payload).encode()

        try:
            data = self._request_json(
                f"/accounts/{self._account_id}/orders",
                method="POST",
                body=order_body,
            )
            fill = data.get("orderFillTransaction", {}) or {}
            create = data.get("orderCreateTransaction", {}) or {}
            cancel = data.get("orderCancelTransaction") or {}
            if cancel:
                cancel_reason = cancel.get("reason", "unknown")
                result = {
                    "ok": False,
                    "environment": "practice",
                    "instrument": instrument,
                    "side": side,
                    "units": units,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "reason": reason,
                    "cancel_reason": cancel_reason,
                    "cancel_transaction_id": cancel.get("id"),
                    "error": f"OANDA canceled order: {cancel_reason}",
                    "order_id": cancel.get("orderID") or create.get("id"),
                    "trade_id": None,
                    "stop_loss_order_id": None,
                    "take_profit_order_id": None,
                    "order_create": create,
                    "order_cancel": cancel,
                    "order_fill": fill,
                    "last_transaction_id": data.get("lastTransactionID"),
                    "related_transaction_ids": data.get("relatedTransactionIDs", []),
                    "broker_response": data,
                    "placed_at": datetime.utcnow().isoformat() + "Z",
                }
            else:
                result = {
                    "ok": True,
                    "environment": "practice",
                    "instrument": instrument,
                    "side": side,
                    "units": units,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "reason": reason,
                    "order_create": create,
                    "order_fill": fill,
                    "last_transaction_id": data.get("lastTransactionID"),
                    "related_transaction_ids": data.get("relatedTransactionIDs", []),
                    "order_id": create.get("id") or fill.get("orderID"),
                    "trade_id": self._extract_trade_id(fill),
                    "stop_loss_order_id": fill.get("stopLossOrder", {}).get("id"),
                    "take_profit_order_id": fill.get("takeProfitOrder", {}).get("id"),
                    "broker_response": data,
                    "placed_at": datetime.utcnow().isoformat() + "Z",
                }
        except Exception as e:
            result = self._fail(
                str(e),
                instrument=instrument,
                side=side,
                units=units,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

        self._log_order(result, reason)
        return result

    def order_state(self, order_id: str) -> dict[str, Any]:
        self._enforce_safety_env()
        return self._request_json(f"/accounts/{self._account_id}/orders/{order_id}")

    def trade_state(self, trade_id: str) -> dict[str, Any]:
        self._enforce_safety_env()
        return self._request_json(f"/accounts/{self._account_id}/trades/{trade_id}")

    def open_trades(self) -> dict[str, Any]:
        self._enforce_safety_env()
        return self._request_json(f"/accounts/{self._account_id}/openTrades")

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
        normalized = self._normalize_practice_url(os.getenv("OANDA_API_URL", PRACTICE_API_BASE))
        host = urllib.parse.urlparse(normalized).hostname or ""
        if "fxtrade" in normalized or "live" in host:
            raise OandaSafetyError(
                "[OANDA BLOCKED] Live OANDA endpoint detected in OANDA_API_URL. Practice only."
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

    def _practice_api_base(self) -> str:
        configured = os.getenv("OANDA_API_URL", PRACTICE_API_BASE)
        return self._normalize_practice_url(configured)

    def _normalize_practice_url(self, value: str) -> str:
        raw = (value or "").strip()
        if not raw:
            return PRACTICE_API_BASE
        if "://" not in raw:
            raw = f"https://{raw}"
        parsed = urllib.parse.urlparse(raw)
        host = (parsed.hostname or "").lower()
        if "fxtrade" in host:
            raise OandaSafetyError("[OANDA BLOCKED] Live OANDA hostname is not allowed.")
        if host and host != "api-fxpractice.oanda.com":
            # Keep explicit practice host only; anything else is treated as malformed.
            raise OandaSafetyError(f"[OANDA BLOCKED] Unexpected OANDA practice host: {host}")
        scheme = parsed.scheme or "https"
        path = parsed.path or "/v3"
        if not path.endswith("/v3"):
            path = path.rstrip("/")
            if not path.endswith("/v3"):
                path = f"{path}/v3" if path else "/v3"
        return urllib.parse.urlunparse((scheme, "api-fxpractice.oanda.com", path, "", "", ""))

    def _request_json(self, path: str, *, method: str = "GET", body: bytes | None = None) -> dict[str, Any]:
        import urllib.error
        import urllib.request

        url = f"{self._api_base}{path}"
        attempts = 3
        errors: list[str] = []
        for attempt in range(1, attempts + 1):
            headers = self._headers()
            if body is not None:
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(
                url,
                data=body,
                headers=headers,
                method=method,
            )
            try:
                with urllib.request.urlopen(req, timeout=15, context=self._ssl_context()) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = {"errorMessage": raw}
                raise RuntimeError(f"HTTP {exc.code}: {json.dumps(payload)}") from exc
            except Exception as exc:
                errors.append(f"attempt_{attempt}:{exc}")
                dns = self.dns_preflight()
                if attempt >= attempts:
                    raise RuntimeError(f"{exc} | dns_preflight={json.dumps(dns)} | attempts={errors}") from exc
                time.sleep(0.75 * attempt)

    def _format_price(self, value: float) -> str:
        return f"{float(value):.5f}"

    def _extract_trade_id(self, fill: dict[str, Any]) -> str | None:
        opened = fill.get("tradeOpened") or {}
        reduced = fill.get("tradeReduced") or {}
        closed = fill.get("tradesClosed") or []
        return (
            opened.get("tradeID")
            or reduced.get("tradeID")
            or (closed[0].get("tradeID") if closed else None)
        )

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
