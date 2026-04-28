#!/usr/bin/env python3
"""
Replay-backed strategy promotion bridge for the paper trader.

This script closes the gap between:
YouTube/research-driven strategy proposals -> replay/backtest results -> paper trader intake.

It reads Supabase proposal/replay/risk data, computes a simple strategy rating,
builds a local queue/status snapshot, and can optionally submit the top replay-backed
forex candidates to the paper trader's existing manual signal endpoint.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, parse, request

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass


ROOT = Path("/Users/raymonddavis/nexus-ai")
STATUS_FILE = ROOT / "logs" / "strategy_tester_status.json"
QUEUE_FILE = ROOT / "logs" / "strategy_paper_queue.json"
PAPER_SIGNAL_URL = os.getenv("NEXUS_PAPER_SIGNAL_URL", "http://127.0.0.1:5000/signal/manual")

WIN_OUTCOMES = {"tp_hit", "win"}
NON_LOSS_OUTCOMES = {"tp_hit", "win", "breakeven", "expired"}


def env_first(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


SUPABASE_URL = env_first("SUPABASE_URL")
SUPABASE_READ_KEY = env_first("SUPABASE_ANON_KEY", "SUPABASE_KEY")
SUPABASE_WRITE_KEY = env_first("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY")


def iso_now() -> str:
    return datetime.now().isoformat()


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str))
    tmp.replace(path)


def sb_headers(service: bool = False) -> dict[str, str]:
    key = SUPABASE_WRITE_KEY if service else SUPABASE_READ_KEY
    return {
        "Content-Type": "application/json",
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }


def sb_get(query_path: str, *, service: bool = False, tolerate_missing: bool = False) -> list[dict[str, Any]]:
    url = f"{SUPABASE_URL}/rest/v1/{query_path}"
    req = request.Request(url, headers=sb_headers(service=service))
    try:
        with request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except error.HTTPError as exc:
        body = exc.read().decode(errors="ignore")
        if tolerate_missing and exc.code in {400, 404}:
            return []
        raise RuntimeError(f"Supabase GET failed [{exc.code}] {query_path}: {body}") from exc


def http_post_json(url: str, payload: dict[str, Any]) -> tuple[int, Any]:
    data = json.dumps(payload).encode()
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as resp:
        raw = resp.read()
        try:
            body = json.loads(raw)
        except Exception:
            body = raw.decode(errors="ignore")
        return resp.status, body


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def load_strategy_data() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    proposals = sb_get(
        "reviewed_signal_proposals"
        "?select=id,signal_id,symbol,side,timeframe,strategy_id,asset_type,"
        "entry_price,stop_loss,take_profit,ai_confidence,status,trace_id,created_at"
        "&asset_type=eq.forex"
        "&status=in.(proposed,needs_review)"
        "&order=created_at.desc"
        "&limit=250",
        tolerate_missing=True,
    )
    replay_results = sb_get(
        "replay_results"
        "?select=proposal_id,strategy_id,replay_outcome,pnl_r,pnl_pct,created_at"
        "&order=created_at.desc"
        "&limit=500",
        tolerate_missing=True,
    )
    risk_decisions = sb_get(
        "risk_decisions"
        "?select=proposal_id,decision,risk_score,created_at"
        "&order=created_at.desc"
        "&limit=500",
        tolerate_missing=True,
    )
    strategy_variants = sb_get(
        "strategy_variants"
        "?select=strategy_id,variant_name,replay_score,backtest_score,parameter_set,created_at"
        "&order=created_at.desc"
        "&limit=250",
        tolerate_missing=True,
    )
    return proposals, replay_results, risk_decisions, strategy_variants


def latest_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_key = row.get(key)
        if row_key and row_key not in latest:
            latest[row_key] = row
    return latest


def canonical_replays_by_proposal(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Collapse historical duplicate replay rows so analytics only count one replay
    result per proposal. We keep the earliest row for a proposal because the
    earlier duplicates came from a one-time executor bug that spawned extra
    runs for the same proposal.
    """
    canonical: dict[str, dict[str, Any]] = {}
    ordered = sorted(rows, key=lambda row: str(row.get("created_at") or ""))
    for row in ordered:
        proposal_id = row.get("proposal_id")
        if not proposal_id:
            continue
        canonical.setdefault(str(proposal_id), row)
    return list(canonical.values())


