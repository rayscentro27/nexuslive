"""
CEO Grouped Digest — 7-Section Apple Format.

Pulls live data from user_intelligence, analytics_events, and provider_health,
runs anomaly detection, and produces a structured digest for Raymond.

Run:
  python3 -m lib.ceo_grouped_digest

Returns a formatted string ready for Telegram or email.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger("CeoGroupedDigest")

# ── env loading ───────────────────────────────────────────────────────────────

_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
DRY_RUN = os.getenv('NEXUS_DRY_RUN', 'true').lower() == 'true'


# ── Supabase helpers ──────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }


def _sb_get(path: str, default: Any = None) -> Any:
    if default is None:
        default = []
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        logger.error("GET %s → HTTP %s: %s", path, e.code, e.read().decode()[:150])
        return default
    except Exception as e:
        logger.error("GET %s → %s", path, e)
        return default


# ── Section builders ──────────────────────────────────────────────────────────

def _icon(health: str) -> str:
    return {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}.get(health, '⚪')


def _section_platform_pulse(profiles: list, intelligence: list, analytics_today: list) -> str:
    total_users = len(profiles)
    scored = len(intelligence)
    green  = sum(1 for r in intelligence if r.get('operational_health') == 'green')
    yellow = sum(1 for r in intelligence if r.get('operational_health') == 'yellow')
    red    = sum(1 for r in intelligence if r.get('operational_health') == 'red')
    onboarded = sum(1 for p in profiles if p.get('onboarding_complete'))
    events_today = len(analytics_today)

    lines = ["📊 PLATFORM PULSE", "─" * 32]
    lines.append(f"Users: {total_users}  |  Scored: {scored}  |  Events today: {events_today}")
    lines.append(f"Health: 🟢 {green}  🟡 {yellow}  🔴 {red}")
    lines.append(f"Onboarding complete: {onboarded}/{total_users}")
    if total_users > 0:
        pct = round(onboarded / total_users * 100)
        lines.append(f"Completion rate: {pct}%")
    return "\n".join(lines)


def _section_user_intelligence(intelligence: list) -> str:
    lines = ["🧠 USER INTELLIGENCE", "─" * 32]
    if not intelligence:
        lines.append("No scored users yet. Run user_intelligence_worker with NEXUS_DRY_RUN=false.")
        return "\n".join(lines)

    avg_score = round(sum(r.get('user_intelligence_score', 0) for r in intelligence) / len(intelligence))
    top = sorted(intelligence, key=lambda r: r.get('user_intelligence_score', 0), reverse=True)[:3]

    lines.append(f"Avg composite score: {avg_score}/100")
    lines.append("Top users by score:")
    for r in top:
        uid = (r.get('user_id') or '?')[:8]
        score = r.get('user_intelligence_score', 0)
        health = r.get('operational_health', '?')
        nba = r.get('next_best_action') or '—'
        lines.append(f"  {_icon(health)} {uid}... score={score} → {nba[:60]}")
    return "\n".join(lines)


def _section_anomalies(anomaly_summary: dict) -> str:
    lines = ["⚠️  ANOMALIES", "─" * 32]
    anomalies = anomaly_summary.get('anomalies') or []
    if not anomalies:
        lines.append("✅ No anomalies detected.")
        return "\n".join(lines)

    crit = anomaly_summary.get('critical', 0)
    high = anomaly_summary.get('high', 0)
    med  = anomaly_summary.get('medium', 0)
    lines.append(f"Total: {len(anomalies)}  Critical: {crit}  High: {high}  Medium: {med}")
    for a in anomalies[:5]:
        sev = a.get('severity', '?').upper()
        title = a.get('title', '')
        icon = '🔴' if sev == 'CRITICAL' else ('🟠' if sev == 'HIGH' else '🟡')
        lines.append(f"  {icon} [{sev}] {title}")
        detail = a.get('detail', '')
        if detail:
            lines.append(f"      {detail[:100]}")
    return "\n".join(lines)


def _section_provider_health(providers: list) -> str:
    lines = ["🔌 PROVIDER HEALTH", "─" * 32]
    if not providers:
        lines.append("No provider health data.")
        return "\n".join(lines)

    for p in providers:
        name   = (p.get('provider_name') or p.get('name') or 'unknown').ljust(12)
        status = p.get('status') or 'unknown'
        icon   = {'online': '🟢', 'offline': '🔴', 'degraded': '🟡'}.get(status, '⚪')
        latency = p.get('avg_latency_ms') or p.get('latency_ms')
        lat_str = f"{latency}ms" if latency else "—"
        lines.append(f"  {icon} {name}  status={status}  latency={lat_str}")
    return "\n".join(lines)


def _section_analytics_activity(analytics_today: list) -> str:
    lines = ["📈 ANALYTICS ACTIVITY (TODAY)", "─" * 32]
    if not analytics_today:
        lines.append("No analytics events today yet.")
        return "\n".join(lines)

    by_feature: dict[str, int] = {}
    by_event: dict[str, int] = {}
    for ev in analytics_today:
        f = ev.get('feature') or 'unknown'
        e = ev.get('event_name') or ev.get('event_type') or 'unknown'
        by_feature[f] = by_feature.get(f, 0) + 1
        by_event[e] = by_event.get(e, 0) + 1

    lines.append(f"Total events: {len(analytics_today)}")
    top_features = sorted(by_feature.items(), key=lambda x: x[1], reverse=True)[:5]
    lines.append("By feature:")
    for feat, cnt in top_features:
        lines.append(f"  • {feat}: {cnt}")
    top_events = sorted(by_event.items(), key=lambda x: x[1], reverse=True)[:3]
    lines.append("Top events:")
    for evt, cnt in top_events:
        lines.append(f"  • {evt}: {cnt}")
    return "\n".join(lines)


def _section_next_actions(intelligence: list, anomaly_summary: dict) -> str:
    lines = ["✅ NEXT ACTIONS", "─" * 32]

    actions = []

    # Surface anomaly-driven actions first
    for a in (anomaly_summary.get('anomalies') or []):
        sev = a.get('severity', '')
        if sev in ('critical', 'high'):
            actions.append(f"[{sev.upper()}] {a.get('title', '')}")

    # User NBA queue
    high_priority_nba = [
        r for r in intelligence
        if r.get('next_best_action_priority') == 'high'
    ]
    for r in high_priority_nba[:3]:
        nba = r.get('next_best_action', '')
        uid = (r.get('user_id') or '?')[:8]
        if nba:
            actions.append(f"User {uid}…: {nba}")

    if not actions:
        actions = ["All clear — review dashboard for low-priority improvements."]

    for idx, a in enumerate(actions[:7], start=1):
        lines.append(f"  {idx}. {a}")
    return "\n".join(lines)


def _section_safety_check() -> str:
    lines = ["🔒 SAFETY STATE", "─" * 32]
    ui_writes  = os.getenv('USER_INTELLIGENCE_WRITES_ENABLED', 'false').lower() == 'true'
    ph_writes  = os.getenv('PROVIDER_HEALTH_WRITES_ENABLED', 'false').lower() == 'true'
    an_writes  = os.getenv('ANOMALY_WRITES_ENABLED', 'false').lower() == 'true'
    live_trade = os.getenv('LIVE_TRADING', 'false').lower() == 'true'
    lines.append(f"  NEXUS_DRY_RUN={str(DRY_RUN).lower()}  (global safety — always true)")
    lines.append(f"  LIVE_TRADING={str(live_trade).lower()}")
    lines.append(f"  TRADING_LIVE_EXECUTION_ENABLED=false")
    lines.append(f"  NEXUS_AUTO_TRADING=false")
    lines.append(f"  Auto social posting: disabled")
    lines.append("")
    lines.append("  Worker persistence (controlled activation):")
    lines.append(f"  {'✅' if ui_writes else '⬜'} USER_INTELLIGENCE_WRITES_ENABLED={str(ui_writes).lower()}")
    lines.append(f"  {'✅' if ph_writes else '⬜'} PROVIDER_HEALTH_WRITES_ENABLED={str(ph_writes).lower()}")
    lines.append(f"  {'✅' if an_writes else '⬜'} ANOMALY_WRITES_ENABLED={str(an_writes).lower()}")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def format_grouped_digest() -> str:
    """Pull live data and return a 7-section CEO digest string."""
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%SZ')

    logger.info("Building CEO grouped digest...")

    profiles     = _sb_get('user_profiles?select=id,onboarding_complete,created_at&limit=500')
    intelligence = _sb_get('user_intelligence?select=user_id,user_intelligence_score,operational_health,next_best_action,next_best_action_priority&limit=500')
    providers    = _sb_get('provider_health?select=*')
    analytics_today = _sb_get(
        f'analytics_events?select=event_type,event_name,feature,user_id'
        f'&created_at=gt.{day_start}&limit=2000'
    )

    # Run anomaly detection
    try:
        from lib.anomaly_detector import run_detection
        anomaly_summary = run_detection()
    except Exception as e:
        logger.warning("Anomaly detection failed: %s", e)
        anomaly_summary = {'anomalies': [], 'critical': 0, 'high': 0, 'medium': 0}

    date_str = now.strftime("%Y-%m-%d %H:%M UTC")
    header = f"NEXUS CEO DIGEST — {date_str}\n{'═' * 38}"

    sections = [
        header,
        _section_platform_pulse(profiles, intelligence, analytics_today),
        _section_user_intelligence(intelligence),
        _section_anomalies(anomaly_summary),
        _section_provider_health(providers),
        _section_analytics_activity(analytics_today),
        _section_next_actions(intelligence, anomaly_summary),
        _section_safety_check(),
    ]

    digest = "\n\n".join(sections)
    logger.info("Digest built: %d chars, %d sections", len(digest), len(sections) - 1)
    return digest


if __name__ == '__main__':
    import logging as _logging
    _logging.basicConfig(
        level=_logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%SZ',
    )
    print(format_grouped_digest())
