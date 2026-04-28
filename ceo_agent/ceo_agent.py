"""
CEO Agent.

Reads recent agent_run_summaries, deduplicates, prioritizes, and produces
an executive_briefing. Rule-based aggregation — no AI required.

Prioritization order:
  1. blockers / client_stalled          → critical
  2. funding_approved / capital changes → high
  3. credit_analysis_completed          → high
  4. signal/strategy published          → medium
  5. routine communications             → low

Deduplication:
  - If the same client_id + summary_type appears multiple times in the
    window, only the highest-priority + most recent is included.
"""

import logging
from typing import Optional, List
from autonomy.summary_service import get_recent_summaries
from ceo_agent.briefing_service import store_briefing

logger = logging.getLogger('CeoAgent')

PRIORITY_RANK = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}

BLOCKER_TYPES = {
    'blocker_detected', 'client_stalled',
}

HIGH_PRIORITY_TYPES = {
    'funding_approved', 'capital_deployment', 'capital_opportunity',
    'credit_analysis_completed', 'credit_issues_detected',
}


def _deduplicate(summaries: List[dict]) -> List[dict]:
    """
    Keep only the highest-priority + most recent summary per
    (client_id, summary_type) pair. Summaries without a client_id
    are always kept.
    """
    seen: dict = {}
    deduplicated = []
    for s in summaries:
        cid  = s.get('client_id')
        stype = s.get('summary_type', '')
        if not cid:
            deduplicated.append(s)
            continue
        key = (cid, stype)
        if key not in seen:
            seen[key] = s
        else:
            existing_rank = PRIORITY_RANK.get(seen[key].get('priority', 'low'), 3)
            new_rank      = PRIORITY_RANK.get(s.get('priority', 'low'), 3)
            if new_rank < existing_rank:
                seen[key] = s
    deduplicated += list(seen.values())
    return deduplicated


def _extract_blockers(summaries: List[dict]) -> List[dict]:
    blockers = []
    for s in summaries:
        if s.get('summary_type') in BLOCKER_TYPES or s.get('priority') == 'critical':
            sp = s.get('structured_payload') or {}
            blockers.append({
                'agent':       s.get('agent_name'),
                'client_id':   s.get('client_id'),
                'description': s.get('summary_text', '')[:200],
                'blockers':    sp.get('blockers', []),
                'created_at':  s.get('created_at'),
            })
    return blockers


def _extract_top_updates(summaries: List[dict], limit: int = 10) -> List[dict]:
    """Return the top N updates sorted by priority, excluding blockers."""
    non_blockers = [s for s in summaries if s.get('summary_type') not in BLOCKER_TYPES]
    sorted_s = sorted(
        non_blockers,
        key=lambda x: (PRIORITY_RANK.get(x.get('priority', 'low'), 3), x.get('created_at', ''))
    )
    updates = []
    for s in sorted_s[:limit]:
        sp = s.get('structured_payload') or {}
        updates.append({
            'agent':        s.get('agent_name'),
            'client_id':    s.get('client_id'),
            'summary_type': s.get('summary_type'),
            'text':         s.get('summary_text', '')[:300],
            'priority':     s.get('priority'),
            'next_action':  sp.get('recommended_next_action', ''),
            'follow_up':    sp.get('follow_up_needed', False),
            'created_at':   s.get('created_at'),
        })
    return updates


def _extract_recommended_actions(summaries: List[dict]) -> List[dict]:
    """Pull recommended_next_action from high-priority follow_up_needed summaries."""
    actions = []
    for s in summaries:
        sp = s.get('structured_payload') or {}
        if not sp.get('follow_up_needed'):
            continue
        action = sp.get('recommended_next_action', '')
        if not action:
            continue
        priority = s.get('priority', 'medium')
        if PRIORITY_RANK.get(priority, 3) > 2:
            continue  # skip low
        actions.append({
            'action':     action,
            'agent':      s.get('agent_name'),
            'client_id':  s.get('client_id'),
            'urgency':    priority,
            'created_at': s.get('created_at'),
        })
    # Deduplicate by action text
    seen_actions = set()
    unique = []
    for a in actions:
        key = a['action'][:80]
        if key not in seen_actions:
            seen_actions.add(key)
            unique.append(a)
    return unique[:10]


def _build_headline(summaries: List[dict], blockers: List[dict]) -> str:
    total    = len(summaries)
    n_block  = len(blockers)
    n_high   = sum(1 for s in summaries if s.get('priority') in ('critical', 'high'))
    n_follow = sum(
        1 for s in summaries
        if (s.get('structured_payload') or {}).get('follow_up_needed')
    )
    parts = [f"{total} agent update(s)"]
    if n_block:
        parts.append(f"{n_block} blocker(s)")
    if n_high:
        parts.append(f"{n_high} high-priority")
    if n_follow:
        parts.append(f"{n_follow} need follow-up")
    return ' | '.join(parts)


def _build_summary_text(
    summaries: List[dict],
    blockers: List[dict],
    top_updates: List[dict],
) -> str:
    lines = []
    if blockers:
        lines.append(f"BLOCKERS ({len(blockers)}): " +
                     '; '.join(b['description'][:80] for b in blockers[:3]))
    if top_updates:
        lines.append(f"TOP UPDATES ({len(top_updates)}):")
        for u in top_updates[:5]:
            cid = f" [client {u['client_id'][:8]}]" if u.get('client_id') else ''
            lines.append(f"  {u['agent']}{cid}: {u['text'][:120]}")
    if not lines:
        lines.append("No significant activity in this window.")
    return '\n'.join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_briefing(
    hours: int       = 24,
    brief_type: str  = 'periodic',
    min_updates: int = 1,
) -> Optional[str]:
    """
    Aggregate recent summaries and store an executive briefing.
    Returns the briefing id, or None if nothing to report.
    """
    logger.info(f"CEO agent running [{brief_type}] window={hours}h")

    raw_summaries = get_recent_summaries(hours=hours, limit=200)
    if len(raw_summaries) < min_updates:
        logger.info(f"No summaries to brief ({len(raw_summaries)} < {min_updates})")
        return None

    summaries = _deduplicate(raw_summaries)
    blockers  = _extract_blockers(summaries)

    # For critical briefings triggered by blockers, override brief_type
    if blockers and brief_type == 'periodic':
        brief_type = 'critical'

    top_updates          = _extract_top_updates(summaries)
    recommended_actions  = _extract_recommended_actions(summaries)
    headline             = _build_headline(summaries, blockers)
    summary_text         = _build_summary_text(summaries, blockers, top_updates)

    briefing_id = store_briefing(
        headline=headline,
        summary=summary_text,
        brief_type=brief_type,
        top_updates=top_updates,
        blockers=blockers,
        recommended_actions=recommended_actions,
    )

    logger.info(
        f"Briefing stored id={briefing_id} type={brief_type} "
        f"updates={len(top_updates)} blockers={len(blockers)} "
        f"actions={len(recommended_actions)}"
    )
    return briefing_id