def compute_strategy_snapshot(
    proposals: list[dict[str, Any]],
    replay_results: list[dict[str, Any]],
    risk_decisions: list[dict[str, Any]],
    strategy_variants: list[dict[str, Any]],
    *,
    min_rating: float,
    min_confidence: float,
    allow_manual_review: bool,
    allow_breakeven: bool,
) -> dict[str, Any]:
    warnings: list[str] = []
    queue_state = read_json(QUEUE_FILE, {"submitted_proposal_ids": [], "submissions": []})
    submitted_ids = set(queue_state.get("submitted_proposal_ids", []))
    canonical_replays = canonical_replays_by_proposal(replay_results)
    duplicate_replay_count = max(0, len(replay_results) - len(canonical_replays))

    proposals_by_id = {row["id"]: row for row in proposals if row.get("id")}
    latest_replay = latest_by_key(canonical_replays, "proposal_id")
    latest_risk = latest_by_key(risk_decisions, "proposal_id")

    strategy_stats: dict[str, dict[str, Any]] = {}
    for replay in canonical_replays:
        proposal_id = replay.get("proposal_id")
        proposal = proposals_by_id.get(proposal_id, {})
        strategy_id = replay.get("strategy_id") or proposal.get("strategy_id") or "unknown"
        stats = strategy_stats.setdefault(
            strategy_id,
            {
                "strategy_id": strategy_id,
                "replays": 0,
                "wins": 0,
                "non_losses": 0,
                "approved": 0,
                "manual_review": 0,
                "blocked": 0,
                "confidences": [],
                "pnl_r": [],
                "variant_score": 0.0,
            },
        )
        stats["replays"] += 1
        outcome = replay.get("replay_outcome")
        if outcome in WIN_OUTCOMES:
            stats["wins"] += 1
        if outcome in NON_LOSS_OUTCOMES:
            stats["non_losses"] += 1
        pnl_r = replay.get("pnl_r")
        if pnl_r is not None:
            stats["pnl_r"].append(safe_float(pnl_r))
        confidence = proposal.get("ai_confidence")
        if confidence is not None:
            stats["confidences"].append(safe_float(confidence))
        risk = latest_risk.get(proposal_id)
        decision = (risk or {}).get("decision")
        if decision in {"approved", "manual_review", "blocked"}:
            stats[decision] += 1

    for variant in strategy_variants:
        strategy_id = variant.get("strategy_id")
        if not strategy_id:
            continue
        stats = strategy_stats.setdefault(
            strategy_id,
            {
                "strategy_id": strategy_id,
                "replays": 0,
                "wins": 0,
                "non_losses": 0,
                "approved": 0,
                "manual_review": 0,
                "blocked": 0,
                "confidences": [],
                "pnl_r": [],
                "variant_score": 0.0,
            },
        )
        stats["variant_score"] = max(stats["variant_score"], safe_float(variant.get("replay_score")) / 100.0)

    top_strategies: list[dict[str, Any]] = []
    for strategy_id, stats in strategy_stats.items():
        replays = stats["replays"]
        risk_total = stats["approved"] + stats["manual_review"] + stats["blocked"]
        win_rate = stats["wins"] / replays if replays else 0.0
        non_loss_rate = stats["non_losses"] / replays if replays else 0.0
        approval_base = stats["approved"]
        if allow_manual_review:
            approval_base += stats["manual_review"]
        approval_rate = approval_base / risk_total if risk_total else 0.0
        avg_confidence = (
            sum(stats["confidences"]) / len(stats["confidences"]) if stats["confidences"] else 0.0
        )
        avg_pnl_r = sum(stats["pnl_r"]) / len(stats["pnl_r"]) if stats["pnl_r"] else 0.0
        pnl_score = max(0.0, min(1.0, (avg_pnl_r + 1.0) / 3.0))
        rating = round(
            100.0
            * (
                0.45 * win_rate
                + 0.15 * non_loss_rate
                + 0.15 * approval_rate
                + 0.10 * avg_confidence
                + 0.10 * pnl_score
                + 0.05 * stats["variant_score"]
            ),
            1,
        )
        top_strategies.append(
            {
                "strategy_id": strategy_id,
                "rating": rating,
                "replays": replays,
                "win_rate": round(win_rate, 3),
                "non_loss_rate": round(non_loss_rate, 3),
                "approval_rate": round(approval_rate, 3),
                "avg_confidence": round(avg_confidence, 3),
                "avg_pnl_r": round(avg_pnl_r, 3),
                "variant_score": round(stats["variant_score"] * 100.0, 1),
            }
        )

    top_strategies.sort(key=lambda row: (row["rating"], row["replays"]), reverse=True)
    ratings_by_strategy = {row["strategy_id"]: row for row in top_strategies}

    eligible_candidates: list[dict[str, Any]] = []
    allowed_outcomes = set(WIN_OUTCOMES)
    if allow_breakeven:
        allowed_outcomes.update({"breakeven", "expired"})

    for proposal_id, proposal in proposals_by_id.items():
        replay = latest_replay.get(proposal_id)
        if not replay:
            continue
        outcome = replay.get("replay_outcome")
        if outcome not in allowed_outcomes:
            continue

        risk = latest_risk.get(proposal_id, {})
        decision = risk.get("decision")
        if decision != "approved" and not (allow_manual_review and decision == "manual_review"):
            continue

        strategy_id = proposal.get("strategy_id") or replay.get("strategy_id") or "unknown"
        strategy_rating = ratings_by_strategy.get(strategy_id, {})
        if safe_float(strategy_rating.get("rating")) < min_rating:
            continue

        ai_confidence = safe_float(proposal.get("ai_confidence"))
        if ai_confidence < min_confidence:
            continue

        if not proposal.get("symbol") or not proposal.get("side"):
            continue
        if proposal.get("entry_price") in {None, ""} or proposal.get("stop_loss") in {None, ""} or proposal.get("take_profit") in {None, ""}:
            continue

        signal_payload = {
            "symbol": proposal.get("symbol"),
            "action": str(proposal.get("side")).upper(),
            "entry_price": proposal.get("entry_price"),
            "stop_loss": proposal.get("stop_loss"),
            "take_profit": proposal.get("take_profit"),
            "timeframe": proposal.get("timeframe") or "H1",
            "strategy": strategy_id,
            "confidence": int(round(ai_confidence * 100)),
        }
        eligible_candidates.append(
            {
                "proposal_id": proposal_id,
                "signal_id": proposal.get("signal_id"),
                "symbol": proposal.get("symbol"),
                "side": proposal.get("side"),
                "strategy_id": strategy_id,
                "strategy_rating": safe_float(strategy_rating.get("rating")),
                "replay_outcome": outcome,
                "risk_decision": decision,
                "risk_score": safe_float(risk.get("risk_score")),
                "ai_confidence": round(ai_confidence, 3),
                "trace_id": proposal.get("trace_id"),
                "created_at": proposal.get("created_at"),
                "signal_payload": signal_payload,
                "already_submitted": proposal_id in submitted_ids,
            }
        )

    eligible_candidates.sort(
        key=lambda row: (
            row["already_submitted"],
            -row["strategy_rating"],
            -row["ai_confidence"],
            row["symbol"],
        )
    )

    if not SUPABASE_URL:
        warnings.append("SUPABASE_URL is missing")
    if not SUPABASE_READ_KEY:
        warnings.append("Supabase read key is missing")
    if not SUPABASE_WRITE_KEY:
        warnings.append("Supabase service key is missing; queue submit still works but table writes are unavailable")
    if not proposals and not replay_results and not risk_decisions:
        warnings.append("Trading lab Supabase tables are missing or empty; apply the reviewed/replay/risk SQL before this bridge can rank strategies")
    if not top_strategies:
        warnings.append("No replay-backed strategy ratings found yet")
    if not eligible_candidates:
        warnings.append("No replay-backed paper candidates cleared the current thresholds")
    if duplicate_replay_count:
        warnings.append(
            f"Ignored {duplicate_replay_count} duplicate replay result rows by canonicalizing to one replay per proposal"
        )

    return {
        "updated_at": iso_now(),
        "thresholds": {
            "min_rating": min_rating,
            "min_confidence": min_confidence,
            "allow_manual_review": allow_manual_review,
            "allow_breakeven": allow_breakeven,
        },
        "summary": {
            "proposal_count": len(proposals),
            "replay_count": len(replay_results),
            "canonical_replay_count": len(canonical_replays),
            "duplicate_replay_count": duplicate_replay_count,
            "risk_count": len(risk_decisions),
            "strategy_count": len(top_strategies),
            "eligible_candidate_count": len(eligible_candidates),
            "submitted_candidate_count": len(queue_state.get("submissions", [])),
        },
        "top_strategies": top_strategies[:10],
        "eligible_candidates": eligible_candidates[:20],
        "recent_submissions": queue_state.get("submissions", [])[-10:],
        "warnings": warnings,
    }


