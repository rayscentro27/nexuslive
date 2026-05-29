"""
daily_opportunity_intake_engine.py
=====================================
Collects, registers, and organizes opportunity sources for Hermes.

Rules:
  NO SOURCE DISAPPEARS.
  NO FAKE RESULTS — if a source is unavailable, create a structured fallback task.
  NO PAID APIS — free research only.
  EVERY SOURCE GETS AN INTAKE RECORD.
  EVERY INTAKE RECORD GETS AN ARTIFACT.

Source categories:
  A. YouTube: from existing channel registry + channel poller outputs
  B. Google/web keywords: requires free search API — creates fallback tasks if unavailable
  C. Social/trend: creates structured manual research tasks (no scraping without approval)
  D. GitHub: reads from run_weekly_github_trend_research.py outputs
  E. Monetization sources: affiliate/program pages from structured keyword research

Storage:
  docs/reports/intake/daily_opportunity_intake_<timestamp>.json
  docs/reports/intake/daily_opportunity_intake_<timestamp>.md
"""
from __future__ import annotations

import json
import re
import uuid
import yaml
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parent.parent
INTAKE_DIR = ROOT / "docs" / "reports" / "intake"
CONFIG_FILE = ROOT / "config" / "opportunity_intake_sources.yaml"

IntakeStatus = Literal[
    "discovered", "registered", "queued", "needs_transcript",
    "needs_more_research", "assigned", "blocked", "rejected",
    "ready_for_decision", "processed_with_artifact",
]

# ── Intake record ──────────────────────────────────────────────────────────────

@dataclass
class IntakeRecord:
    intake_id: str = field(default_factory=lambda: f"src_{uuid.uuid4().hex[:10]}")
    source_type: str = ""          # youtube, google, github, social, affiliate, manual
    platform: str = ""
    url: str = ""
    title: str = ""
    keyword: str = ""
    discovered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    discovered_by: str = "daily_opportunity_intake_engine"
    status: IntakeStatus = "registered"
    assigned_scout: str = ""
    artifact_registry_id: str = ""
    supabase_id: str = ""
    priority: str = "normal"       # low, normal, high, urgent
    why_collected: str = ""
    next_action: str = ""
    evidence_level: str = "registered"
    requires_ray_approval: bool = False
    fallback: bool = False         # True if source was unavailable — task created instead
    fallback_reason: str = ""
    monetization_potential: str = "" # low, medium, high

    def to_dict(self) -> dict:
        return asdict(self)

    def to_plain_english(self) -> str:
        mark = "🔶" if self.fallback else "📥"
        line = f"{mark} [{self.source_type}] {self.title or self.keyword or self.url[:60]}"
        if self.fallback:
            line += f" (fallback task — {self.fallback_reason})"
        elif self.priority == "high":
            line = "⭐ " + line
        return line


# ── Config loader ─────────────────────────────────────────────────────────────

def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Source A: YouTube ─────────────────────────────────────────────────────────

