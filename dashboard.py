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

    def _trading_api_data(self):
        """Shared helper: fetch engine status + recent paper trades from local sources."""
        # Engine status from local file
        status_file = Path(__file__).parent / 'logs' / 'trading_engine_status.json'
        engine = {}
        try:
            engine = json.loads(status_file.read_text())
        except Exception:
            pass

        # Recent paper trades from Supabase
        sb_url = os.getenv('SUPABASE_URL', '')
        sb_key = os.getenv('SUPABASE_KEY', '')
        trades = []
        if sb_url and sb_key:
            try:
                import requests as _req
                r = _req.get(
                    f"{sb_url}/rest/v1/paper_trading_journal_entries"
                    "?select=id,symbol,asset_class,entry_status,thesis,stop_loss,"
                    "target_price,tags,opened_at,closed_at"
                    "&order=opened_at.desc&limit=50",
                    headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'},
                    timeout=8,
                )
                trades = r.json() if r.ok else []
            except Exception:
                pass

        # Signal review log tail
        log_file = Path(__file__).parent / 'logs' / 'signal_review.log'
        log_tail = []
        try:
            lines = log_file.read_text().splitlines()
            log_tail = lines[-20:]
        except Exception:
            pass

        return engine, trades, log_tail

    # ── /api/trading/paper-trades ──────────────────────────────────────────────

    def _register_trading_routes(self):

        @self.app.route('/api/trading/paper-trades')
        def api_paper_trades():
            engine, trades, log_tail = self._trading_api_data()
            return jsonify({
                'engine':    engine,
                'trades':    trades,
                'log_tail':  log_tail,
            })

        # ── /trading  (dashboard page) ─────────────────────────────────────────

        @self.app.route('/trading')
        def trading_dashboard():
            html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nexus — Trading Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0f172a,#1e3a5f);color:#e2e8f0;min-height:100vh;padding:20px}
