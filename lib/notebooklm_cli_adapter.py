from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import subprocess

from lib.notebooklm_ingest_adapter import (
    NOTEBOOK_DOMAIN_MAP,
    QUEUE_FILE,
    cli_capability_check,
    fetch_named_notebook_payload,
    ingest_named_notebook,
    load_dry_run_queue,
)


ROOT = Path(__file__).resolve().parent.parent
REGISTRY_FILE = ROOT / "notebooklm" / "notebook_registry.json"
NLM_BIN = ROOT / ".venv-notebooklm" / "bin" / "nlm"
MAX_ITEMS_DEFAULT = 20

DEFAULT_REGISTRY = {
    "version": 1,
    "updated_at": None,
    "notebooks": [
        {"notebook_id": "forex", "notebook_name": "Nexus Trading", "category": "forex_trading", "description": "Forex trading notes and setups.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.65, "enabled": True, "max_items_per_sync": 15, "destination_domain": "trading"},
        {"notebook_id": "options", "notebook_name": "Nexus Trading", "category": "options_trading", "description": "Options playbooks and risk rules.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.65, "enabled": True, "max_items_per_sync": 15, "destination_domain": "trading"},
        {"notebook_id": "crypto", "notebook_name": "Nexus Trading", "category": "crypto_trading", "description": "Crypto strategy concepts and execution notes.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.62, "enabled": True, "max_items_per_sync": 15, "destination_domain": "trading"},
        {"notebook_id": "stocks", "notebook_name": "Nexus Trading", "category": "stock_trading", "description": "Stock trading ideas and pattern lessons.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.62, "enabled": True, "max_items_per_sync": 15, "destination_domain": "trading"},
        {"notebook_id": "funding", "notebook_name": "Nexus Funding", "category": "business_funding", "description": "Funding readiness and capital access notes.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.72, "enabled": True, "max_items_per_sync": 20, "destination_domain": "funding"},
        {"notebook_id": "credit", "notebook_name": "Nexus Credit", "category": "business_credit", "description": "Business credit frameworks and underwriting insights.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.71, "enabled": True, "max_items_per_sync": 20, "destination_domain": "credit"},
        {"notebook_id": "grants", "notebook_name": "Nexus Grants", "category": "grants", "description": "Grant matching, eligibility, and application intelligence.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.74, "enabled": True, "max_items_per_sync": 20, "destination_domain": "grants"},
        {"notebook_id": "automation", "notebook_name": "Nexus Operations", "category": "ai_automation", "description": "AI automation workflows and operational implementation notes.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.7, "enabled": True, "max_items_per_sync": 20, "destination_domain": "operations"},
        {"notebook_id": "opportunities", "notebook_name": "Nexus Business Opportunities", "category": "business_opportunities", "description": "Low-cost business opportunities and monetization intelligence.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.7, "enabled": True, "max_items_per_sync": 20, "destination_domain": "business_opportunities"},
        {"notebook_id": "marketing", "notebook_name": "Nexus Marketing", "category": "marketing", "description": "Marketing and content growth insights.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.68, "enabled": True, "max_items_per_sync": 20, "destination_domain": "marketing"},
        {"notebook_id": "operations", "notebook_name": "Nexus Operations", "category": "operations", "description": "Operational intelligence and execution guidance.", "source_type": "notebooklm", "sync_status": "idle", "last_sync_at": None, "last_ingested_at": None, "confidence": 0.69, "enabled": True, "max_items_per_sync": 20, "destination_domain": "operations"},
    ],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(text: str) -> str:
    raw = str(text or "")
    for key in ["token", "access_token", "refresh_token", "authorization", "cookie", "session"]:
        raw = raw.replace(key, "[REDACTED_KEY]")
        raw = raw.replace(key.upper(), "[REDACTED_KEY]")
    return raw


def _run_nlm(args: list[str], timeout_seconds: int = 18) -> tuple[bool, str]:
    if not NLM_BIN.exists():
        return False, "nlm_binary_missing"
    try:
        p = subprocess.run([str(NLM_BIN), *args], capture_output=True, text=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return False, "nlm_timeout"
    except Exception as exc:
        return False, f"nlm_error:{exc.__class__.__name__}"
    out = _redact(((p.stdout or "") + (p.stderr or "")).strip())
    return p.returncode == 0, out


def ensure_registry() -> dict[str, Any]:
    if REGISTRY_FILE.exists():
        payload = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload.setdefault("notebooks", [])
            return payload
        return {**DEFAULT_REGISTRY, "updated_at": _now()}
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {**DEFAULT_REGISTRY, "updated_at": _now()}
    REGISTRY_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def load_registry() -> dict[str, Any]:
    if not REGISTRY_FILE.exists():
        ensure_registry()
    payload = json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {**DEFAULT_REGISTRY, "updated_at": _now()}
    payload.setdefault("notebooks", [])
    return payload


def save_registry(payload: dict[str, Any]) -> None:
    payload["updated_at"] = _now()
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def list_notebooks() -> list[dict[str, Any]]:
    ok, out = _run_nlm(["notebook", "list", "--json"])
    if not ok:
        return []
    try:
        rows = json.loads(out)
    except Exception:
        return []
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def get_notebook_sources(notebook_id: str) -> list[dict[str, Any]]:
    ok, out = _run_nlm(["source", "list", notebook_id, "--json"])
    if not ok:
        return []
    try:
        rows = json.loads(out)
    except Exception:
        return []
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _registry_row(notebook_id: str) -> dict[str, Any] | None:
    reg = load_registry()
    for row in reg.get("notebooks") or []:
        if str(row.get("notebook_id") or "").strip().lower() == notebook_id.strip().lower():
            return row
    return None


def export_notebook(notebook_id: str) -> dict[str, Any]:
    row = _registry_row(notebook_id)
    if not row:
        return {"ok": False, "error": "registry_not_found", "notebook_id": notebook_id}
    name = str(row.get("notebook_name") or "").strip()
    if not name:
        return {"ok": False, "error": "registry_name_missing", "notebook_id": notebook_id}
    payload = fetch_named_notebook_payload(name)
    if not payload.get("ok"):
        return payload
    sources = payload.get("sources") or []
    max_items = int(row.get("max_items_per_sync") or MAX_ITEMS_DEFAULT)
    payload["sources"] = sources[: max(1, min(max_items, 50))]
    payload["registry_notebook_id"] = notebook_id
    payload["category"] = row.get("category")
    payload["destination_domain"] = row.get("destination_domain")
    return payload


def normalize_notebook_export(raw: dict[str, Any]) -> dict[str, Any]:
    if not raw.get("ok"):
        return {"ok": False, "error": raw.get("error") or "export_failed"}
    sources = raw.get("sources") or []
    normalized_sources: list[dict[str, Any]] = []
    seen: set[str] = set()
    for src in sources:
        url = str(src.get("url") or "").strip()
        title = str(src.get("title") or "source").strip()
        base = f"{url}|{title}".strip("|")
        dedup = hashlib.sha256(base.encode()).hexdigest()[:24] if base else ""
        if dedup and dedup in seen:
            continue
        if dedup:
            seen.add(dedup)
        normalized_sources.append(
            {
                "source_id": src.get("id"),
                "title": title,
                "url": url,
                "source_type": src.get("type") or "unknown",
                "hash": dedup,
            }
        )
    return {
        "ok": True,
        "notebook_id": raw.get("registry_notebook_id"),
        "notebook_name": raw.get("notebook_name"),
        "category": raw.get("category"),
        "destination_domain": raw.get("destination_domain") or NOTEBOOK_DOMAIN_MAP.get(str(raw.get("notebook_name") or ""), "operations"),
        "summary": str(raw.get("summary") or "").strip(),
        "source_count": len(normalized_sources),
        "sources": normalized_sources,
        "updated_at": raw.get("updated_at"),
    }


def build_ingestion_jobs(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    if not normalized.get("ok"):
        return []
    return [
        {
            "job_type": "notebooklm_ingest",
            "notebook_id": normalized.get("notebook_id"),
            "notebook_name": normalized.get("notebook_name"),
            "domain": normalized.get("destination_domain") or "operations",
            "source_count": normalized.get("source_count") or 0,
            "dedup_keys": [s.get("hash") for s in normalized.get("sources") or [] if s.get("hash")],
        }
    ]


def _update_registry_status(notebook_id: str, *, status: str, last_ingested_at: str | None = None, confidence: float | None = None) -> None:
    reg = load_registry()
    rows = reg.get("notebooks") or []
    for row in rows:
        if str(row.get("notebook_id") or "").strip().lower() == notebook_id.strip().lower():
            row["sync_status"] = status
            row["last_sync_at"] = _now()
            if last_ingested_at:
                row["last_ingested_at"] = last_ingested_at
            if confidence is not None:
                row["confidence"] = round(max(0.0, min(float(confidence), 1.0)), 2)
            break
    reg["notebooks"] = rows
    save_registry(reg)


def dry_run_sync(notebook_id: str) -> dict[str, Any]:
    exported = export_notebook(notebook_id)
    normalized = normalize_notebook_export(exported)
    jobs = build_ingestion_jobs(normalized)
    if not normalized.get("ok"):
        _update_registry_status(notebook_id, status="error")
        return {"ok": False, "error": normalized.get("error"), "jobs": []}
    _update_registry_status(notebook_id, status="dry_run_ready", confidence=0.7 if normalized.get("source_count", 0) > 0 else 0.4)
    return {"ok": True, "mode": "dry_run", "normalized": normalized, "jobs": jobs}


def apply_sync(notebook_id: str) -> dict[str, Any]:
    row = _registry_row(notebook_id)
    if not row:
        return {"ok": False, "error": "registry_not_found", "notebook_id": notebook_id}
    result = ingest_named_notebook(str(row.get("notebook_name") or ""), apply=True)
    if result.get("ok"):
        _update_registry_status(notebook_id, status="synced", last_ingested_at=_now(), confidence=0.78)
    else:
        _update_registry_status(notebook_id, status="error")
    return result


def sync_notebook(notebook_id: str, *, apply: bool = False) -> dict[str, Any]:
    return apply_sync(notebook_id) if apply else dry_run_sync(notebook_id)


def sync_enabled(*, apply: bool = False) -> dict[str, Any]:
    reg = load_registry()
    out = []
    for row in reg.get("notebooks") or []:
        if not bool(row.get("enabled")):
            continue
        out.append(sync_notebook(str(row.get("notebook_id") or ""), apply=apply))
    return {"ok": all(bool(r.get("ok")) for r in out), "count": len(out), "results": out}


def notebook_sync_status() -> dict[str, Any]:
    reg = load_registry()
    queue = load_dry_run_queue(str(QUEUE_FILE))
    return {
        "ok": True,
        "registry_count": len(reg.get("notebooks") or []),
        "enabled_count": len([r for r in reg.get("notebooks") or [] if bool(r.get("enabled"))]),
        "pending_review_count": len(queue),
        "registry": reg,
    }


def discovery() -> dict[str, Any]:
    caps = cli_capability_check()
    ok_help, help_text = _run_nlm(["--help"], timeout_seconds=8)
    return {
        "timestamp": _now(),
        "capabilities": caps,
        "headless_help_ok": ok_help,
        "help_preview": _redact(help_text[:300]),
        "registry_file": str(REGISTRY_FILE),
    }
