#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "logs" / "network_dns_stability_latest.json"
OUT_MD = ROOT / "reports" / "showroom" / "network_dns_stability_report.md"


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def parse_host(url_or_host: str) -> str:
    if "://" in url_or_host:
        parsed = urlparse(url_or_host)
        return parsed.hostname or url_or_host
    return url_or_host


def safe_url(host: str) -> str:
    if host.startswith("api.telegram.org"):
        return "https://api.telegram.org"
    if host.startswith("api-fxpractice.oanda.com"):
        return "https://api-fxpractice.oanda.com/v3/accounts"
    if host.startswith("app.goclearonline.cc"):
        return "https://app.goclearonline.cc"
    if host.startswith("nexuslive.netlify.app"):
        return "https://nexuslive.netlify.app"
    if host.startswith("api.resend.com"):
        return "https://api.resend.com"
    if host.startswith("smtp."):
        return ""
    if host.startswith("http"):
        return host
    return f"https://{host}"


def socket_probe(host: str) -> dict:
    started = time.time()
    try:
        infos = socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)
        ips = sorted({item[4][0] for item in infos})
        return {
            "ok": True,
            "latency_ms": round((time.time() - started) * 1000, 2),
            "ips": ips[:4],
            "error": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "latency_ms": round((time.time() - started) * 1000, 2),
            "ips": [],
            "error": str(exc)[:200],
        }


def dns_tool_probe(host: str) -> dict:
    if shutil.which("dig"):
        proc = subprocess.run(
            ["dig", "+short", host],
            capture_output=True,
            text=True,
            timeout=8,
        )
        ips = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        return {"tool": "dig", "ok": bool(ips), "ips": ips[:4], "error": proc.stderr.strip() or None}
    if shutil.which("nslookup"):
        proc = subprocess.run(
            ["nslookup", host],
            capture_output=True,
            text=True,
            timeout=8,
        )
        ok = "Address:" in proc.stdout
        return {"tool": "nslookup", "ok": ok, "ips": [], "error": proc.stderr.strip() or None}
    return {"tool": "none", "ok": False, "ips": [], "error": "dig/nslookup unavailable"}


def http_probe(host: str) -> dict:
    url = safe_url(host)
    if not url:
        return {"ok": None, "status": None, "latency_ms": None, "error": "no_http_probe_for_host"}
    started = time.time()
    try:
        req = Request(url, method="HEAD")
        with urlopen(req, timeout=8) as resp:
            return {
                "ok": True,
                "status": getattr(resp, "status", None),
                "latency_ms": round((time.time() - started) * 1000, 2),
                "error": None,
            }
    except Exception as exc:
        return {
            "ok": False,
            "status": None,
            "latency_ms": round((time.time() - started) * 1000, 2),
            "error": str(exc)[:200],
        }


def run_target(name: str, host: str, spacing_seconds: int = 2) -> dict:
    attempts = []
    for idx in range(3):
        socket_result = socket_probe(host)
        tool_result = dns_tool_probe(host)
        http_result = http_probe(host)
        attempts.append(
            {
                "attempt": idx + 1,
                "socket": socket_result,
                "dns_tool": tool_result,
                "http": http_result,
                "passed": bool(socket_result["ok"]),
            }
        )
        if idx < 2:
            time.sleep(spacing_seconds)
    passes = sum(1 for attempt in attempts if attempt["passed"])
    if passes == 3:
        status = "DNS_STABLE"
    elif passes == 0:
        status = "DNS_BLOCKED"
    else:
        status = "DNS_INTERMITTENT"
    return {"name": name, "host": host, "status": status, "attempts": attempts}


def classify_overall(results: list[dict]) -> str:
    statuses = {row["status"] for row in results}
    if statuses == {"DNS_STABLE"}:
        return "DNS_STABLE"
    if statuses == {"DNS_BLOCKED"}:
        return "DNS_BLOCKED"
    if "DNS_INTERMITTENT" in statuses:
        return "DNS_INTERMITTENT"
    stable_count = sum(1 for row in results if row["status"] == "DNS_STABLE")
    blocked_count = sum(1 for row in results if row["status"] == "DNS_BLOCKED")
    if stable_count and blocked_count:
        return "PROVIDER_SPECIFIC_FAILURE"
    return "DNS_INTERMITTENT"


def recommendations(classification: str, result_map: dict[str, dict]) -> dict:
    telegram_safe = result_map["telegram"]["status"] == "DNS_STABLE"
    email_safe = result_map["email"]["status"] == "DNS_STABLE"
    oanda_safe = result_map["oanda"]["status"] == "DNS_STABLE"
    supabase_safe = result_map["supabase"]["status"] == "DNS_STABLE"
    return {
        "telegram_retry_safe": telegram_safe,
        "email_retry_safe": email_safe,
        "oanda_retry_should_wait": not oanda_safe,
        "supabase_dry_run_should_wait": not supabase_safe,
        "recommended_retry_timing": (
            "safe now"
            if classification == "DNS_STABLE"
            else "wait for a stable resolver window and re-run this diagnostic first"
        ),
    }


def main() -> int:
    load_env()
    supabase_host = parse_host(os.getenv("SUPABASE_URL", ""))
    smtp_host = "smtp.gmail.com"
    if os.getenv("RESEND_API_KEY", "").strip():
        smtp_host = "api.resend.com"
    targets = [
        ("telegram", "api.telegram.org"),
        ("email", smtp_host),
        ("supabase", supabase_host or "missing_supabase_host"),
        ("oanda", "api-fxpractice.oanda.com"),
        ("app", "app.goclearonline.cc"),
        ("netlify", "nexuslive.netlify.app"),
    ]
    results = [run_target(name, host) for name, host in targets]
    result_map = {row["name"]: row for row in results}
    overall = classify_overall(results)
    reco = recommendations(overall, result_map)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "classification": overall,
        "results": results,
        "recommendations": reco,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    lines = [
        "# Network / DNS Stability Report",
        f"_Generated: {payload['generated_at']}_",
        "",
        f"- classification: {overall}",
        "",
        "## Targets",
    ]
    for row in results:
        latencies = [
            str(attempt["socket"]["latency_ms"])
            for attempt in row["attempts"]
            if attempt["socket"]["latency_ms"] is not None
        ]
        lines += [
            f"### {row['name']}",
            f"- host: {row['host']}",
            f"- status: {row['status']}",
            f"- socket latencies ms: {', '.join(latencies) if latencies else 'n/a'}",
            f"- latest socket error: {row['attempts'][-1]['socket']['error'] or 'none'}",
            f"- latest http error: {row['attempts'][-1]['http']['error'] or 'none'}",
            "",
        ]
    lines += [
        "## Recommendations",
        f"- Telegram retry safe: {'yes' if reco['telegram_retry_safe'] else 'no'}",
        f"- Ray-only email retry safe: {'yes' if reco['email_retry_safe'] else 'no'}",
        f"- Oanda one-shot retry should wait: {'yes' if reco['oanda_retry_should_wait'] else 'no'}",
        f"- Supabase dry-run should wait: {'yes' if reco['supabase_dry_run_should_wait'] else 'no'}",
        f"- recommended retry timing: {reco['recommended_retry_timing']}",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(OUT_MD.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
