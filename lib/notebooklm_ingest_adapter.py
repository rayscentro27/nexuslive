from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import argparse
import hashlib
import json
import os
import subprocess
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports" / "knowledge_intake"
QUEUE_FILE = REPORT_DIR / "notebooklm_intake_queue.json"
NLM_BIN = ROOT / ".venv-notebooklm" / "bin" / "nlm"

NOTEBOOK_DOMAIN_MAP = {
    "Nexus Grants": "grants",
    "Nexus Trading": "trading",
    "Nexus Funding": "funding",
    "Nexus Credit": "credit",
    "Nexus Business Opportunities": "business_opportunities",
    "Nexus Marketing": "marketing",
    "Nexus Operations": "operations",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_nlm(args: list[str]) -> tuple[bool, str]:
    if not NLM_BIN.exists():
        return False, "nlm_binary_missing"
    p = subprocess.run([str(NLM_BIN), *args], capture_output=True, text=True)
    out = ((p.stdout or "") + (p.stderr or "")).strip()
    return p.returncode == 0, out


def cli_capability_check() -> dict[str, Any]:
    installed = NLM_BIN.exists()
    ok_auth, auth_out = _run_nlm(["auth", "status"])
    ok_list, list_help = _run_nlm(["notebook", "list", "--help"])
    ok_source, source_help = _run_nlm(["source", "list", "--help"])
    return {
        "timestamp": _now(),
        "binary": str(NLM_BIN),
        "installed": installed,
        "auth_ok": ok_auth,
        "authenticated": "Not authenticated" not in auth_out,
        "auth_status": auth_out[:600],
        "can_list_notebooks": ok_list and "--json" in list_help,
        "can_list_sources": ok_source and "--json" in source_help,
        "can_pull_notebook_summary": True,
    }


def _safe_json(out: str) -> Any:
    try:
        return json.loads(out)
    except Exception:
        return None


def list_notebooks() -> list[dict[str, Any]]:
    ok, out = _run_nlm(["notebook", "list", "--json"])
    if not ok:
        return []
    data = _safe_json(out)
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def _find_notebook_id(notebook_name: str) -> str:
    target = notebook_name.strip().lower()
    for row in list_notebooks():
        if str(row.get("title") or "").strip().lower() == target:
            return str(row.get("id") or "")
    return ""


def _notebook_describe(notebook_id: str) -> str:
    ok, out = _run_nlm(["notebook", "describe", notebook_id])
    return out.strip() if ok else ""


def _source_list(notebook_id: str) -> list[dict[str, Any]]:
    ok, out = _run_nlm(["source", "list", notebook_id, "--json"])
    if not ok:
        return []
    data = _safe_json(out)
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


def _source_get(source_id: str) -> dict[str, Any]:
    ok, out = _run_nlm(["source", "get", source_id, "--json"])
    if not ok:
        return {}
    data = _safe_json(out)
    return data if isinstance(data, dict) else {}


def _source_type_from_url(url: str) -> str:
    u = (url or "").lower()
    if "youtube.com/" in u or "youtu.be/" in u:
        return "youtube"
    if url:
        return "website"
    return "notebooklm"


def _quality_score(summary: str, insight_count: int, source_count: int) -> int:
    score = 45
    if len(summary) > 120:
        score += 10
    if len(summary) > 400:
        score += 10
    score += min(15, insight_count * 3)
    score += min(10, source_count * 2)
    return max(35, min(score, 93))


def _insights(summary: str) -> list[str]:
    parts = [p.strip(" -") for p in summary.replace("\r", "").split("\n") if p.strip()]
    return parts[:8]


def _dedup_key(notebook_name: str, source_urls: list[str], summary: str) -> str:
    base = f"{notebook_name}|{'|'.join(source_urls[:20])}|{summary[:240]}"
    return hashlib.sha256(base.encode()).hexdigest()[:24]


def build_proposed_record(note: dict[str, Any]) -> dict[str, Any]:
    notebook_name = str(note.get("notebook_name") or "Unknown Notebook").strip()
    domain = str(note.get("domain") or "operations").strip().lower()
    summary = str(note.get("summary") or "").strip()
    source_urls = [str(u).strip() for u in (note.get("source_urls") or []) if str(u).strip()]
    insights = [str(x).strip() for x in (note.get("insights") or []) if str(x).strip()]
    source_count = int(note.get("source_count") or len(source_urls))
    score = _quality_score(summary, len(insights), source_count)
    return {
        "title": f"[Proposed] NotebookLM: {notebook_name}",
        "domain": domain,
        "content": summary[:4000],
        "source_url": source_urls[0] if source_urls else f"notebooklm://{urllib.parse.quote(notebook_name)}",
        "source_type": "notebooklm",
        "status": "proposed",
        "quality_score": score,
        "freshness_status": "fresh",
        "metadata": {
            "source_name": notebook_name,
            "review_required": True,
            "source_urls": source_urls[:50],
            "source_count": source_count,
            "insights": insights[:12],
            "notebook_updated_at": note.get("updated_at"),
            "notebook_created_at": note.get("created_at"),
            "dedup_key": _dedup_key(notebook_name, source_urls, summary),
        },
        "dry_run": bool(note.get("dry_run", True)),
        "created_at": _now(),
    }


def summarize_intake_queue(records: list[dict[str, Any]]) -> str:
    if not records:
        return "NotebookLM intake queue is empty (dry-run)."
    lines = [f"NotebookLM dry-run queue: {len(records)} item(s)"]
    for row in records[:6]:
        lines.append(f"- {row.get('metadata', {}).get('source_name') or row.get('title')} | {row.get('domain')} | score={row.get('quality_score')}")
    return "\n".join(lines)


def load_dry_run_queue(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    return []


def _save_dry_run_queue(rows: list[dict[str, Any]]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def _supabase_base() -> str:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    if not url:
        raise RuntimeError("SUPABASE_URL not configured")
    return f"{url}/rest/v1"


def _supabase_headers() -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not key:
        raise RuntimeError("Supabase service key not configured")
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _supabase_get(path: str, params: dict[str, str]) -> list[dict[str, Any]]:
    url = f"{_supabase_base()}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=_supabase_headers(), method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode() or "[]")


def _supabase_post(path: str, payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    req = urllib.request.Request(
        f"{_supabase_base()}/{path}",
        headers={**_supabase_headers(), "Prefer": "return=representation"},
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode() or "[]")


def _existing_dedup_keys() -> set[str]:
    rows = _supabase_get("knowledge_items", {"select": "metadata", "status": "eq.proposed", "limit": "300"})
    out: set[str] = set()
    for r in rows:
        md = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
        k = str(md.get("dedup_key") or "")
        if k:
            out.add(k)
    return out


def _build_transcript_rows(notebook_name: str, domain: str, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for s in sources[:10]:
        url = str(s.get("url") or "").strip()
        if _source_type_from_url(url) != "youtube":
            continue
        rows.append(
            {
                "title": f"NotebookLM source: {notebook_name}",
                "source_url": url,
                "source_type": "youtube",
                "raw_content": "",
                "cleaned_content": "",
                "extraction_notes": f"notebooklm source import; notebook={notebook_name}",
                "quality_label": "low",
                "status": "needs_transcript",
                "domain": domain,
                "metadata": {"source_name": notebook_name, "ingestion_category": domain, "review_required": True},
            }
        )
    return rows


def fetch_named_notebook_payload(notebook_name: str) -> dict[str, Any]:
    notebook_id = _find_notebook_id(notebook_name)
    if not notebook_id:
        return {"ok": False, "error": "notebook_not_found", "notebook_name": notebook_name}
    details_ok, details_out = _run_nlm(["notebook", "get", notebook_id, "--json"])
    details = _safe_json(details_out) if details_ok else {}
    details = details if isinstance(details, dict) else {}
    summary = _notebook_describe(notebook_id)
    sources_raw = _source_list(notebook_id)
    sources: list[dict[str, Any]] = []
    for row in sources_raw[:20]:
        sid = str(row.get("id") or "")
        full = _source_get(sid) if sid else {}
        merged = {**row, **full}
        sources.append(
            {
                "id": sid,
                "title": str(merged.get("title") or merged.get("name") or "source"),
                "url": str(merged.get("url") or merged.get("sourceUrl") or ""),
                "type": str(merged.get("type") or "unknown"),
                "created_at": merged.get("created_at") or merged.get("createdAt"),
                "updated_at": merged.get("updated_at") or merged.get("updatedAt"),
            }
        )
    return {
        "ok": True,
        "notebook_name": notebook_name,
        "notebook_id": notebook_id,
        "summary": summary,
        "sources": sources,
        "created_at": details.get("created_at") or details.get("createdAt"),
        "updated_at": details.get("updated_at") or details.get("updatedAt"),
    }


def ingest_named_notebook(notebook_name: str, apply: bool = False) -> dict[str, Any]:
    domain = NOTEBOOK_DOMAIN_MAP.get(notebook_name, "operations")
    payload = fetch_named_notebook_payload(notebook_name)
    if not payload.get("ok"):
        return payload
    sources = payload.get("sources") or []
    source_urls = [str(s.get("url") or "").strip() for s in sources if str(s.get("url") or "").strip()]
    summary = str(payload.get("summary") or "").strip() or f"NotebookLM notebook '{notebook_name}' ingestion summary pending."
    proposed = build_proposed_record(
        {
            "notebook_name": notebook_name,
            "domain": domain,
            "summary": summary,
            "source_urls": source_urls,
            "source_count": len(sources),
            "insights": _insights(summary),
            "created_at": payload.get("created_at"),
            "updated_at": payload.get("updated_at"),
            "dry_run": not apply,
        }
    )
    queue = load_dry_run_queue(str(QUEUE_FILE))
    dedup_key = ((proposed.get("metadata") or {}).get("dedup_key") or "")
    in_queue = any(((r.get("metadata") or {}).get("dedup_key") or "") == dedup_key for r in queue)
    duplicates = 1 if in_queue else 0
    inserted_knowledge = 0
    inserted_transcripts = 0
    errors: list[str] = []

    if apply:
        try:
            existing_keys = _existing_dedup_keys()
            if dedup_key in existing_keys:
                duplicates += 1
            else:
                inserted_knowledge = len(_supabase_post("knowledge_items", [proposed]))
                t_rows = _build_transcript_rows(notebook_name, domain, sources)
                if t_rows:
                    inserted_transcripts = len(_supabase_post("transcript_queue", t_rows))
        except Exception as exc:
            errors.append(str(exc))
    else:
        if not in_queue:
            queue.append(proposed)
            queue = queue[-1200:]
            _save_dry_run_queue(queue)

    return {
        "ok": not errors,
        "apply": apply,
        "notebook_name": notebook_name,
        "domain": domain,
        "sources_found": len(sources),
        "source_urls_found": len(source_urls),
        "duplicates": duplicates,
        "knowledge_rows_inserted": inserted_knowledge,
        "transcript_rows_inserted": inserted_transcripts,
        "proposed_record": proposed,
        "errors": errors,
    }


def ingest_all_configured(apply: bool = False) -> dict[str, Any]:
    results = [ingest_named_notebook(name, apply=apply) for name in NOTEBOOK_DOMAIN_MAP.keys()]
    return {
        "ok": all(bool(r.get("ok")) for r in results),
        "apply": apply,
        "results": results,
        "attempted": len(results),
        "success": sum(1 for r in results if r.get("ok")),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="NotebookLM named notebook ingestion adapter")
    p.add_argument("--notebook", help="Notebook name to ingest")
    p.add_argument("--all-configured", action="store_true", help="Ingest all configured named notebooks")
    p.add_argument("--dry-run", action="store_true", help="Dry-run mode (default)")
    p.add_argument("--apply", action="store_true", help="Write proposed records to Supabase")
    p.add_argument("--capability-check", action="store_true", help="Print CLI capability/auth diagnostics")
    args = p.parse_args()

    if args.capability_check:
        print(json.dumps(cli_capability_check(), indent=2))
        return 0

    apply = bool(args.apply)
    if args.all_configured:
        print(json.dumps(ingest_all_configured(apply=apply), indent=2))
        return 0
    if args.notebook:
        print(json.dumps(ingest_named_notebook(args.notebook, apply=apply), indent=2))
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
