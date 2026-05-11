"""
Trading task executor.

Consumes trading implementation tasks and turns them into concrete local
artifacts under `generated_trading/`, while optionally queueing a paper-trade
run row for the replay lab to pick up.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
GENERATED_TRADING = ROOT / "generated_trading"

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

SUPPORTED_TEAMS = {"TradingEngine", "ResearchDesk"}


def _headers(prefer: str = "return=representation") -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _sb_get(path: str) -> List[dict]:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _sb_post(table: str, rows: List[dict]) -> List[dict]:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}",
        data=json.dumps(rows).encode(),
        headers=_headers(),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _sb_patch(table: str, query: str, data: dict) -> None:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}?{query}",
        data=json.dumps(data).encode(),
        headers=_headers("return=minimal"),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=20):
        pass


def _quote(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return value or "trading-task"


def _deterministic_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def _active_projects(limit: int = 10) -> List[dict]:
    return _sb_get(
        "implementation_projects"
        "?select=id,recommendation_id,title,status,metadata,created_at"
        "&domain=eq.trading"
        "&project_type=eq.trading_execution"
        "&status=in.(queued,in_progress)"
        "&order=created_at.asc"
        f"&limit={limit}"
    )


def _project_tasks(project_id: str) -> List[dict]:
    rows = _sb_get(
        "implementation_tasks"
        "?select=id,project_id,task_order,task_type,title,details,assigned_team,status,metadata,updated_at"
        f"&project_id=eq.{_quote(project_id)}"
        "&status=in.(pending,ready,in_progress)"
        "&order=task_order.asc"
    )
    return [row for row in rows if row.get("assigned_team") in SUPPORTED_TEAMS]


def _recommendation(rec_id: str) -> Optional[dict]:
    rows = _sb_get(
        "research_recommendations"
        "?select=id,title,summary,thesis,profitability_path,metadata,source_id,trace_id,category"
        f"&id=eq.{_quote(rec_id)}&limit=1"
    )
    return rows[0] if rows else None


def _proposal(rec: dict) -> Optional[dict]:
    source_id = rec.get("source_id")
    if not source_id:
        return None
    try:
        rows = _sb_get(
            "reviewed_signal_proposals"
            "?select=id,signal_id,symbol,side,timeframe,strategy_id,strategy_type,asset_type,entry_price,stop_loss,take_profit,underlying,expiration_note,strike_note,premium_estimate,delta_guidance,recommendation,trace_id"
            f"&id=eq.{_quote(source_id)}&limit=1"
        )
    except Exception:
        rows = _sb_get(
            "reviewed_signal_proposals"
            "?select=id,signal_id,symbol,side,timeframe,strategy_id,asset_type,entry_price,stop_loss,take_profit,underlying,expiration_note,strike_note,premium_estimate,delta_guidance,recommendation,trace_id"
            f"&id=eq.{_quote(source_id)}&limit=1"
        )
    return rows[0] if rows else None


def _bundle_dir(project: dict) -> Path:
    metadata = dict(project.get("metadata") or {})
    bundle_path = metadata.get("trading_bundle_path")
    if not bundle_path:
        bundle_path = str(GENERATED_TRADING / _slug(project.get("title")))
        metadata["trading_bundle_path"] = bundle_path
        _sb_patch(
            "implementation_projects",
            f"id=eq.{_quote(project['id'])}",
            {
                "status": "in_progress",
                "metadata": metadata,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    path = Path(bundle_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _risk_summary(rec: dict, proposal: Optional[dict]) -> List[str]:
    metadata = rec.get("metadata") or {}
    risk_decision = metadata.get("risk_decision") or {}
    recent_replays = metadata.get("recent_replays") or []
    lines = [
        "## Recommendation Context",
        "",
        f"- Title: {rec.get('title')}",
        f"- Thesis: {rec.get('thesis') or 'n/a'}",
        f"- Profitability path: {rec.get('profitability_path') or 'n/a'}",
        f"- Risk decision: {risk_decision.get('decision') or 'n/a'}",
        f"- Risk score: {risk_decision.get('risk_score') or 'n/a'}",
        f"- Risk flags: {', '.join(risk_decision.get('risk_flags') or []) or 'n/a'}",
        "",
        "## Proposal Snapshot",
        "",
        f"- Symbol: {(proposal or {}).get('symbol') or 'n/a'}",
        f"- Side: {(proposal or {}).get('side') or 'n/a'}",
        f"- Timeframe: {(proposal or {}).get('timeframe') or 'n/a'}",
        f"- Strategy ID: {(proposal or {}).get('strategy_id') or 'n/a'}",
        f"- Asset type: {(proposal or {}).get('asset_type') or rec.get('category') or 'n/a'}",
        "",
        "## Replay Evidence",
        "",
    ]
    if recent_replays:
        for row in recent_replays[:5]:
            lines.append(
                f"- {row.get('replay_outcome')}: pnl_r={row.get('pnl_r')} pnl_pct={row.get('pnl_pct')} created_at={row.get('created_at')}"
            )
    else:
        lines.append("- No recent replay rows were attached to the recommendation metadata.")
    return lines


def _research_brief(task: dict, rec: dict, proposal: Optional[dict]) -> str:
    lines = [
        f"# {task.get('title')}",
        "",
        f"Assigned team: {task.get('assigned_team')}",
        f"Task type: {task.get('task_type')}",
        "",
    ]
    lines.extend(_risk_summary(rec, proposal))
    lines.extend(
        [
            "",
            "## Operator Recommendation",
            "",
            "- Confirm the latest risk flags still match market structure before promotion.",
            "- Keep the setup in paper-only mode until replay evidence remains aligned.",
            "- Promote only after replay, risk review, and analyst confidence all point the same way.",
            "",
            "## Updated At",
            "",
            datetime.now(timezone.utc).isoformat(),
            "",
        ]
    )
    return "\n".join(lines)


def _submission_payload(project: dict, task: dict, rec: dict, proposal: Optional[dict], run_id: Optional[str]) -> dict:
    metadata = rec.get("metadata") or {}
    risk_decision = metadata.get("risk_decision") or {}
    return {
        "project_id": project.get("id"),
        "recommendation_id": rec.get("id"),
        "implementation_task_id": task.get("id"),
        "paper_trade_run_id": run_id,
        "proposal_id": (proposal or {}).get("id") or rec.get("source_id"),
        "signal_id": (proposal or {}).get("signal_id"),
        "symbol": (proposal or {}).get("symbol"),
        "side": (proposal or {}).get("side"),
        "timeframe": (proposal or {}).get("timeframe"),
        "strategy_id": (proposal or {}).get("strategy_id") or metadata.get("strategy_id"),
        "strategy_type": (proposal or {}).get("strategy_type"),
        "asset_type": (proposal or {}).get("asset_type") or rec.get("category"),
        "entry_price": (proposal or {}).get("entry_price"),
        "stop_loss": (proposal or {}).get("stop_loss"),
        "take_profit": (proposal or {}).get("take_profit"),
        "recommendation": rec.get("summary"),
        "risk_decision": risk_decision,
        "recent_replays": metadata.get("recent_replays") or [],
        "queued_at": datetime.now(timezone.utc).isoformat(),
    }


def _queue_paper_trade_run(project: dict, rec: dict, proposal: Optional[dict]) -> Optional[str]:
    if not proposal:
        return None
    run_id = _deterministic_uuid(f"paper-trade-run:{project['id']}:{proposal['id']}")
    replay_mode = (
        "options_historical_profile"
        if (proposal.get("asset_type") or rec.get("category")) == "options"
        else "forex_static_rr"
    )
    existing = _sb_get(
        "paper_trade_runs"
        f"?id=eq.{_quote(run_id)}&select=id&limit=1"
    )
    if existing:
        return existing[0]["id"]
    _sb_post(
        "paper_trade_runs",
        [
            {
                "id": run_id,
                "proposal_id": proposal.get("id"),
                "signal_id": proposal.get("signal_id"),
                "asset_type": proposal.get("asset_type") or rec.get("category") or "forex",
                "symbol": proposal.get("symbol"),
                "strategy_id": proposal.get("strategy_id"),
                "strategy_type": proposal.get("strategy_type"),
                "replay_mode": replay_mode,
                "status": "running",
                "trace_id": rec.get("trace_id") or proposal.get("trace_id"),
            }
        ],
    )
    return run_id


def _output_path(base: Path, task: dict, suffix: str) -> Path:
    return base / f"{int(task.get('task_order', 0)):02d}-{_slug(task.get('assigned_team'))}-{_slug(task.get('title'))}{suffix}"


def _write_output(project: dict, task: dict, rec: dict, proposal: Optional[dict]) -> tuple[str, Optional[str]]:
    base = _bundle_dir(project)
    if task.get("assigned_team") == "TradingEngine":
        run_id = _queue_paper_trade_run(project, rec, proposal)
        path = _output_path(base, task, ".json")
        path.write_text(
            json.dumps(_submission_payload(project, task, rec, proposal, run_id), indent=2),
            encoding="utf-8",
        )
        return str(path), run_id
    path = _output_path(base, task, ".md")
    path.write_text(_research_brief(task, rec, proposal), encoding="utf-8")
    return str(path), None


def _patch_task(task_id: str, data: dict) -> None:
    _sb_patch("implementation_tasks", f"id=eq.{_quote(task_id)}", data)


def _finalize_project(project: dict) -> None:
    remaining = _sb_get(
        "implementation_tasks"
        "?select=id,status"
        f"&project_id=eq.{_quote(project['id'])}"
        "&status=in.(pending,ready,in_progress,blocked)"
        "&limit=1"
    )
    if remaining:
        return
    current = _sb_get(
        "implementation_projects"
        f"?id=eq.{_quote(project['id'])}&select=metadata&limit=1"
    )
    metadata = dict((current[0].get("metadata") if current else project.get("metadata")) or {})
    if metadata.get("pending_paper_trade_run_id"):
        metadata["awaiting_replay_completion"] = True
        _sb_patch(
            "implementation_projects",
            f"id=eq.{_quote(project['id'])}",
            {
                "status": "in_progress",
                "metadata": metadata,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return
    metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
    _sb_patch(
        "implementation_projects",
        f"id=eq.{_quote(project['id'])}",
        {
            "status": "completed",
            "metadata": metadata,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def execute_once(limit: int = 10) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    projects = _active_projects(limit)
    completed = 0
    outputs: List[str] = []
    queued_runs: List[str] = []
    for project in projects:
        rec = _recommendation(project["recommendation_id"])
        if not rec:
            continue
        proposal = _proposal(rec)
        tasks = _project_tasks(project["id"])
        for task in tasks:
            output_path, run_id = _write_output(project, task, rec, proposal)
            metadata = dict(task.get("metadata") or {})
            metadata["output_path"] = output_path
            metadata["completed_by_worker"] = "trading_task_executor"
            if run_id:
                metadata["queued_run_id"] = run_id
                project_metadata = dict(project.get("metadata") or {})
                project_metadata["pending_paper_trade_run_id"] = run_id
                project_metadata["trading_bundle_path"] = str(_bundle_dir(project))
                _sb_patch(
                    "implementation_projects",
                    f"id=eq.{_quote(project['id'])}",
                    {
                        "status": "in_progress",
                        "metadata": project_metadata,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                queued_runs.append(run_id)
                project["metadata"] = project_metadata
            _patch_task(
                task["id"],
                {
                    "status": "completed",
                    "metadata": metadata,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            outputs.append(output_path)
            completed += 1
        _finalize_project(project)
    return {
        "projects_found": len(projects),
        "tasks_completed": completed,
        "queued_run_ids": queued_runs[:10],
        "outputs_written": outputs[:10],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(execute_once(limit=args.limit), indent=2))