def submit_candidates(snapshot: dict[str, Any], limit: int) -> dict[str, Any]:
    queue_state = read_json(QUEUE_FILE, {"submitted_proposal_ids": [], "submissions": []})
    submitted_ids = set(queue_state.get("submitted_proposal_ids", []))
    submissions = []

    for candidate in snapshot.get("eligible_candidates", []):
        if candidate["proposal_id"] in submitted_ids:
            continue
        if len(submissions) >= limit:
            break

        record = {
            "proposal_id": candidate["proposal_id"],
            "signal_id": candidate.get("signal_id"),
            "symbol": candidate["symbol"],
            "strategy_id": candidate["strategy_id"],
            "strategy_rating": candidate["strategy_rating"],
            "replay_outcome": candidate["replay_outcome"],
            "submitted_at": iso_now(),
        }
        try:
            status_code, response_body = http_post_json(PAPER_SIGNAL_URL, candidate["signal_payload"])
            record["status"] = "submitted" if status_code < 300 else "failed"
            record["receiver_status_code"] = status_code
            record["response"] = response_body
            if record["status"] == "submitted":
                submitted_ids.add(candidate["proposal_id"])
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = str(exc)

        queue_state.setdefault("submissions", []).append(record)
        submissions.append(record)

    queue_state["updated_at"] = iso_now()
    queue_state["submitted_proposal_ids"] = sorted(submitted_ids)
    write_json(QUEUE_FILE, queue_state)
    snapshot["recent_submissions"] = queue_state.get("submissions", [])[-10:]
    snapshot["summary"]["submitted_candidate_count"] = len(queue_state.get("submissions", []))
    return {"count": len(submissions), "items": submissions}


