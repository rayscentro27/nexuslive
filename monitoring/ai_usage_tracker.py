"""
AI Usage Tracker.

Records each AI API call into ai_usage_log with real token counts.
Polls OpenRouter usage API for authoritative monthly spend.
Alerts via Telegram when monthly budget thresholds are crossed.

Usage:
    from monitoring.ai_usage_tracker import track_ai_call, timed_ai_call

    # Manual tracking after a call:
    track_ai_call(
        caller='signal_reviewer',
        model='anthropic/claude-haiku-4-5',
        provider='openrouter',
        prompt_tokens=320,
        completion_tokens=95,
        latency_ms=1200,
    )

    # Context manager (tracks timing + token extraction automatically):
    with timed_ai_call('research_brain', model='hermes', provider='hermes',
                       prompt=prompt_text) as ctx:
        response = call_hermes(prompt)
        ctx.set_response(response)   # pass full API response dict
"""

import os
import json
import time
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('AIUsageTracker')

SUPABASE_URL       = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY       = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID', '')

# ── Per-model cost rates (USD per 1M tokens, input / output) ─────────────────
MODEL_RATES: dict = {
    'anthropic/claude-haiku-4-5':        (0.80,   4.00),
    'anthropic/claude-sonnet-4-6':       (3.00,  15.00),
    'anthropic/claude-opus-4-7':        (15.00,  75.00),
    'openai/gpt-4o-mini':                (0.15,   0.60),
    'openai/gpt-4o':                     (2.50,  10.00),
    'mistralai/mistral-7b-instruct':     (0.07,   0.07),
    'meta-llama/llama-3.1-8b-instruct':  (0.06,   0.06),
    'hermes':                            (0.00,   0.00),
}
DEFAULT_RATE = (1.00, 3.00)


def cost_for_tokens(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    in_rate, out_rate = MODEL_RATES.get(model, DEFAULT_RATE)
    return round((prompt_tokens * in_rate + completion_tokens * out_rate) / 1_000_000, 8)


# ── Supabase helpers ──────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type':  'application/json',
        'Prefer':        'return=minimal',
    }


def _sb_post(path: str, row: dict) -> bool:
    url  = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(row).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=6):
            return True
    except Exception as e:
        logger.debug(f"track insert failed: {e}")
        return False


def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.debug(f"sb_get {path} failed: {e}")
        return []


def _sb_patch(path: str, row: dict) -> bool:
    url  = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(row).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=6):
            return True
    except Exception as e:
        logger.debug(f"sb_patch failed: {e}")
        return False


# ── Core tracking ─────────────────────────────────────────────────────────────

def track_ai_call(
    caller: str,
    model: str                = 'hermes',
    provider: str             = 'hermes',
    prompt_tokens: int        = 0,
    completion_tokens: int    = 0,
    prompt_chars: int         = 0,
    response_chars: int       = 0,
    latency_ms: int           = 0,
    status: str               = 'ok',
    cost_usd: Optional[float] = None,
    meta: Optional[dict]      = None,
) -> bool:
    """Insert one ai_usage_log row. Fire-and-forget — never raises."""
    total_tokens = prompt_tokens + completion_tokens
    if cost_usd is None:
        if total_tokens > 0:
            cost_usd = cost_for_tokens(model, prompt_tokens, completion_tokens)
        else:
            cost_usd = round((prompt_chars + response_chars) / 1000 * 0.002, 8)

    return _sb_post('ai_usage_log', {
        'caller':            caller,
        'model':             model,
        'provider':          provider,
        'prompt_tokens':     prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens':      total_tokens,
        'prompt_chars':      prompt_chars,
        'response_chars':    response_chars,
        'latency_ms':        latency_ms,
        'cost_usd':          cost_usd,
        'status':            status,
        'meta':              meta or {},
    })


def extract_usage_from_response(response: dict) -> tuple:
    """Pull (prompt_tokens, completion_tokens) from an OpenAI-compatible response."""
    usage = response.get('usage', {})
    prompt     = usage.get('prompt_tokens') or usage.get('input_tokens') or 0
    completion = usage.get('completion_tokens') or usage.get('output_tokens') or 0
    return int(prompt), int(completion)