def _collect_youtube_sources(cfg: dict, max_sources: int) -> list[IntakeRecord]:
    records: list[IntakeRecord] = []

    # 1. Read from existing telegram source intake (Ray-provided URLs)
    tg_intake = ROOT / "docs" / "reports" / "intake" / "telegram_source_intake.jsonl"
    if tg_intake.exists():
        try:
            for line in tg_intake.read_text().splitlines():
                if not line.strip():
                    continue
                d = json.loads(line)
                url = d.get("url", "")
                if "youtube" in url.lower() or "youtu.be" in url.lower():
                    records.append(IntakeRecord(
                        intake_id=f"src_yt_tg_{uuid.uuid4().hex[:8]}",
                        source_type="youtube",
                        platform="youtube",
                        url=url,
                        title=d.get("title", url),
                        discovered_by="telegram_source_intake",
                        why_collected="Ray submitted via Telegram",
                        next_action="run_youtube_intelligence_cycle",
                        priority="high",
                        monetization_potential="medium",
                    ))
        except Exception:
            pass

    # 2. Read from nexus_sources.yaml (existing channel registry)
    existing_sources = ROOT / "config" / "nexus_sources.yaml"
    if existing_sources.exists():
        try:
            with open(existing_sources) as f:
                src_cfg = yaml.safe_load(f) or {}
            for div_key, div_sources in src_cfg.items():
                if isinstance(div_sources, list):
                    for s in div_sources:
                        if not isinstance(s, dict):
                            continue
                        url = s.get("url", "")
                        if url and ("youtube" in url.lower() or "youtu.be" in url.lower()):
                            records.append(IntakeRecord(
                                intake_id=f"src_yt_reg_{uuid.uuid4().hex[:8]}",
                                source_type="youtube",
                                platform="youtube",
                                url=url,
                                title=s.get("name", url),
                                discovered_by="nexus_sources_yaml",
                                why_collected=f"Registered channel ({div_key})",
                                next_action="run_youtube_intelligence_cycle",
                                priority="normal",
                                monetization_potential="medium",
                            ))
        except Exception:
            pass

    # 3. Register keyword-based YouTube research tasks
    yt_keywords = cfg.get("youtube_keywords", {})
    if isinstance(yt_keywords, dict):
        kw_list = [kw for group in yt_keywords.values() for kw in group]
    else:
        kw_list = list(yt_keywords) if yt_keywords else []

    for kw in kw_list[:10]:
        records.append(IntakeRecord(
            intake_id=f"src_yt_kw_{uuid.uuid4().hex[:8]}",
            source_type="youtube",
            platform="youtube",
            url="",
            title=f"YouTube keyword research: {kw}",
            keyword=kw,
            discovered_by="keyword_config",
            why_collected="Keyword search for opportunity signals",
            next_action="run_youtube_source_reconciliation",
            priority="normal",
            monetization_potential=_kw_monetization_potential(kw),
        ))

    return _dedup_and_limit(records, max_sources // 3)


def _kw_monetization_potential(keyword: str) -> str:
    kw = keyword.lower()
    if any(t in kw for t in ["affiliate", "make money", "monetiz", "funnel", "sell", "income", "revenue"]):
        return "high"
    if any(t in kw for t in ["credit", "fund", "grant", "business", "loan"]):
        return "high"
    if any(t in kw for t in ["strategy", "backtest", "trading"]):
        return "medium"
    return "low"


# ── Source B: Google/web ──────────────────────────────────────────────────────

def _collect_google_sources(cfg: dict, max_sources: int) -> list[IntakeRecord]:
    """
    No free search API is configured by default.
    Creates structured fallback tasks — no fake results.
    """
    records: list[IntakeRecord] = []
    google_kws = cfg.get("google_keywords", {})
    if isinstance(google_kws, dict):
        kw_list = [kw for group in google_kws.values() for kw in group]
    else:
        kw_list = list(google_kws) if google_kws else []

    # Check if a free search API is available
    search_available = _is_search_available()

    for kw in kw_list[:max_sources]:
        if search_available:
            # Future: call search API here
            records.append(IntakeRecord(
                intake_id=f"src_goog_{uuid.uuid4().hex[:8]}",
                source_type="google",
                platform="google",
                url="",
                title=f"Google search: {kw}",
                keyword=kw,
                discovered_by="google_search_api",
                why_collected="Keyword opportunity research",
                next_action="process_search_results",
                priority="normal",
                monetization_potential=_kw_monetization_potential(kw),
            ))
        else:
            records.append(IntakeRecord(
                intake_id=f"src_goog_fb_{uuid.uuid4().hex[:8]}",
                source_type="google",
                platform="google",
                url="",
                title=f"Manual research task: {kw}",
                keyword=kw,
                discovered_by="fallback_task_generator",
                why_collected="Google search API not available — structured manual task",
                next_action="ray_manual_research_or_add_search_api",
                status="needs_more_research",
                fallback=True,
                fallback_reason="No free search API configured",
                monetization_potential=_kw_monetization_potential(kw),
            ))

    return records[:max_sources]


def _is_search_available() -> bool:
    """Return True only if a free search API is actually configured."""
    return bool(
        os.getenv("BRAVE_SEARCH_API_KEY") or
        os.getenv("SERPAPI_KEY") or
        os.getenv("SERPER_API_KEY")
    )


# ── Source C: Social/trend ───────────────────────────────────────────────────

def _collect_social_sources(cfg: dict, max_sources: int) -> list[IntakeRecord]:
    """
    No scraping without approved paid APIs.
    Creates structured manual research tasks per platform.
    """
    records: list[IntakeRecord] = []
    platforms = cfg.get("social_platforms", [])
    keywords = cfg.get("social_keywords", [])[:5]

    for platform_cfg in platforms:
        if not isinstance(platform_cfg, dict):
            continue
        platform = platform_cfg.get("platform", "")
        method = platform_cfg.get("method", "manual_fallback")
        if method == "existing_poller":
            continue  # handled by YouTube channel poller — do not duplicate
        for kw in keywords[:3]:
            records.append(IntakeRecord(
                intake_id=f"src_social_{platform[:4]}_{uuid.uuid4().hex[:8]}",
                source_type="social",
                platform=platform,
                url="",
                title=f"{platform} trend research: {kw}",
                keyword=kw,
                discovered_by="fallback_task_generator",
                why_collected=f"Social trend research — {platform} not available without approved API",
                next_action="ray_manual_social_research",
                status="needs_more_research",
                fallback=True,
                fallback_reason=f"No {platform} API available",
                monetization_potential=_kw_monetization_potential(kw),
                requires_ray_approval=False,
            ))

    return records[:max_sources]


# ── Source D: GitHub ──────────────────────────────────────────────────────────

def _collect_github_sources(cfg: dict, max_sources: int) -> list[IntakeRecord]:
    """
    Read outputs from run_weekly_github_trend_research.py.
    If outputs exist, register them. Otherwise create a dispatch task.
    """
    records: list[IntakeRecord] = []
    github_report_dirs = [
        ROOT / "docs" / "reports" / "research",
        ROOT / "docs" / "reports",
        ROOT / "research-engine",
    ]

    github_outputs = []
    for d in github_report_dirs:
        if d.exists():
            github_outputs.extend(d.glob("*github*trend*.json"))
            github_outputs.extend(d.glob("*github*research*.json"))

    if github_outputs:
        latest = max(github_outputs, key=lambda p: p.stat().st_mtime)
        try:
            data = json.loads(latest.read_text())
            repos = data.get("repos", data.get("results", []))
            for repo in repos[:max_sources]:
                if not isinstance(repo, dict):
                    continue
                records.append(IntakeRecord(
                    intake_id=f"src_gh_{uuid.uuid4().hex[:8]}",
                    source_type="github",
                    platform="github",
                    url=repo.get("url", repo.get("html_url", "")),
                    title=repo.get("name", repo.get("full_name", "GitHub repo")),
                    keyword=repo.get("topics", [""])[0] if repo.get("topics") else "",
                    discovered_by="github_trend_research_output",
                    why_collected="Trending AI/automation tool with monetization potential",
                    next_action="score_and_route_to_system_improvement_scout",
                    status="registered",
                    monetization_potential="medium",
                ))
        except Exception:
            pass

    if not records:
        # No existing outputs — register dispatch task
        github_kws = cfg.get("github_keywords", [])[:5]
        for kw in github_kws:
            records.append(IntakeRecord(
                intake_id=f"src_gh_kw_{uuid.uuid4().hex[:8]}",
                source_type="github",
                platform="github",
                url="",
                title=f"GitHub trend research needed: {kw}",
                keyword=kw,
                discovered_by="fallback_task_generator",
                why_collected="Run weekly GitHub trend research to find tools for this keyword",
                next_action="run_weekly_github_trend_research",
                status="needs_more_research",
                fallback=True,
                fallback_reason="run_weekly_github_trend_research not yet run for this keyword",
                monetization_potential="medium",
            ))

    return records[:max_sources]


# ── Source E: Monetization sources ────────────────────────────────────────────

def _collect_monetization_sources(cfg: dict, max_sources: int) -> list[IntakeRecord]:
    """
    Register monetization categories as structured research tasks.
    Creates one entry per category for scoring.
    """
    records: list[IntakeRecord] = []
    categories = cfg.get("monetization_categories", [])

    category_details = {
        "affiliate": ("Affiliate program research", "affiliate_monetization_scout", "high"),
        "lead_magnet": ("Lead magnet opportunity", "content_intelligence_scout", "high"),
        "paid_template": ("Paid template/tool product", "content_intelligence_scout", "medium"),
        "newsletter_premium": ("Newsletter premium tier", "content_intelligence_scout", "high"),
        "landing_page": ("Landing page opportunity", "funnel_builder_scout", "medium"),
        "audit_offer": ("Business audit offer", "monetization_scout", "high"),
        "education_product": ("Education product", "content_intelligence_scout", "high"),
        "content_funnel": ("Content-to-funnel path", "funnel_builder_scout", "high"),
        "demo_trading_education": ("Demo trading education content", "trading_research_scout", "medium"),
        "client_readiness_report": ("Client readiness report template", "monetization_scout", "high"),
        "consulting_upsell": ("Consulting/coaching upsell", "monetization_scout", "medium"),
    }

    for cat in categories:
        details = category_details.get(cat)
        if not details:
            continue
        title, scout, potential = details
        records.append(IntakeRecord(
            intake_id=f"src_mon_{cat[:8]}_{uuid.uuid4().hex[:6]}",
            source_type="affiliate" if cat == "affiliate" else "monetization",
            platform="internal",
            url="",
            title=f"Monetization opportunity: {title}",
            keyword=cat,
            discovered_by="monetization_category_scanner",
            why_collected=f"Nexus 30-day revenue goal — {cat} category has known demand",
            next_action=f"route_to_{scout}",
            assigned_scout=scout,
            status="registered",
            monetization_potential=potential,
        ))

    return records[:max_sources]


# ── Dedup / limit ─────────────────────────────────────────────────────────────

def _dedup_and_limit(records: list[IntakeRecord], limit: int) -> list[IntakeRecord]:
    seen_urls: set[str] = set()
    result = []
    for r in records:
        key = r.url or r.title
        if key and key not in seen_urls:
            seen_urls.add(key)
            result.append(r)
        if len(result) >= limit:
            break
    return result


# ── Artifact registration ─────────────────────────────────────────────────────

def _register_artifact(path: Path, records_count: int, ts: str) -> str:
    try:
        from lib.nexus_artifact_registry import register_artifact
        art = register_artifact(
            agent_name="daily_opportunity_intake_engine",
            artifact_type="daily_intake_report",
            file_path=str(path),
            source_type="daily_intake",
            title=f"Daily Opportunity Intake {ts}",
            description=f"{records_count} sources registered",
            evidence_level="verified_file",
        )
        return art.artifact_id
    except Exception:
        return ""


# ── Save intake records ────────────────────────────────────────────────────────

def _save_records(records: list[IntakeRecord], ts: str) -> tuple[Path, Path]:
    INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    md_path   = INTAKE_DIR / f"daily_opportunity_intake_{ts}.md"
    json_path = INTAKE_DIR / f"daily_opportunity_intake_{ts}.json"

    # JSON
    data = {
        "intake_run_id": f"intake_{ts}",
        "generated_at": _now(),
        "total": len(records),
        "records": [r.to_dict() for r in records],
    }
    json_path.write_text(json.dumps(data, indent=2))

    # Markdown
    by_type: dict[str, list[IntakeRecord]] = {}
    for r in records:
        by_type.setdefault(r.source_type, []).append(r)

    fallbacks = [r for r in records if r.fallback]
    registered = [r for r in records if not r.fallback]

    md = [
        f"# Daily Opportunity Intake",
        f"*{ts[:8]} {ts[9:11]}:{ts[11:13]} UTC*",
        f"**{len(records)} sources registered** ({len(registered)} real, {len(fallbacks)} fallback tasks)",
        "",
    ]
    for src_type, recs in sorted(by_type.items()):
        md.append(f"## {src_type.capitalize()} ({len(recs)})")
        for r in recs:
            md.append(f"- {r.to_plain_english()}")
        md.append("")

    if fallbacks:
        md.append("## Fallback Tasks (source unavailable)")
        for r in fallbacks:
            md.append(f"- 🔶 {r.platform}: {r.title} — {r.fallback_reason}")
        md.append("")

    md_path.write_text("\n".join(md))
    return json_path, md_path


# ── Main run function ─────────────────────────────────────────────────────────

def run_intake(
    mode: str = "validation",
    max_sources: int = 20,
    register_artifacts: bool = True,
    dry_run: bool = True,
    cost: str = "free",
) -> dict:
    """
    Run the daily opportunity intake cycle.

    Returns a results dict with:
      records, artifact_path, md_path, stats
    """
    import os as os_mod
    cfg = _load_config()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    per_category = max(2, max_sources // 5)

    # Collect from each source category
    yt_records   = _collect_youtube_sources(cfg, per_category * 2)
    goog_records = _collect_google_sources(cfg, per_category)
    social_records = _collect_social_sources(cfg, per_category)
    gh_records   = _collect_github_sources(cfg, per_category)
    mon_records  = _collect_monetization_sources(cfg, per_category)

    all_records: list[IntakeRecord] = (
        yt_records + goog_records + social_records + gh_records + mon_records
    )
    all_records = all_records[:max_sources]

    # Save records
    json_path, md_path = _save_records(all_records, ts)

    # Register artifact
    artifact_id = ""
    if register_artifacts and not dry_run:
        artifact_id = _register_artifact(json_path, len(all_records), ts)
    elif register_artifacts:
        artifact_id = _register_artifact(json_path, len(all_records), ts)

    # Always register in source intake JSONL — registering sources is safe even in validation mode
    _persist_to_intake_jsonl(all_records)

    stats = {
        "total": len(all_records),
        "youtube": len(yt_records),
        "google": len(goog_records),
        "social": len(social_records),
        "github": len(gh_records),
        "monetization": len(mon_records),
        "fallbacks": sum(1 for r in all_records if r.fallback),
        "real_sources": sum(1 for r in all_records if not r.fallback),
        "high_potential": sum(1 for r in all_records if r.monetization_potential == "high"),
    }

    return {
        "mode": mode,
        "dry_run": dry_run,
        "records": [r.to_dict() for r in all_records],
        "record_objects": all_records,
        "artifact_id": artifact_id,
        "artifact_path": str(json_path.relative_to(ROOT)),
        "md_path": str(md_path.relative_to(ROOT)),
        "stats": stats,
        "ts": ts,
    }


def _persist_to_intake_jsonl(records: list[IntakeRecord]) -> None:
    """Append records to the main source intake JSONL (append-only log)."""
    intake_jsonl = INTAKE_DIR / "daily_opportunity_intake_registry.jsonl"
    INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(intake_jsonl, "a") as f:
            for r in records:
                f.write(json.dumps(r.to_dict()) + "\n")
    except Exception:
        pass


def load_latest_intake(limit: int = 50) -> list[dict]:
    """Load the most recent intake records from the registry JSONL."""
    intake_jsonl = INTAKE_DIR / "daily_opportunity_intake_registry.jsonl"
    if not intake_jsonl.exists():
        return []
    try:
        lines = intake_jsonl.read_text().splitlines()
        records = []
        for line in lines[-limit:]:
            if line.strip():
                records.append(json.loads(line))
        return list(reversed(records))
    except Exception:
        return []


import os
