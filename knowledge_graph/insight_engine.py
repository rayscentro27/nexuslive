"""
Cross-Domain Insight Engine.

Finds patterns across the knowledge graph where nodes from different domains
are strongly connected, and materializes those patterns as cross_domain_insights.

Pattern types:
  'cross_domain_signal'   — a signal/strategy appears in 2+ domains
  'shared_source'         — a source covers multiple domains
  'domain_convergence'    — two domains both heavily reference the same topics
  'strategy_bridge'       — a strategy from domain A is relevant in domain B

Each insight gets a confidence score (0-1) derived from edge weights and
co-occurrence counts.

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m knowledge_graph.insight_engine
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger('InsightEngine')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

MIN_CONFIDENCE = float(os.getenv('INSIGHT_MIN_CONFIDENCE', '0.5'))


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
    }


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def _sb_post(path: str, body: dict) -> Optional[dict]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return None
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


def _upsert_insight(row: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/cross_domain_insights"
    data = json.dumps(row).encode()
    h    = _headers()
    h['Prefer'] = 'return=minimal'
    req  = urllib.request.Request(url, data=data, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"Upsert insight → {e}")
        return False


# ─── Pattern detectors ────────────────────────────────────────────────────────

def _detect_shared_sources(nodes: List[dict], edges: List[dict]) -> int:
    """
    Find source nodes that are connected to multiple domain nodes.
    Insight: a single source covers multiple domains → cross_domain_signal.
    """
    # Build a map: node_id → domain (for domain-type nodes)
    domain_nodes: Dict[str, str] = {
        n['id']: n['label']
        for n in nodes if n.get('node_type') == 'domain'
    }
    # Build: source_node_id → set of domains it connects to
    source_to_domains: Dict[str, set] = {}

    for edge in edges:
        if edge.get('edge_type') != 'belongs_to':
            continue
        from_id = edge.get('from_node_id', '')
        to_id   = edge.get('to_node_id', '')
        # from=source → to=domain
        if to_id in domain_nodes:
            source_to_domains.setdefault(from_id, set()).add(domain_nodes[to_id])

    count = 0
    for source_id, domains in source_to_domains.items():
        if len(domains) < 2:
            continue
        domain_list = sorted(domains)
        # Look up source label
        src_nodes = [n for n in nodes if n['id'] == source_id]
        label     = src_nodes[0].get('label', source_id[:12]) if src_nodes else source_id[:12]

        confidence = min(0.5 + (len(domains) - 2) * 0.1, 0.95)
        summary = (
            f"Source '{label}' spans {len(domains)} domain(s): {', '.join(domain_list)}. "
            f"This cross-domain source may yield insights applicable across multiple strategies."
        )

        for i, da in enumerate(domain_list):
            for db in domain_list[i+1:]:
                row = {
                    'insight_type':     'shared_source',
                    'domain_a':         da,
                    'domain_b':         db,
                    'related_entities': json.dumps([source_id]),
                    'summary':          summary,
                    'confidence':       round(confidence, 3),
                    'status':           'active',
                }
                if _upsert_insight(row):
                    count += 1
                    logger.info(f"Insight: shared_source {da}↔{db} via '{label}'")

    return count


def _detect_domain_convergence(nodes: List[dict], edges: List[dict]) -> int:
    """
    Find two domains that share multiple node connections (via related_to or supports edges).
    Confidence based on number of shared connections.
    """
    # Map node_id → domain
    node_domain: Dict[str, Optional[str]] = {n['id']: n.get('domain') for n in nodes}

    # Count cross-domain edge pairs
    pair_counts: Dict[Tuple[str, str], List[str]] = {}
    entity_pairs: Dict[Tuple[str, str], List[str]] = {}

    for edge in edges:
        if edge.get('edge_type') not in ('related_to', 'supports', 'leads_to'):
            continue
        da = node_domain.get(edge.get('from_node_id', ''))
        db = node_domain.get(edge.get('to_node_id', ''))
        if not da or not db or da == db:
            continue
        pair = tuple(sorted([da, db]))
        pair_counts[pair] = pair_counts.get(pair, [])
        pair_counts[pair].append(edge.get('weight', 0.5))
        entity_pairs[pair] = entity_pairs.get(pair, [])
        entity_pairs[pair].extend([
            edge.get('from_node_id', ''), edge.get('to_node_id', '')
        ])

    count = 0
    for (da, db), weights in pair_counts.items():
        if len(weights) < 2:
            continue
        avg_weight = sum(weights) / len(weights)
        confidence = min(avg_weight * (1 + (len(weights) - 2) * 0.05), 0.95)
        if confidence < MIN_CONFIDENCE:
            continue

        entities = list(set(entity_pairs.get((da, db), [])))[:10]
        summary  = (
            f"Domain convergence detected between '{da}' and '{db}': "
            f"{len(weights)} cross-domain connection(s), avg edge weight={round(avg_weight, 2)}. "
            f"Signals and strategies in these domains may be mutually reinforcing."
        )
        row = {
            'insight_type':     'domain_convergence',
            'domain_a':         da,
            'domain_b':         db,
            'related_entities': json.dumps(entities),
            'summary':          summary,
            'confidence':       round(confidence, 3),
            'status':           'active',
        }
        if _upsert_insight(row):
            count += 1
            logger.info(f"Insight: domain_convergence {da}↔{db} confidence={round(confidence,3)}")

    return count


def _detect_strategy_bridges(nodes: List[dict], edges: List[dict]) -> int:
    """
    Find strategy nodes that are connected to topics in multiple domains.
    Strategy in domain A → referenced in domain B = strategy bridge.
    """
    strategy_nodes = {n['id']: n for n in nodes if n.get('node_type') == 'strategy'}
    node_domain    = {n['id']: n.get('domain') for n in nodes}

    # For each strategy: find which domains it connects to via 'produces'/'supports'
    strategy_domains: Dict[str, set] = {}

    for edge in edges:
        if edge.get('edge_type') not in ('produces', 'supports', 'related_to'):
            continue
        src_id = edge.get('from_node_id', '')
        tgt_id = edge.get('to_node_id', '')
        for node_id in (src_id, tgt_id):
            if node_id in strategy_nodes:
                # The other endpoint domain
                other = tgt_id if node_id == src_id else src_id
                domain = node_domain.get(other)
                if domain:
                    strategy_domains.setdefault(node_id, set()).add(domain)
                # Also include the strategy's own domain
                strat_domain = strategy_nodes[node_id].get('domain')
                if strat_domain:
                    strategy_domains.setdefault(node_id, set()).add(strat_domain)

    count = 0
    for strat_id, domains in strategy_domains.items():
        if len(domains) < 2:
            continue
        domain_list = sorted(domains)
        snode       = strategy_nodes[strat_id]
        label       = snode.get('label', strat_id[:12])
        confidence  = min(0.55 + (len(domains) - 2) * 0.1, 0.90)

        for i, da in enumerate(domain_list):
            for db in domain_list[i+1:]:
                summary = (
                    f"Strategy '{label}' bridges domains '{da}' and '{db}'. "
                    f"Applying this strategy across both domains may unlock compounding returns."
                )
                row = {
                    'insight_type':     'strategy_bridge',
                    'domain_a':         da,
                    'domain_b':         db,
                    'related_entities': json.dumps([strat_id]),
                    'summary':          summary,
                    'confidence':       round(confidence, 3),
                    'status':           'active',
                }
                if _upsert_insight(row):
                    count += 1
                    logger.info(f"Insight: strategy_bridge '{label}' {da}↔{db}")

    return count


# ─── Public API ───────────────────────────────────────────────────────────────

def run_insight_engine(node_limit: int = 500, edge_limit: int = 1000) -> dict:
    """
    Load graph nodes + edges, run all pattern detectors, store insights.
    Returns counts dict.
    """
    nodes = _sb_get(f"knowledge_nodes?select=*&limit={node_limit}")
    edges = _sb_get(f"knowledge_edges?select=*&order=weight.desc&limit={edge_limit}")

    if not nodes:
        logger.info("No nodes in graph — nothing to analyse")
        return {'shared_source': 0, 'domain_convergence': 0, 'strategy_bridge': 0, 'total': 0}

    shared   = _detect_shared_sources(nodes, edges)
    conv     = _detect_domain_convergence(nodes, edges)
    bridges  = _detect_strategy_bridges(nodes, edges)
    total    = shared + conv + bridges

    if total > 0:
        try:
            from autonomy.summary_service import write_summary
            write_summary(
                agent_name='insight_engine',
                summary_type='cross_domain_insight',
                summary_text=(
                    f"Cross-domain insight engine found {total} new pattern(s): "
                    f"{shared} shared source(s), {conv} domain convergence(s), "
                    f"{bridges} strategy bridge(s)."
                ),
                what_happened=f"Insight engine analysed {len(nodes)} nodes, {len(edges)} edges",
                what_changed=f"{total} new cross-domain insights stored",
                recommended_next_action=(
                    "Review cross_domain_insights table. Consider adding sources that "
                    "reinforce the detected convergence domains."
                ),
                follow_up_needed=(total > 3),
                priority='medium',
            )
        except Exception as e:
            logger.warning(f"Summary write failed: {e}")

    logger.info(
        f"Insight engine done: shared={shared} convergence={conv} bridges={bridges}"
    )
    return {
        'shared_source':     shared,
        'domain_convergence': conv,
        'strategy_bridge':   bridges,
        'total':             total,
    }


def get_active_insights(
    min_confidence: float    = 0.5,
    domain: Optional[str]   = None,
    insight_type: Optional[str] = None,
    limit: int               = 50,
) -> List[dict]:
    """Return active insights, optionally filtered."""
    parts = [
        'status=eq.active',
        f'confidence=gte.{min_confidence}',
        'order=confidence.desc',
        f'limit={limit}',
        'select=*',
    ]
    if insight_type:
        parts.append(f'insight_type=eq.{insight_type}')
    if domain:
        parts.append(f'domain_a=eq.{domain}')
    return _sb_get(f"cross_domain_insights?{'&'.join(parts)}")


if __name__ == '__main__':
    _env = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(_env):
        with open(_env) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s %(message)s')
    result = run_insight_engine()
    print(f"Insights generated: {result}")