# ── Context manager ───────────────────────────────────────────────────────────

class timed_ai_call:
    """
    Context manager — records timing and extracts token counts automatically.

        with timed_ai_call('signal_reviewer',
                           model='anthropic/claude-haiku-4-5',
                           provider='openrouter',
                           prompt=prompt_text) as ctx:
            api_response = call_openrouter(prompt_text)
            ctx.set_response(api_response)  # full dict or plain string
    """

    def __init__(self, caller: str, model: str = 'hermes',
                 provider: str = 'hermes', prompt: str = ''):
        self.caller             = caller
        self.model              = model
        self.provider           = provider
        self.prompt             = prompt
        self._response_text     = ''
        self._prompt_tokens     = 0
        self._completion_tokens = 0
        self._start             = 0.0

    def set_response(self, response):
        if isinstance(response, dict):
            self._prompt_tokens, self._completion_tokens = extract_usage_from_response(response)
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            self._response_text = content or ''
        else:
            self._response_text = str(response)

    def __enter__(self):
        self._start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = int((time.time() - self._start) * 1000)
        track_ai_call(
            caller=self.caller,
            model=self.model,
            provider=self.provider,
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            prompt_chars=len(self.prompt),
            response_chars=len(self._response_text),
            latency_ms=latency,
            status='error' if exc_type else 'ok',
        )
        return False


# ── OpenRouter spend sync ─────────────────────────────────────────────────────

def sync_openrouter_spend() -> Optional[float]:
    """
    Fetch current month's authoritative spend from OpenRouter.
    Updates ai_token_budget.month_spend_usd for provider=openrouter.
    Returns USD spent, or None on failure.
    """
    if not OPENROUTER_API_KEY:
        return None

    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/auth/key',
        headers={'Authorization': f'Bearer {OPENROUTER_API_KEY}'},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except Exception as e:
        logger.warning(f"OpenRouter spend fetch failed: {e}")
        return None

    usage_usd = data.get('data', {}).get('usage')
    if usage_usd is None:
        return None

    usage_usd     = round(float(usage_usd), 6)
    current_month = datetime.now(timezone.utc).strftime('%Y-%m')

    _sb_patch('ai_token_budget?provider=eq.openrouter', {
        'month_spend_usd': usage_usd,
        'current_month':   current_month,
        'last_synced_at':  datetime.now(timezone.utc).isoformat(),
        'updated_at':      datetime.now(timezone.utc).isoformat(),
    })
    logger.info(f"OpenRouter spend synced: ${usage_usd:.4f} ({current_month})")
    return usage_usd


# ── Budget check + alert ──────────────────────────────────────────────────────

def _send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url  = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    data = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
    req  = urllib.request.Request(url, data=data,
                                  headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=8):
            pass
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")


def check_budgets() -> list:
    """
    Check all provider budgets against monthly limits.
    Sends Telegram alert for any that hit their alert_pct threshold.
    Returns list of breached providers.
    """
    rows   = _sb_get('ai_token_budget?select=*')
    alerts = []

    for row in rows:
        provider  = row.get('provider', '?')
        limit     = float(row.get('monthly_limit_usd') or 0)
        spend     = float(row.get('month_spend_usd') or 0)
        alert_pct = int(row.get('alert_pct') or 80)

        if limit <= 0:
            continue

        pct = (spend / limit) * 100
        if pct >= alert_pct:
            alerts.append({'provider': provider, 'spend': spend,
                           'limit': limit, 'pct': round(pct, 1)})

    if alerts:
        lines = ['⚠️ <b>AI Budget Alert</b>\n']
        for a in alerts:
            lines.append(
                f"  {a['provider'].upper()}: ${a['spend']:.2f} / ${a['limit']:.2f} "
                f"({a['pct']}% used)"
            )
        _send_telegram('\n'.join(lines))

    return alerts


