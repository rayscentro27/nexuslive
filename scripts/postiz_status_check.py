#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "reports" / "showroom" / "postiz_status.md"
OUT_JSON = ROOT / "logs" / "postiz_status_latest.json"


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def env_present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def docker_status() -> dict:
    if not shutil.which("docker"):
        return {"available": False, "running": False, "error": "docker_cli_missing"}
    proc = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}\t{{.Image}}\t{{.Ports}}"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        return {"available": True, "running": False, "error": proc.stderr.strip() or "docker_unavailable"}
    rows = []
    for line in proc.stdout.splitlines():
        if "postiz" in line.lower() or "gitroom" in line.lower():
            rows.append(line)
    return {"available": True, "running": bool(rows), "containers": rows, "error": None}


def main() -> int:
    load_env()
    now = datetime.now(timezone.utc).isoformat()
    docker = docker_status()
    compose_files = []
    for rel in ["reports", "scripts", "integrations", "tool-lab"]:
        base = ROOT / rel
        if not base.exists():
            continue
        for pattern in ("*postiz*", "docker-compose*.yml", "docker-compose*.yaml"):
            for path in base.rglob(pattern):
                if path.is_file() or path.is_dir():
                    item = str(path.relative_to(ROOT))
                    if item not in compose_files:
                        compose_files.append(item)
    compose_files.sort()
    install_markers = [
        item for item in compose_files
        if item.startswith("tool-lab/postiz")
        or "/postiz-app" in item
        or item.endswith("/postiz")
        or item.endswith("/postiz-app")
    ]
    creds = {
        "POSTIZ_URL": env_present("POSTIZ_URL"),
        "POSTIZ_API_KEY": env_present("POSTIZ_API_KEY"),
        "FACEBOOK_PAGE_ID": env_present("FACEBOOK_PAGE_ID"),
        "INSTAGRAM_BUSINESS_ACCOUNT_ID": env_present("INSTAGRAM_BUSINESS_ACCOUNT_ID"),
        "LINKEDIN_CLIENT_ID": env_present("LINKEDIN_CLIENT_ID"),
        "TIKTOK_CLIENT_KEY": env_present("TIKTOK_CLIENT_KEY"),
        "YOUTUBE_CLIENT_ID": env_present("YOUTUBE_CLIENT_ID") or env_present("GOOGLE_CLIENT_ID"),
    }
    payload = {
        "generated_at": now,
        "installed": False,
        "running": docker.get("running", False),
        "local_url": os.getenv("POSTIZ_URL", "").strip() or None,
        "credentials_present": creds,
        "accounts_connected": False,
        "nexus_adapter_exists": False,
        "hermes_adapter_exists": False,
        "approval_gate_exists": (ROOT / "scripts" / "social_publish_executor.py").exists(),
        "draft_only_test_possible": False,
        "auto_post_blocked": True,
        "compose_files": compose_files,
        "install_markers": install_markers,
        "docker": docker,
        "next_approval_needed": "Approve local-only Postiz install/evaluation before any account connection.",
    }
    payload["installed"] = bool(install_markers or payload["local_url"] or payload["credentials_present"]["POSTIZ_URL"])
    payload["draft_only_test_possible"] = bool(payload["installed"] and payload["approval_gate_exists"])

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    lines = [
        "# Postiz Status",
        f"_Generated: {now}_",
        "",
        f"- installed: {'yes' if payload['installed'] else 'no'}",
        f"- running: {'yes' if payload['running'] else 'no'}",
        f"- local url: {payload['local_url'] or 'not configured'}",
        f"- postiz-related files found: {', '.join(compose_files) if compose_files else 'none'}",
        f"- install markers: {', '.join(install_markers) if install_markers else 'none'}",
        f"- accounts connected: {'yes' if payload['accounts_connected'] else 'no'}",
        f"- credentials present (names only): " +
        ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in creds.items()),
        f"- Nexus adapter exists: {'yes' if payload['nexus_adapter_exists'] else 'no'}",
        f"- Hermes adapter exists: {'yes' if payload['hermes_adapter_exists'] else 'no'}",
        f"- approval gate exists: {'yes' if payload['approval_gate_exists'] else 'no'}",
        f"- draft-only test possible: {'yes' if payload['draft_only_test_possible'] else 'no'}",
        f"- auto-post blocked: {'yes' if payload['auto_post_blocked'] else 'no'}",
        f"- docker status: {docker.get('error') or ('running' if docker.get('running') else 'not running')}",
        "",
        "## Safe interpretation",
        "- Postiz is not wired as an active publishing layer yet.",
        "- The existing social publish gate remains the approval boundary.",
        "- Safe next step is a local-only Postiz evaluation, not account connection or publishing.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n")
    print(OUT_MD.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
