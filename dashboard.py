#!/usr/bin/env python3
"""
Nexus AI Trading Dashboard
Real-time monitoring and visualization of trading activity
"""

import os
import json
import ssl
import urllib.request as _ureq
import urllib.error as _uerr
import subprocess
import socket
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template_string, jsonify, request
from typing import Dict, Any, List, Optional
import logging

# SSL context using certifi CA bundle — required on macOS Python 3.14
try:
    import certifi as _certifi
    _SSL_CTX = ssl.create_default_context(cafile=_certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

# Load .env from nexus-ai root so launchd-launched process has full env
_env_path = Path(__file__).parent / '.env'
if _env_path.exists():
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

try:
    import requests as _requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('Dashboard')

class NexusDashboard:
    """Nexus trading dashboard with real-time metrics"""

    def __init__(self, config_file: str = "telegram_config.json"):
        self.app = Flask(__name__)
        self.config = self.load_config(config_file)
        self.setup_routes()

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load dashboard configuration"""
        default_config = {
            'nexus_api_url': 'http://localhost:3000',
            'hermes_url': 'http://localhost:8642',
            'supabase_url': 'YOUR_SUPABASE_URL',
            'supabase_key': 'YOUR_SUPABASE_ANON_KEY'
        }

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logger.error(f"Error loading config: {e}")

        return default_config

    def setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>Nexus AI Trading Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #fff;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            text-align: center;
            margin-bottom: 40px;
            padding: 20px;
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.8; font-size: 0.9em; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            padding: 20px;
            transition: all 0.3s;
        }
        .card:hover { background: rgba(255,255,255,0.15); }
        .card h3 { margin-bottom: 15px; font-size: 0.9em; opacity: 0.8; }
        .metric { font-size: 2em; font-weight: bold; margin-bottom: 10px; }
        .status { display: flex; align-items: center; gap: 8px; }
        .status-dot { width: 12px; height: 12px; border-radius: 50%; }
        .status-dot.online { background: #4ade80; }
        .status-dot.offline { background: #ef4444; }
        .chart { background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px; margin-top: 10px; }
        .table { width: 100%; font-size: 0.9em; }
        .table td { padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .positive { color: #4ade80; }
        .negative { color: #ef4444; }
        .refresh { text-align: center; margin: 20px 0; }
        .button { 
            background: rgba(59, 130, 246, 0.8);
            border: 1px solid rgba(59, 130, 246, 1);
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9em;
        }
        .button:hover { background: rgba(59, 130, 246, 1); }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🦞 Nexus AI Trading Dashboard</h1>
            <p>Real-time AI Trading System Monitoring</p>
        </div>

        <div class="grid">
            <!-- System Status -->
            <div class="card">
                <h3>🤖 System Status</h3>
                <div class="status">
                    <div class="status-dot online"></div>
                    <span id="system-status">Connected</span>
                </div>
                <p style="font-size: 0.8em; margin-top: 10px; opacity: 0.7;" id="last-update">Last update: now</p>
            </div>

            <!-- Trading Metrics -->
            <div class="card">
                <h3>📊 Today's P&L</h3>
                <div class="metric positive" id="daily-pnl">+$0.00</div>
                <p style="font-size: 0.8em; opacity: 0.7;">Win Rate: <span id="win-rate">0%</span></p>
            </div>

            <!-- Active Trades -->
            <div class="card">
                <h3>📈 Active Trades</h3>
                <div class="metric" id="active-trades">0</div>
                <p style="font-size: 0.8em; opacity: 0.7;">Max Allowed: 3</p>
            </div>

            <!-- Signals Today -->
            <div class="card">
                <h3>⚡ Signals (24h)</h3>
                <div class="metric" id="signals-today">0</div>
                <p style="font-size: 0.8em; opacity: 0.7;">Executed: <span id="executed-signals">0</span></p>
            </div>

            <!-- Research Pipeline -->
            <div class="card">
                <h3>🧠 Research Status</h3>
                <div class="status">
                    <div class="status-dot online"></div>
                    <span id="research-status">Waiting for next cycle</span>
                </div>
                <p style="font-size: 0.8em; margin-top: 10px; opacity: 0.7;">Strategies: <span id="strategy-count">0</span></p>
            </div>

            <!-- Broker Connection -->
            <div class="card">
                <h3>🔗 Broker Status</h3>
                <div class="status">
                    <div class="status-dot online" id="broker-status-dot"></div>
                    <span id="broker-name">Demo Account</span>
                </div>
                <p style="font-size: 0.8em; margin-top: 10px; opacity: 0.7;">Balance: <span id="broker-balance">$10,000</span></p>
            </div>
        </div>

        <!-- Recent Trades -->
        <div class="card">
            <h3>📋 Recent Trades</h3>
            <table class="table">
                <tr style="opacity: 0.6; font-size: 0.85em;">
                    <td>Time</td>
                    <td>Symbol</td>
                    <td>Action</td>
                    <td>Entry</td>
                    <td>Current</td>
                    <td>P&L</td>
                </tr>
                <tbody id="trades-table">
                    <tr><td colspan="6" style="text-align: center; padding: 20px;">No trades yet</td></tr>
                </tbody>
            </table>
        </div>

        <div class="refresh">
            <button class="button" onclick="location.reload()">🔄 Refresh</button>
            <p style="font-size: 0.85em; margin-top: 10px; opacity: 0.7;">Auto-refresh: every 30 seconds</p>
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds
        setInterval(function() {
            fetch('/api/metrics')
                .then(r => r.json())
                .then(data => updateDashboard(data))
                .catch(e => console.error(e));
        }, 30000);

        // Initial load
        fetch('/api/metrics')
            .then(r => r.json())
            .then(data => updateDashboard(data))
            .catch(e => console.error(e));

        function updateDashboard(data) {
            document.getElementById('daily-pnl').textContent = '$' + data.daily_pnl.toFixed(2);
            document.getElementById('daily-pnl').className = 'metric ' + (data.daily_pnl >= 0 ? 'positive' : 'negative');
            document.getElementById('active-trades').textContent = data.active_trades;
            document.getElementById('signals-today').textContent = data.signals_today;
            document.getElementById('win-rate').textContent = data.win_rate + '%';
            document.getElementById('system-status').textContent = data.system_status;
            document.getElementById('last-update').textContent = 'Last update: ' + new Date().toLocaleTimeString();
        }
    </script>
</body>
</html>
            """
            return render_template_string(html)

        @self.app.route('/api/metrics')
        def get_metrics():
            """Get dashboard metrics"""
            return jsonify({
                'daily_pnl': 250.50,
                'active_trades': 1,
                'signals_today': 3,
                'win_rate': 67,
                'system_status': 'Operational',
                'strategy_count': 12
            })

        @self.app.route('/api/trades')
        def get_trades():
            """Get recent trades"""
            return jsonify([
                {
                    'time': datetime.now().isoformat(),
                    'symbol': 'EURUSD',
                    'action': 'BUY',
                    'entry': 1.0500,
                    'current': 1.0520,
                    'pnl': 20.00
                }
            ])

        @self.app.route('/api/health')
        def health():
            """Health check"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat()
            })

        @self.app.route('/api/mac-mini/status')
        def mac_mini_status():
            """
            GET /api/mac-mini/status
            Normalized Mac Mini runtime health shape for Nexus Integration Manager.
            Safe: no secrets, tokens, or raw env values are exposed.
            Accessible over Tailscale at http://100.69.193.49:3000/api/mac-mini/status
            """
            now = datetime.utcnow().isoformat() + 'Z'

            def _probe(url: str, timeout: int = 3) -> Optional[dict]:
                """Probe a local HTTP endpoint. Returns parsed JSON or None."""
                try:
                    req = _ureq.Request(url)
                    # Local HTTP — no SSL needed; use default opener
                    with _ureq.urlopen(req, timeout=timeout) as r:
                        return json.loads(r.read())
                except Exception:
                    return None

            def _sb_open(req, timeout=5):
                """Open a Supabase (HTTPS) request using certifi CA bundle."""
                return _ureq.urlopen(req, timeout=timeout, context=_SSL_CTX)

            def _supabase_heartbeat() -> dict:
                """Fetch latest worker heartbeat from Supabase."""
                supabase_url = os.getenv('SUPABASE_URL', '')
                supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '') or os.getenv('SUPABASE_KEY', '')
                if not supabase_url or not supabase_key:
                    return {'found': False, 'reason': 'supabase_not_configured'}
                try:
                    url = (supabase_url.rstrip('/') +
                           '/rest/v1/worker_heartbeats'
                           '?select=worker_id,status,current_job_id,in_flight_jobs,max_concurrency,last_heartbeat_at,last_seen_at,metadata'
                           '&worker_id=eq.mac-mini-worker-1'
                           '&order=last_seen_at.desc&limit=1')
                    req = _ureq.Request(url, headers={
                        'apikey': supabase_key,
                        'Authorization': f'Bearer {supabase_key}',
                    })
                    with _sb_open(req) as r:
                        rows = json.loads(r.read())
                    if rows:
                        return {'found': True, 'row': rows[0]}
                    return {'found': False, 'reason': 'no_heartbeat_rows'}
                except Exception as e:
                    return {'found': False, 'reason': str(e)[:80]}

            def _last_worker_error() -> Optional[str]:
                """Fetch latest failed job error from Supabase job_results."""
                supabase_url = os.getenv('SUPABASE_URL', '')
                supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '') or os.getenv('SUPABASE_KEY', '')
                if not supabase_url or not supabase_key:
                    return None
                try:
                    url = (supabase_url.rstrip('/') +
                           '/rest/v1/job_results'
                           '?select=job_type,error,created_at'
                           '&status=eq.failed'
                           '&order=created_at.desc&limit=1')
                    req = _ureq.Request(url, headers={
                        'apikey': supabase_key,
                        'Authorization': f'Bearer {supabase_key}',
                    })
                    with _sb_open(req) as r:
                        rows = json.loads(r.read())
                    if rows:
                        r0 = rows[0]
                        return f"{r0.get('job_type','?')}: {r0.get('error','?')} at {r0.get('created_at','?')}"
                    return None
                except Exception:
                    return None

            def _pilot_ready() -> bool:
                """Check integration_readiness for critical blockers."""
                supabase_url = os.getenv('SUPABASE_URL', '')
                supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '') or os.getenv('SUPABASE_KEY', '')
                if not supabase_url or not supabase_key:
                    return False
                try:
                    url = (supabase_url.rstrip('/') +
                           '/rest/v1/integration_readiness'
                           '?select=status,severity'
                           '&severity=eq.critical'
                           '&status=in.(blocked,missing)')
                    req = _ureq.Request(url, headers={
                        'apikey': supabase_key,
                        'Authorization': f'Bearer {supabase_key}',
                    })
                    with _sb_open(req) as r:
                        rows = json.loads(r.read())
                    return len(rows) == 0
                except Exception:
                    return False

            # ── Probe local services ─────────────────────────────────────────────
            signal_router_data = _probe('http://127.0.0.1:8000/health')
            hermes_data      = _probe('http://127.0.0.1:8642/health')
            heartbeat_data     = _supabase_heartbeat()
            last_error         = _last_worker_error()
            pilot_ready        = _pilot_ready()

            # ── Derive fields ────────────────────────────────────────────────────
            signal_router_healthy   = signal_router_data is not None and signal_router_data.get('status') == 'healthy'
            telegram_bridge_ready   = signal_router_healthy and bool(signal_router_data.get('telegram_configured'))
            local_assistant_ready   = hermes_data is not None and hermes_data.get('ok') is True

            hb_row = heartbeat_data.get('row') if heartbeat_data.get('found') else None
            worker_online = False
            heartbeat_at  = None
            memory_usage_mb  = None
            concurrent_jobs  = 0
            current_job_type = None

            if hb_row:
                heartbeat_at     = hb_row.get('last_heartbeat_at') or hb_row.get('last_seen_at')
                meta             = hb_row.get('metadata') or {}
                memory_usage_mb  = meta.get('memory_usage_mb')
                concurrent_jobs  = hb_row.get('in_flight_jobs', 0)
                current_job_type = meta.get('current_job_type')
                # Consider online if heartbeat is within last 2 minutes
                try:
                    from datetime import timezone
                    hb_ts = datetime.fromisoformat(heartbeat_at.replace('Z', '+00:00'))
                    age_s = (datetime.now(timezone.utc) - hb_ts).total_seconds()
                    worker_online = age_s < 120
                except Exception:
                    worker_online = True  # Can't parse → assume alive

            # Research ingestion: check if scheduler state file has recent run
            research_ingestion_ready = False
            _state_path = os.path.join(os.path.dirname(__file__), 'operations_center', 'scheduler_state.json')
            try:
                with open(_state_path) as f:
                    _state = json.load(f)
                _rp = _state.get('research_pipeline', '')
                if _rp:
                    _rp_ts = datetime.fromisoformat(_rp)
                    research_ingestion_ready = (datetime.utcnow() - _rp_ts).total_seconds() < 86400  # within 24h
            except Exception:
                pass

            status = {
                'worker_id':               'mac-mini-worker-1',
                'worker_online':           worker_online,
                'heartbeat_at':            heartbeat_at,
                'memory_usage_mb':         memory_usage_mb,
                'concurrent_jobs':         concurrent_jobs,
                'current_job_type':        current_job_type,
                'telegram_bridge_ready':   telegram_bridge_ready,
                'local_assistant_ready':   local_assistant_ready,
                'signal_router_healthy':   signal_router_healthy,
                'dashboard_healthy':       True,  # we're serving this response
                'research_ingestion_ready': research_ingestion_ready,
                'last_error':              last_error,
                'pilot_ready':             pilot_ready,
                'checked_at':              now,
            }

            http_status = 200 if worker_online else 206  # 206 = partial content / degraded
            return jsonify(status), http_status

        # ─── Portal consumption contract ─────────────────────────────────────────
        # These routes implement the AFinalChapter portal API contract.
        # Only approved, published, unexpired records from approved_signals are served.
        # Raw signal candidates NEVER appear here.

        @self.app.route('/api/trading/signals')
        def portal_signals_list():
            """
            GET /api/trading/signals
            List approved educational signals for the portal.

            Query params (all optional):
              symbol       — filter by symbol (case-insensitive)
              market_type  — forex | crypto | equity | futures | options | commodities | indices
              timeframe    — e.g. 1h, 4h, 1D
              limit        — max rows (default 20, max 100)
              offset       — pagination offset (default 0)

            Returns only: published=true, review_status='approved', expires_at > now.
            """
            supabase_url = os.getenv('SUPABASE_URL', '')
            supabase_key = os.getenv('SUPABASE_KEY', '')

            if not supabase_url or not supabase_key:
                return jsonify({'error': 'Supabase not configured'}), 503

            symbol      = (request.args.get('symbol', '') or '').upper()
            market_type = request.args.get('market_type', '')
            timeframe   = request.args.get('timeframe', '')
            try:
                limit  = min(int(request.args.get('limit',  20)), 100)
                offset = max(int(request.args.get('offset',  0)),   0)
            except ValueError:
                limit, offset = 20, 0

            # Portal-safe field list — no raw execution data
            select_fields = (
                'id,symbol,market_type,setup_type,direction,timeframe,'
                'headline,client_summary,why_it_matters,invalidation_note,'
                'confidence_label,risk_label,score_total,'
                'published_at,expires_at,review_status'
            )

            import urllib.request as _ureq
            import urllib.parse as _uparse
            from datetime import timezone as _tz

            now_iso = datetime.now(_tz.utc).isoformat()

            params = {
                'is_published':  'eq.true',
                'review_status': 'eq.approved',
                'expires_at':    f'gt.{now_iso}',
                'select':        select_fields,
                'order':         'published_at.desc',
                'limit':         str(limit),
                'offset':        str(offset),
            }
            if symbol:
                params['symbol'] = f'eq.{symbol}'
            if market_type:
                params['market_type'] = f'eq.{market_type}'
            if timeframe:
                params['timeframe'] = f'eq.{timeframe}'

            qs = '&'.join(f"{k}={_uparse.quote(str(v))}" for k, v in params.items())
            url = f"{supabase_url}/rest/v1/approved_signals?{qs}"

            try:
                req = _ureq.Request(url, headers={
                    'apikey':        supabase_key,
                    'Authorization': f'Bearer {supabase_key}',
                })
                with _ureq.urlopen(req, timeout=10) as r:
                    signals = json.loads(r.read())
                return jsonify({'data': signals, 'count': len(signals)}), 200
            except Exception as e:
                logger.error(f"Portal signals list error: {e}")
                return jsonify({'error': 'Failed to fetch signals'}), 500


        @self.app.route('/api/trading/signals/<signal_id>')
        def portal_signal_detail(signal_id: str):
            """
            GET /api/trading/signals/:id
            Single approved educational signal detail.

            Returns 404 if not found, unpublished, rejected, or expired.
            """
            supabase_url = os.getenv('SUPABASE_URL', '')
            supabase_key = os.getenv('SUPABASE_KEY', '')

            if not supabase_url or not supabase_key:
                return jsonify({'error': 'Supabase not configured'}), 503

            import urllib.request as _ureq
            import urllib.parse as _uparse
            from datetime import timezone as _tz

            # Basic UUID format check — prevent injection
            import re
            if not re.match(r'^[0-9a-f-]{36}$', signal_id, re.IGNORECASE):
                return jsonify({'error': 'invalid signal id'}), 400

            select_fields = (
                'id,symbol,market_type,setup_type,direction,timeframe,'
                'headline,client_summary,why_it_matters,invalidation_note,'
                'confidence_label,risk_label,score_total,'
                'published_at,expires_at,review_status'
            )
            now_iso = datetime.now(_tz.utc).isoformat()
            url = (
                f"{supabase_url}/rest/v1/approved_signals"
                f"?id=eq.{_uparse.quote(signal_id)}"
                f"&is_published=eq.true"
                f"&review_status=eq.approved"
                f"&expires_at=gt.{_uparse.quote(now_iso)}"
                f"&select={select_fields}"
                f"&limit=1"
            )

            try:
                req = _ureq.Request(url, headers={
                    'apikey':        supabase_key,
                    'Authorization': f'Bearer {supabase_key}',
                })
                with _ureq.urlopen(req, timeout=10) as r:
                    rows = json.loads(r.read())
                if not rows:
                    return jsonify({'error': 'signal not found or not available'}), 404
                return jsonify({'data': rows[0]}), 200
            except Exception as e:
                logger.error(f"Portal signal detail error for {signal_id}: {e}")
                return jsonify({'error': 'Failed to fetch signal'}), 500

    def run(self, host: str = '127.0.0.1', port: int = 3000, debug: bool = False):
        """Start dashboard server"""
        logger.info(f"🚀 Dashboard running at http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    dashboard = NexusDashboard()
    dashboard.run()