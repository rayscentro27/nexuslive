"""
API Marketplace.

Defines available Nexus services exposed via the API layer.
Each service maps to a scope, a description, and a handler.

Services:
  funding_analysis   — analyse a client for funding products
  credit_analysis    — run credit score assessment
  strategy_insights  — pull recent approved strategies
  research_data      — query research summaries
  lead_management    — create/update lead profiles

Usage (from a Flask/FastAPI route):
    from api_gateway.marketplace import dispatch_service
    from api_gateway.key_service import validate_key, has_scope

    key_row = validate_key(request.headers.get('Authorization', '').replace('Bearer ', ''))
    if not key_row:
        return {'error': 'Invalid API key'}, 401

    result = dispatch_service('funding_analysis', key_row, payload)
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger('Marketplace')

# ─── Service catalog ──────────────────────────────────────────────────────────

SERVICES = {
    'funding_analysis': {
        'scope':       'funding_analysis',
        'description': 'Analyse a client profile and return funding product matches',
        'input_fields': ['client_id', 'credit_score', 'monthly_revenue', 'time_in_business'],
    },
    'credit_analysis': {
        'scope':       'credit_analysis',
        'description': 'Run a credit assessment and return improvement recommendations',
        'input_fields': ['client_id', 'credit_score', 'derogatory_items'],
    },
    'strategy_insights': {
        'scope':       'strategy_insights',
        'description': 'Return recent approved trading/business strategies',
        'input_fields': ['domain', 'limit'],
    },
    'research_data': {
        'scope':       'research_data',
        'description': 'Query research summaries by domain or keyword',
        'input_fields': ['query', 'domain', 'limit'],
    },
    'lead_management': {
        'scope':       'lead_management',
        'description': 'Create or update lead profiles in the Nexus CRM',
        'input_fields': ['external_id', 'channel', 'name', 'interest'],
    },
}


def get_catalog() -> list:
    """Return the full service catalog (safe to expose publicly)."""
    return [
        {'service': name, 'description': cfg['description'], 'required_scope': cfg['scope']}
        for name, cfg in SERVICES.items()
    ]


# ─── Service handlers ─────────────────────────────────────────────────────────

def _handle_funding_analysis(payload: dict) -> dict:
    client_id      = payload.get('client_id', '')
    credit_score   = int(payload.get('credit_score', 0))
    monthly_rev    = float(payload.get('monthly_revenue', 0))
    time_in_biz    = int(payload.get('time_in_business', 0))  # months

    products = []
    if credit_score >= 680 and monthly_rev >= 10000 and time_in_biz >= 12:
        products.append({'product': 'SBA Loan', 'max_amount': 500000, 'rate': '6–9%', 'timeline': '30–60 days'})
    if credit_score >= 600 and monthly_rev >= 5000:
        products.append({'product': 'Business Line of Credit', 'max_amount': 150000, 'rate': '12–24%', 'timeline': '3–7 days'})
    if monthly_rev >= 3000:
        products.append({'product': 'Revenue-Based Advance', 'max_amount': monthly_rev * 3, 'rate': '1.2–1.5x factor', 'timeline': '24–72 hours'})
    if credit_score >= 550:
        products.append({'product': 'Equipment Financing', 'max_amount': 100000, 'rate': '8–18%', 'timeline': '5–10 days'})

    return {
        'client_id':         client_id,
        'products_matched':  len(products),
        'products':          products,
        'recommendation':    products[0]['product'] if products else 'Credit improvement needed',
    }


def _handle_credit_analysis(payload: dict) -> dict:
    credit_score    = int(payload.get('credit_score', 0))
    derogatory      = int(payload.get('derogatory_items', 0))

    tier = 'excellent' if credit_score >= 750 else \
           'good'      if credit_score >= 680 else \
           'fair'      if credit_score >= 600 else \
           'poor'

    recs = []
    if derogatory > 0:
        recs.append(f"Dispute {derogatory} derogatory item(s) with all 3 bureaus")
    if credit_score < 680:
        recs.append("Pay down revolving balances below 30% utilization")
        recs.append("Avoid new hard inquiries for 90 days")
    if credit_score < 600:
        recs.append("Become an authorized user on a seasoned positive account")
        recs.append("Open a secured credit card to build positive history")

    return {
        'score':            credit_score,
        'tier':             tier,
        'funding_eligible': credit_score >= 550,
        'recommendations':  recs,
        'estimated_improvement': '30–80 points in 90 days' if recs else 'Maintain current habits',
    }


def _handle_strategy_insights(payload: dict) -> dict:
    domain = payload.get('domain', 'trading')
    limit  = min(int(payload.get('limit', 5)), 20)
    try:
        import urllib.request
        key = os.getenv('SUPABASE_KEY', '')
        url = (
            f"{os.getenv('SUPABASE_URL', '')}/rest/v1/"
            f"research?domain=eq.{domain}&order=created_at.desc&limit={limit}&select=title,summary,created_at"
        )
        req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())
        return {'domain': domain, 'count': len(rows), 'insights': rows}
    except Exception:
        return {'domain': domain, 'count': 0, 'insights': []}


def _handle_research_data(payload: dict) -> dict:
    query  = payload.get('query', '')
    domain = payload.get('domain', '')
    limit  = min(int(payload.get('limit', 10)), 50)
    try:
        import urllib.request, urllib.parse
        key   = os.getenv('SUPABASE_KEY', '')
        parts = [f"limit={limit}", "select=title,summary,domain,created_at", "order=created_at.desc"]
        if domain:
            parts.append(f"domain=eq.{domain}")
        if query:
            parts.append(f"summary=ilike.{urllib.parse.quote('%' + query + '%')}")
        url = f"{os.getenv('SUPABASE_URL', '')}/rest/v1/research?{'&'.join(parts)}"
        req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())
        return {'query': query, 'count': len(rows), 'results': rows}
    except Exception:
        return {'query': query, 'count': 0, 'results': []}


def _handle_lead_management(payload: dict) -> dict:
    from sales_agent.conversation_service import get_or_create_lead
    lead = get_or_create_lead(
        external_id=payload.get('external_id', ''),
        channel=payload.get('channel', 'api'),
        name=payload.get('name', ''),
        interest=payload.get('interest', ''),
    )
    return {'lead_id': lead.get('id'), 'status': lead.get('status', 'new')}


_HANDLERS = {
    'funding_analysis':  _handle_funding_analysis,
    'credit_analysis':   _handle_credit_analysis,
    'strategy_insights': _handle_strategy_insights,
    'research_data':     _handle_research_data,
    'lead_management':   _handle_lead_management,
}


def dispatch_service(service_name: str, key_row: dict, payload: dict) -> dict:
    """
    Route a validated API request to the appropriate service handler.
    Checks scope before executing.
    """
    from api_gateway.key_service import has_scope, log_usage

    service = SERVICES.get(service_name)
    if not service:
        return {'error': f'Unknown service: {service_name}', 'status': 404}

    if not has_scope(key_row, service['scope']):
        return {'error': f"API key missing scope: {service['scope']}", 'status': 403}

    handler = _HANDLERS.get(service_name)
    if not handler:
        return {'error': 'Service not implemented', 'status': 501}

    try:
        result = handler(payload)
        log_usage(key_row['id'], f'/api/{service_name}', status_code=200,
                  org_id=key_row.get('org_id'))
        return {'success': True, 'service': service_name, 'data': result}
    except Exception as e:
        log_usage(key_row['id'], f'/api/{service_name}', status_code=500,
                  org_id=key_row.get('org_id'))
        logger.error(f"Service {service_name} failed: {e}")
        return {'error': str(e), 'status': 500}
