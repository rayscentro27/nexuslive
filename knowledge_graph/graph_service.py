"""
Knowledge Graph Service.

Manages knowledge_nodes and knowledge_edges in Supabase.

Node types: source, client, domain, strategy, signal, insight, agent
Edge types: produces, belongs_to, related_to, leads_to, contradicts, supports, generated_by

Usage:
    from knowledge_graph.graph_service import add_node, add_edge, get_neighbors, find_related

    node_id = add_node('source', entity_id=source_uuid, label='Bloomberg Feed', domain='trading')
    add_edge(node_a, node_b, 'produces', weight=0.8)
    neighbors = get_neighbors(node_id)
    related   = find_related(domain='trading', limit=20)
"""

import os
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any

logger = logging.getLogger('GraphService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

VALID_NODE_TYPES = {
    'source', 'client', 'domain', 'strategy', 'signal',
    'insight', 'agent', 'topic', 'event',
}
VALID_EDGE_TYPES = {
    'produces', 'belongs_to', 'related_to', 'leads_to',
    'contradicts', 'supports', 'generated_by', 'mentions',
}


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
            return None  # duplicate
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


# ─── Nodes ────────────────────────────────────────────────────────────────────

def add_node(
    node_type: str,
    label: str,
    entity_id: Optional[str]     = None,
    domain: Optional[str]        = None,
    properties: Optional[dict]   = None,
) -> Optional[str]:
    """
    Add a knowledge node. Returns node id or None on failure.
    If a node with the same (node_type, entity_id) already exists, returns existing id.
    """
    if node_type not in VALID_NODE_TYPES:
        logger.warning(f"Unknown node_type: {node_type}")

    # Check for existing node with same entity_id + node_type
    if entity_id:
        import urllib.parse
        existing = _sb_get(
            f"knowledge_nodes"
            f"?node_type=eq.{node_type}&entity_id=eq.{entity_id}&select=id&limit=1"
        )
        if existing:
            return existing[0]['id']

    row: dict = {
        'node_type':  node_type,
        'label':      label[:255],
        'properties': properties or {},
    }
    if entity_id:
        row['entity_id'] = entity_id
    if domain:
        row['domain'] = domain

    result = _sb_post('knowledge_nodes', row)
    if result:
        nid = result.get('id')
        logger.debug(f"Node added: {node_type} '{label}' id={nid}")
        return nid
    return None


def get_node(node_id: str) -> Optional[dict]:
    """Fetch a single node by id."""
    rows = _sb_get(f"knowledge_nodes?id=eq.{node_id}&select=*&limit=1")
    return rows[0] if rows else None


def find_node(node_type: str, entity_id: str) -> Optional[dict]:
    """Find a node by type + entity_id."""
    rows = _sb_get(
        f"knowledge_nodes?node_type=eq.{node_type}&entity_id=eq.{entity_id}&select=*&limit=1"
    )
    return rows[0] if rows else None


def get_nodes_by_domain(domain: str, limit: int = 100) -> List[dict]:
    """Return all nodes tagged with a specific domain."""
    return _sb_get(
        f"knowledge_nodes?domain=eq.{domain}&order=created_at.desc&limit={limit}&select=*"
    )


# ─── Edges ────────────────────────────────────────────────────────────────────

def add_edge(
    from_node_id: str,
    to_node_id: str,
    edge_type: str,
    weight: float              = 0.5,
    properties: Optional[dict] = None,
) -> Optional[str]:
    """
    Add a directed edge between two nodes.
    UNIQUE(from_node_id, to_node_id, edge_type) — silently skips duplicates.
    Returns edge id or None.
    """
    if edge_type not in VALID_EDGE_TYPES:
        logger.warning(f"Unknown edge_type: {edge_type}")

    row: dict = {
        'from_node_id': from_node_id,
        'to_node_id':   to_node_id,
        'edge_type':    edge_type,
        'weight':       round(max(0.0, min(1.0, weight)), 3),
        'properties':   properties or {},
    }
    result = _sb_post('knowledge_edges', row)
    if result:
        eid = result.get('id')
        logger.debug(f"Edge added: {from_node_id[:8]}→{to_node_id[:8]} [{edge_type}] w={weight}")
        return eid
    return None


def get_neighbors(
    node_id: str,
    direction: str = 'both',   # 'out', 'in', or 'both'
    edge_type: Optional[str] = None,
    limit: int = 50,
) -> List[dict]:
    """
    Return neighboring node ids and edge metadata for a given node.
    direction='out': edges where from_node_id=node_id
    direction='in':  edges where to_node_id=node_id
    direction='both': either direction
    """
    results: List[dict] = []

    def _query(filter_part: str) -> List[dict]:
        extra = f"&edge_type=eq.{edge_type}" if edge_type else ''
        return _sb_get(
            f"knowledge_edges?{filter_part}{extra}"
            f"&order=weight.desc&limit={limit}&select=*"
        )

    if direction in ('out', 'both'):
        results += _query(f"from_node_id=eq.{node_id}")
    if direction in ('in', 'both'):
        results += _query(f"to_node_id=eq.{node_id}")

    return results


def find_related(
    domain: Optional[str]    = None,
    node_type: Optional[str] = None,
    min_weight: float        = 0.5,
    limit: int               = 50,
) -> List[dict]:
    """
    Find strongly-connected nodes, optionally filtered by domain or type.
    Returns edges with weight >= min_weight.
    """
    parts = [f"weight=gte.{min_weight}", f"limit={limit}", "select=*", "order=weight.desc"]
    rows = _sb_get(f"knowledge_edges?{'&'.join(parts)}")

    if not rows or (not domain and not node_type):
        return rows

    # Filter by domain/type of endpoints
    filtered = []
    for edge in rows:
        if domain or node_type:
            fnode = get_node(edge.get('from_node_id', ''))
            tnode = get_node(edge.get('to_node_id', ''))
            nodes = [n for n in [fnode, tnode] if n]
            if domain and not any(n.get('domain') == domain for n in nodes):
                continue
            if node_type and not any(n.get('node_type') == node_type for n in nodes):
                continue
        filtered.append(edge)
    return filtered


# ─── Graph seeding helpers ─────────────────────────────────────────────────────

def ensure_source_node(source_id: str) -> Optional[str]:
    """
    Ensure a knowledge node exists for a research_source.
    Fetches source details and creates/returns the node.
    """
    import urllib.parse
    rows = _sb_get(
        f"research_sources?id=eq.{source_id}&select=label,domain,source_type&limit=1"
    )
    if not rows:
        return None
    src = rows[0]
    return add_node(
        node_type='source',
        label=src.get('label', source_id[:16]),
        entity_id=source_id,
        domain=src.get('domain'),
        properties={'source_type': src.get('source_type', 'unknown')},
    )


def ensure_domain_node(domain: str) -> Optional[str]:
    """Ensure a domain node exists (one per domain)."""
    existing = _sb_get(
        f"knowledge_nodes?node_type=eq.domain&label=eq.{domain}&select=id&limit=1"
    )
    if existing:
        return existing[0]['id']
    return add_node(node_type='domain', label=domain, domain=domain)