def get_daily_summary() -> dict:
    """Return today's token usage and cost broken down by model."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    rows  = _sb_get(
        f"ai_usage_log?created_at=gt.{today.isoformat()}"
        f"&select=model,provider,prompt_tokens,completion_tokens,total_tokens,cost_usd,status"
        f"&limit=10000"
    )

    by_model: dict = {}
    total_cost = 0.0
    total_tokens = 0

    for r in rows:
        model = r.get('model', 'unknown')
        if model not in by_model:
            by_model[model] = {'calls': 0, 'tokens': 0, 'cost_usd': 0.0, 'errors': 0}
        by_model[model]['calls']    += 1
        by_model[model]['tokens']   += int(r.get('total_tokens') or 0)
        by_model[model]['cost_usd'] += float(r.get('cost_usd') or 0)
        if r.get('status') == 'error':
            by_model[model]['errors'] += 1
        total_cost   += float(r.get('cost_usd') or 0)
        total_tokens += int(r.get('total_tokens') or 0)

    return {
        'date':         today.strftime('%Y-%m-%d'),
        'total_calls':  len(rows),
        'total_tokens': total_tokens,
        'total_cost':   round(total_cost, 6),
        'by_model':     by_model,
    }


# ── Scheduler task (called by scheduler.py) ───────────────────────────────────

def run_token_check():
    """
    Daily task for the scheduler:
      1. Sync OpenRouter spend
      2. Check budgets and alert if over threshold
      3. Send daily summary to Telegram
    """
    sync_openrouter_spend()
    check_budgets()

    summary = get_daily_summary()
    lines = [
        f"📊 <b>Daily AI Usage — {summary['date']}</b>",
        f"Calls: {summary['total_calls']}  |  Tokens: {summary['total_tokens']:,}  |  Cost: ${summary['total_cost']:.4f}",
        "",
    ]
    if summary['by_model']:
        lines.append("<b>By model:</b>")
        for model, d in sorted(summary['by_model'].items(), key=lambda x: -x[1]['cost_usd']):
            lines.append(
                f"  {model}: {d['calls']} calls, {d['tokens']:,} tokens, "
                f"${d['cost_usd']:.4f}"
                + (f" ⚠ {d['errors']} errors" if d['errors'] else "")
            )
    _send_telegram('\n'.join(lines))
    logger.info(f"Token check done — {summary['total_calls']} calls, "
                f"{summary['total_tokens']:,} tokens, ${summary['total_cost']:.4f} today")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import argparse
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    # Load .env
    _env = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(_env):
        with open(_env) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())
        SUPABASE_URL       = os.getenv('SUPABASE_URL', '')
        SUPABASE_KEY       = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')
        OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
        TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
        TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID', '')

    p = argparse.ArgumentParser(description='AI Usage Tracker')
    p.add_argument('--sync-spend',   action='store_true', help='Sync OpenRouter spend')
    p.add_argument('--check-budget', action='store_true', help='Check budgets and alert')
    p.add_argument('--summary',      action='store_true', help='Print today\'s summary')
    p.add_argument('--daily',        action='store_true', help='Run full daily check')
    args = p.parse_args()

    if args.sync_spend:
        spend = sync_openrouter_spend()
        print(f"OpenRouter spend: ${spend:.4f}" if spend is not None else "Sync failed")

    if args.check_budget:
        alerts = check_budgets()
        print('\n'.join(
            f"ALERT {a['provider']}: ${a['spend']:.2f}/${a['limit']:.2f} ({a['pct']}%)"
            for a in alerts
        ) or "All budgets within limits")

    if args.summary:
        s = get_daily_summary()
        print(f"\nAI Usage — {s['date']}")
        print(f"  Calls:  {s['total_calls']}")
        print(f"  Tokens: {s['total_tokens']:,}")
        print(f"  Cost:   ${s['total_cost']:.6f}")
        for model, d in sorted(s['by_model'].items(), key=lambda x: -x[1]['cost_usd']):
            print(f"  {model:<45} calls={d['calls']:>4}  tokens={d['tokens']:>8,}  "
                  f"cost=${d['cost_usd']:.6f}  errors={d['errors']}")

    if args.daily:
        run_token_check()