def print_brief(snapshot: dict[str, Any]) -> None:
    summary = snapshot.get("summary", {})
    top = (snapshot.get("top_strategies") or [None])[0]
    print("Strategy tester status")
    print(
        f"Strategies: {summary.get('strategy_count', 0)} rated | "
        f"eligible paper candidates: {summary.get('eligible_candidate_count', 0)}"
    )
    if top:
        print(
            "Top strategy: "
            f"{top.get('strategy_id')} rating={top.get('rating')} "
            f"win_rate={top.get('win_rate')} replays={top.get('replays')}"
        )
    else:
        print("Top strategy: none yet")
    recent = snapshot.get("recent_submissions") or []
    if recent:
        latest = recent[-1]
        print(
            "Last submission: "
            f"{latest.get('symbol')} / {latest.get('strategy_id')} / {latest.get('status')}"
        )
    else:
        print("Last submission: none yet")
    warnings = snapshot.get("warnings") or []
    if warnings:
        print(f"Warnings: {warnings[0]}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "brief"), default="json")
    parser.add_argument("--submit", action="store_true")
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--min-rating", type=float, default=float(os.getenv("NEXUS_STRATEGY_MIN_RATING", "65")))
    parser.add_argument("--min-confidence", type=float, default=float(os.getenv("NEXUS_STRATEGY_MIN_CONFIDENCE", "0.6")))
    parser.add_argument("--allow-manual-review", action="store_true")
    parser.add_argument("--allow-breakeven", action="store_true")
    args = parser.parse_args()

    snapshot = compute_strategy_snapshot(
        *load_strategy_data(),
        min_rating=args.min_rating,
        min_confidence=args.min_confidence,
        allow_manual_review=args.allow_manual_review,
        allow_breakeven=args.allow_breakeven,
    )

    if args.submit:
        snapshot["submission_run"] = submit_candidates(snapshot, max(1, args.limit))

    write_json(STATUS_FILE, snapshot)

    if args.format == "brief":
        print_brief(snapshot)
    else:
        print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()