.container{max-width:1400px;margin:0 auto}
h1{font-size:1.8em;margin-bottom:4px}
.sub{opacity:.6;font-size:.85em;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:24px}
.card{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:10px;padding:16px}
.card h3{font-size:.72em;opacity:.55;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
.card .val{font-size:1.7em;font-weight:700}
.badge{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.75em;font-weight:600}
.badge.green{background:rgba(74,222,128,.15);color:#4ade80;border:1px solid rgba(74,222,128,.3)}
.badge.red{background:rgba(239,68,68,.15);color:#f87171;border:1px solid rgba(239,68,68,.3)}
.badge.yellow{background:rgba(250,204,21,.15);color:#facc15;border:1px solid rgba(250,204,21,.3)}
.badge.blue{background:rgba(96,165,250,.15);color:#60a5fa;border:1px solid rgba(96,165,250,.3)}
.section{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:10px;padding:18px;margin-bottom:20px}
.section h2{font-size:.85em;opacity:.6;text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px}
table{width:100%;border-collapse:collapse;font-size:.85em}
th{text-align:left;padding:8px 10px;opacity:.5;font-weight:500;border-bottom:1px solid rgba(255,255,255,.1)}
td{padding:8px 10px;border-bottom:1px solid rgba(255,255,255,.06)}
tr:hover td{background:rgba(255,255,255,.04)}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;font-size:.75em}
.pill.open{background:rgba(74,222,128,.15);color:#4ade80}
.pill.closed{background:rgba(148,163,184,.1);color:#94a3b8}
.webhook-box{background:rgba(0,0,0,.3);border-radius:8px;padding:14px;font-family:monospace;font-size:.82em;word-break:break-all;color:#7dd3fc;margin-bottom:10px}
.copy-btn{background:rgba(96,165,250,.2);border:1px solid rgba(96,165,250,.4);color:#60a5fa;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:.8em;margin-top:8px}
.copy-btn:hover{background:rgba(96,165,250,.35)}
.log-box{background:rgba(0,0,0,.35);border-radius:8px;padding:12px;font-family:monospace;font-size:.75em;max-height:200px;overflow-y:auto;line-height:1.6;color:#94a3b8}
.log-box .info{color:#7dd3fc}
.log-box .warn{color:#fbbf24}
.log-box .err{color:#f87171}
.refresh-btn{background:rgba(96,165,250,.2);border:1px solid rgba(96,165,250,.4);color:#60a5fa;padding:8px 18px;border-radius:7px;cursor:pointer;font-size:.85em;margin-bottom:20px}
.refresh-btn:hover{background:rgba(96,165,250,.35)}
.nav{margin-bottom:20px;font-size:.85em}
.nav a{color:#7dd3fc;text-decoration:none;margin-right:16px;opacity:.7}
.nav a:hover{opacity:1}
.ts{font-size:.72em;opacity:.45}
#last-refresh{font-size:.75em;opacity:.4;margin-left:10px}
</style>
</head>
<body>
<div class="container">
  <div class="nav"><a href="/">← Main Dashboard</a></div>
  <h1>Trading Dashboard</h1>
  <p class="sub">Paper trading — DRY_RUN mode &nbsp;|&nbsp; Webhook: signals.goclearonline.cc</p>
  <button class="refresh-btn" onclick="loadData()">Refresh <span id="last-refresh"></span></button>

  <div class="grid" id="stat-grid">
    <div class="card"><h3>Mode</h3><div class="val" id="s-mode">—</div></div>
    <div class="card"><h3>Signals Today</h3><div class="val" id="s-count">—</div></div>
    <div class="card"><h3>Open Trades</h3><div class="val" id="s-open">—</div></div>
    <div class="card"><h3>Total Trades</h3><div class="val" id="s-total">—</div></div>
    <div class="card"><h3>Last Signal</h3><div class="val" id="s-last" style="font-size:1em">—</div></div>
  </div>

  <div class="section">
    <h2>TradingView Webhook Setup</h2>
    <div style="font-size:.85em;margin-bottom:10px;opacity:.7">Paste this URL in your TradingView alert → Webhook URL field:</div>
    <div class="webhook-box" id="webhook-url">https://signals.goclearonline.cc/webhook/tradingview</div>
    <button class="copy-btn" onclick="copyWebhook()">Copy URL</button>
    <div style="margin-top:16px;font-size:.82em;opacity:.6">Alert message body (JSON):</div>
    <div class="webhook-box" style="margin-top:6px">{
  "symbol": "{{ticker}}",
  "action": "{{strategy.order.action}}",
  "entry":  {{close}},
  "stop":   {{strategy.order.contracts}},
  "target": {{strategy.order.price}},
  "timeframe": "{{interval}}",
  "confidence": 75,
  "strategy": "my_strategy_name"
}</div>
  </div>

  <div class="section">
    <h2>Recent Paper Trades</h2>
    <table>
      <thead><tr><th>Symbol</th><th>Thesis</th><th>SL</th><th>TP</th><th>Status</th><th>Tags</th><th>Opened</th></tr></thead>
      <tbody id="trades-body"><tr><td colspan="7" style="opacity:.4;text-align:center;padding:20px">Loading...</td></tr></tbody>
    </table>
  </div>

  <div class="section">
    <h2>Signal Review Log</h2>
    <div class="log-box" id="log-box">Loading...</div>
  </div>
</div>

<script>
const WEBHOOK = 'https://signals.goclearonline.cc/webhook/tradingview';

function copyWebhook() {
  navigator.clipboard.writeText(WEBHOOK).then(() => {
    const btn = document.querySelector('.copy-btn');
    btn.textContent = 'Copied!';
    setTimeout(() => btn.textContent = 'Copy URL', 2000);
  });
}

function fmt(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});
}

function pill(status) {
  const cls = status === 'open' ? 'open' : 'closed';
  return `<span class="pill ${cls}">${status}</span>`;
}

function tagBadge(tags) {
  if (!tags || !tags.length) return '';
  return tags.slice(0,3).map(t => `<span class="badge blue" style="margin:1px;font-size:.7em">${t}</span>`).join('');
}

function colorLine(line) {
  if (line.includes('ERROR')) return `<div class="err">${line}</div>`;
  if (line.includes('WARNING') || line.includes('WARN') || line.includes('heuristic')) return `<div class="warn">${line}</div>`;
  return `<div class="info">${line}</div>`;
}

async function loadData() {
  try {
    const res = await fetch('/api/trading/paper-trades');
    const d = await res.json();

    const eng = d.engine || {};
    document.getElementById('s-mode').innerHTML =
      eng.dry_run ? '<span class="badge green">DRY RUN</span>' : '<span class="badge red">LIVE</span>';
    document.getElementById('s-count').textContent = eng.signals_processed ?? '—';

    const trades = d.trades || [];
    const open = trades.filter(t => t.entry_status === 'open').length;
    document.getElementById('s-open').textContent = open;
    document.getElementById('s-total').textContent = trades.length;

    const last = eng.last_signal;
    document.getElementById('s-last').textContent = last
      ? `${last.symbol} ${last.action} @ ${last.entry_price ?? last.entry ?? '—'}`
      : '—';

    // Trades table
    const tbody = document.getElementById('trades-body');
    if (!trades.length) {
      tbody.innerHTML = '<tr><td colspan="7" style="opacity:.4;text-align:center;padding:20px">No paper trades yet</td></tr>';
    } else {
      tbody.innerHTML = trades.map(t => `
        <tr>
          <td><strong>${t.symbol}</strong><br><span class="ts">${t.asset_class || ''}</span></td>
          <td style="max-width:260px;opacity:.8">${(t.thesis||'').slice(0,80)}${t.thesis && t.thesis.length>80?'…':''}</td>
          <td class="ts">${t.stop_loss ? Number(t.stop_loss).toFixed(4) : '—'}</td>
          <td class="ts">${t.target_price ? Number(t.target_price).toFixed(4) : '—'}</td>
          <td>${pill(t.entry_status)}</td>
          <td>${tagBadge(t.tags)}</td>
          <td class="ts">${fmt(t.opened_at)}</td>
        </tr>`).join('');
    }

    // Log
    const logBox = document.getElementById('log-box');
    if (d.log_tail && d.log_tail.length) {
      logBox.innerHTML = d.log_tail.map(colorLine).join('');
      logBox.scrollTop = logBox.scrollHeight;
    } else {
      logBox.textContent = 'No log data available.';
    }

    document.getElementById('last-refresh').textContent =
      '· ' + new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
  } catch(e) {
    console.error('loadData error:', e);
  }
}

loadData();
setInterval(loadData, 30000);
</script>
</body>
</html>"""
            return html

    def run(self, host: str = '127.0.0.1', port: int = 3000, debug: bool = False):
        """Start dashboard server"""
        self._register_trading_routes()
        logger.info(f"🚀 Dashboard running at http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    dashboard = NexusDashboard()
    dashboard.run()