#!/usr/bin/env python3
"""
Hermes Status Bot — Telegram command interface for Nexus AI system status.

Polls @NexusHermbot for commands from Ray and responds with live system info.

Commands:
  /status    — full system status (processes + research pipeline)
  /processes — live process check (launchctl)
  /research  — research pipeline file counts + Supabase rows
  /agents    — AI employees from Supabase
  /help      — list all commands

Usage (manual):
  python3 hermes_status_bot.py
"""
import os
import sys
import time
import json
import logging
import subprocess
from datetime import datetime
from html import escape

import requests

VERSION = "1.0"

# ── Load .env ──────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())

# ── Config ─────────────────────────────────────────────────────────────────────
HERMES_TOKEN  = os.getenv('HERMES_BOT_TOKEN', '')
CHAT_ID       = os.getenv('TELEGRAM_CHAT_ID', '')
POLL_INTERVAL = int(os.getenv('HERMES_POLL_INTERVAL', '4'))
SUPABASE_URL  = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY  = os.getenv('SUPABASE_KEY', '')
HERMES_GATEWAY_URL  = os.getenv('HERMES_GATEWAY_URL', 'http://127.0.0.1:8642')
HERMES_TOKEN = os.getenv('HERMES_GATEWAY_TOKEN', '')
HERMES_MODEL = os.getenv('HERMES_MODEL', 'hermes')
NEXUS_ROOT    = os.path.dirname(os.path.abspath(__file__))
COORD_CLI     = os.path.join(NEXUS_ROOT, 'nexus_coord.py')
OFFSET_FILE   = os.path.join(NEXUS_ROOT, '.hermes_status_offset')
OPS_SNAPSHOT  = os.path.join(NEXUS_ROOT, 'scripts', 'hermes_ops_snapshot.sh')
OPS_ATTENTION = os.path.join(NEXUS_ROOT, 'scripts', 'hermes_ops_attention.sh')
SCHEDULER_SCRIPT = os.path.join(NEXUS_ROOT, 'operations_center', 'scheduler.py')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)s  %(message)s',
    datefmt='%H:%M:%S',
    stream=sys.stdout,
)
log = logging.getLogger('hermes_status')

TG_BASE = f'https://api.telegram.org/bot{HERMES_TOKEN}'


# ── Telegram helpers ───────────────────────────────────────────────────────────

def send(text: str):
    """Send a message to Ray's chat."""
    if len(text) > 4000:
        text = text[:3950] + '\n\n_(truncated)_'
    try:
        requests.post(
            f'{TG_BASE}/sendMessage',
            json={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'},
            timeout=10,
        )
    except Exception as e:
        log.warning(f'send error: {e}')


def get_updates(offset: int) -> list:
    try:
        r = requests.get(
            f'{TG_BASE}/getUpdates',
            params={
                'offset': offset, 'timeout': 10, 'limit': 20,
                'allowed_updates': json.dumps(['message']),
            },
            timeout=15,
        )
        return r.json().get('result', [])
    except Exception as e:
        log.warning(f'getUpdates error: {e}')
        return []


def run_coord_cli(*args: str) -> str:
    try:
        proc = subprocess.run(
            ['python3', COORD_CLI, *args],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=NEXUS_ROOT,
        )
    except Exception as e:
        return f'coordination command failed: {e}'

    output = (proc.stdout or '').strip()
    error = (proc.stderr or '').strip()
    if proc.returncode != 0:
        return error or output or f'coordination command failed ({proc.returncode})'
    return output or 'OK'


def format_pre(text: str) -> str:
    return f'<pre>{escape(text[:3500])}</pre>'


def run_local_command(*args: str, timeout: int = 30) -> str:
    try:
        proc = subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=NEXUS_ROOT,
        )
    except Exception as e:
        return f'command failed: {e}'

    output = (proc.stdout or '').strip()
    error = (proc.stderr or '').strip()
    if proc.returncode != 0:
        return error or output or f'command failed ({proc.returncode})'
    return output or 'OK'


# ── Supabase helper ────────────────────────────────────────────────────────────

def supabase_get(path: str) -> list:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    try:
        r = requests.get(
            f'{SUPABASE_URL}/rest/v1/{path}',
            headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'},
            timeout=10,
        )
        return r.json()
    except Exception as e:
        log.warning(f'Supabase error: {e}')
        return []


# ── Command handlers ───────────────────────────────────────────────────────────

LAUNCHD_SERVICES = [
    ('ai.hermes.gateway',              'Hermes Gateway',     '18789'),
    ('com.nexus.signal-router',          'Signal Router',        '8000'),
    ('com.nexus.trading-engine',         'Trading Engine',       '5000'),
    ('com.raymonddavis.nexus.telegram',  'Telegram Monitor',     ''),
    ('com.raymonddavis.nexus.dashboard', 'Dashboard',            '3000'),
    ('com.raymonddavis.nexus.scheduler', 'Scheduler',            ''),
    ('com.nexus.signal-review',          'Signal Review Poller', ''),
    ('com.nexus.research-worker',        'Research Worker',      ''),
    ('com.nexus.hermes-status',          'Hermes Status Bot',    ''),
]


def cmd_processes() -> str:
    raw = subprocess.run(['launchctl', 'list'], capture_output=True, text=True).stdout
    launchd = {}
    for line in raw.splitlines():
        parts = line.split('\t')
        if len(parts) == 3:
            pid, _, label = parts
            launchd[label.strip()] = pid.strip()

    lines = ['*Live Processes*\n']
    for label, name, port in LAUNCHD_SERVICES:
        pid     = launchd.get(label, '-')
        running = pid not in ('-', '')
        icon    = '✅' if running else '❌'
        pid_s   = f'PID {pid}' if running else 'stopped'
        port_s  = f':{port}' if port else ''
        lines.append(f'{icon} `{name}{port_s}` — {pid_s}')

    running_count = sum(
        1 for lbl, _, _ in LAUNCHD_SERVICES
        if launchd.get(lbl, '-') not in ('-', '')
    )
    lines.append(f'\n_{running_count}/{len(LAUNCHD_SERVICES)} services running_')
    return '\n'.join(lines)


def cmd_research() -> str:
    res   = os.path.join(NEXUS_ROOT, 'research-engine')
    lines = ['*Research Pipeline*\n']

    for label, path, ext in [
        ('Channels',    os.path.join(res, 'channels', 'trading_channels.json'), None),
        ('Transcripts', os.path.join(res, 'transcripts'), '.vtt'),
        ('Summaries',   os.path.join(res, 'summaries'),   '.summary'),
        ('Strategies',  os.path.join(res, 'strategies'),  '.summary'),
    ]:
        if ext is None:
            try:
                with open(path) as f:
                    n = len(json.load(f).get('channels', []))
                lines.append(f'• *{label}*: {n} configured')
            except Exception:
                lines.append(f'• *{label}*: ?')
        else:
            try:
                n = len([x for x in os.listdir(path) if x.endswith(ext)])
                lines.append(f'• *{label}*: {n} files')
            except Exception:
                lines.append(f'• *{label}*: 0 files')

    # Latest Supabase entry
    rows = supabase_get('research?select=created_at&order=created_at.desc&limit=1')
    latest = rows[0]['created_at'][:10] if rows else 'never'
    lines.append(f'\n☁️  Supabase latest: `{latest}`')
    return '\n'.join(lines)


def cmd_agents() -> str:
    agents = supabase_get(
        'agents?select=name,role,division,status&order=division.asc,name.asc'
    )
    if not agents:
        return '⚠️ Could not fetch agents from Supabase.'

    divs: dict = {}
    for a in agents:
        div = a.get('division') or 'Other'
        divs.setdefault(div, []).append(a)

    icons = {'active': '🟢', 'testing': '🟡', 'inactive': '🔴', 'idle': '⚪'}
    lines = ['*AI Employees*\n']
    for div, members in sorted(divs.items()):
        lines.append(f'*[{div}]*')
        for a in members:
            icon = icons.get(a.get('status', ''), '⚪')
            lines.append(f'  {icon} {a["name"]} — _{a.get("role","?")}_')

    active = sum(1 for a in agents if a.get('status') == 'active')
    lines.append(f'\n_Total: {len(agents)} · Active: {active}_')
    return '\n'.join(lines)


def cmd_status() -> str:
    return format_pre(run_local_command(OPS_SNAPSHOT, timeout=60))


def cmd_attention(_args: str = '') -> str:
    return format_pre(run_local_command(OPS_ATTENTION, timeout=60))


def cmd_coord(_args: str = '') -> str:
    return format_pre(run_coord_cli('summary'))


def cmd_activity(args: str = '') -> str:
    limit = args.strip() or '8'
    return format_pre(run_coord_cli('activity', '--limit', limit))


def cmd_tasks(args: str = '') -> str:
    agent = (args or '').strip() or 'codex'
    return format_pre(run_coord_cli('tasks', agent))


def cmd_run_leads(_args: str = '') -> str:
    return format_pre(run_local_command('python3', SCHEDULER_SCRIPT, '--run-now', 'leads', timeout=60))


def cmd_run_reputation(_args: str = '') -> str:
    return format_pre(run_local_command('python3', SCHEDULER_SCRIPT, '--run-now', 'reputation', timeout=60))


def cmd_assign(args: str) -> str:
    payload = (args or '').strip()
    if ':' not in payload:
        return 'Usage: `/assign codex: description`'
    agent, description = payload.split(':', 1)
    agent = agent.strip()
    description = description.strip()
    if not agent or not description:
        return 'Usage: `/assign codex: description`'
    return format_pre(run_coord_cli('add-task', agent, description, '--posted-by', 'hermes'))


# ── Hermes (ChatGPT OAuth) AI path ───────────────────────────────────────────

NEXUS_CONTEXT = """\
You are Hermes, the status/assistant bot for Ray Davis's Nexus AI hedge fund system.
You route through Hermes's gateway, which uses Ray's ChatGPT/Codex OAuth session.

ARCHITECTURE (6 subsystems, all on a Mac Mini unless noted):
1. AI Ops Server — Hermes Gateway on localhost:8642
2. Research Brain — YouTube → transcripts → summaries → Supabase
3. AI Workforce — Hermes agents over Telegram
4. Signal Router — TradingView webhooks → Flask (localhost:8000) → Telegram
5. Trading Engine — signal → strategy → risk manager → broker (Oanda/demo, DRY_RUN=True)
6. CRM/Client Portal — React + Netlify + Supabase (goclearonline.cc)

LAUNCHD SERVICES (all auto-start on boot):
- ai.hermes.gateway — Hermes on localhost:8642
- com.nexus.signal-router — TradingView webhook receiver on localhost:8000
- com.nexus.trading-engine — trading engine (DRY_RUN=True)
- com.raymonddavis.nexus.telegram — Telegram monitor daemon
- com.raymonddavis.nexus.dashboard — Flask dashboard on localhost:3000
- com.raymonddavis.nexus.scheduler — scheduler
- com.nexus.signal-review — signal review poller
- com.nexus.hermes-status — this bot
- com.nexus.mac-mini-worker, com.nexus.orchestrator, com.nexus.ollama — workers

MACHINE BOUNDARY (STRICT):
- Mac Mini: Hermes, AI workflows, Telegram, dashboard, research, signal review.
- Oracle VM (nexus-oracle-api, Fastify/TS at api.goclearonline.cc): managed from Windows only.
- Do NOT suggest SSH/deploy/PM2/nginx actions for Oracle from the Mac.

SUPABASE:
- URL: https://ftxbphwlqskimdnqcfxh.supabase.co
- Key tables: research (18+ rows), agents, tv_raw_alerts, tv_normalized_signals,
  market_price_snapshots, signal_enrichment_jobs, signal_delivery_log

STYLE:
- Ray uses Telegram — keep replies tight. Markdown ok (*bold*, `code`, _italic_).
- If the user asks for live state (who's running, what's up), suggest /status /processes
  /research /agents; you don't have direct shell access from this path.
"""


def hermes_chat(question: str) -> str:
    if not HERMES_TOKEN:
        return '⚠️ `HERMES_GATEWAY_TOKEN` not set — cannot reach ChatGPT session.'
    try:
        r = requests.post(
            f'{HERMES_GATEWAY_URL}/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {HERMES_TOKEN}',
                'Content-Type': 'application/json',
            },
            json={
                'model': HERMES_MODEL,
                'messages': [
                    {'role': 'system', 'content': NEXUS_CONTEXT},
                    {'role': 'user',   'content': question},
                ],
            },
            timeout=120,
        )
        if r.status_code != 200:
            return f'⚠️ Hermes {r.status_code}: `{r.text[:300]}`'
        data = r.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f'❌ Hermes error: `{e}`'


def cmd_ask(args: str) -> str:
    q = args.strip()
    if not q:
        return 'Usage: `/ask <question>` — routes through Hermes (ChatGPT session).'
    return hermes_chat(q)


# ── Dashboard command ──────────────────────────────────────────────────────────

DASHBOARD_URL = 'http://localhost:3000'


def cmd_dashboard(_args: str = '') -> str:
    lines = [f'*Nexus AI Dashboard*\n🔗 {DASHBOARD_URL}\n']

    # Pull metrics from /api/metrics
    try:
        r = requests.get(f'{DASHBOARD_URL}/api/metrics', timeout=6)
        if r.status_code == 200:
            m = r.json()
            pnl    = m.get('daily_pnl', 0)
            pnl_s  = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
            lines += [
                '*Trading*',
                f'• P&L today: `{pnl_s}`',
                f'• Active trades: `{m.get("active_trades", "?")}` / 3 max',
                f'• Signals (24h): `{m.get("signals_today", "?")}`',
                f'• Win rate: `{m.get("win_rate", "?")}%`',
                f'• Strategies: `{m.get("strategy_count", "?")}`',
                '',
            ]
        else:
            lines.append(f'⚠️ Metrics unavailable (HTTP {r.status_code})\n')
    except Exception as e:
        lines.append(f'⚠️ Could not reach dashboard: `{e}`\n')

    # Pull service health from /api/mac-mini/status
    try:
        r2 = requests.get(f'{DASHBOARD_URL}/api/mac-mini/status', timeout=8)
        if r2.status_code in (200, 206):
            s = r2.json()
            def yn(v): return '✅' if v else '❌'
            lines += [
                '*Services*',
                f'• Worker online:      {yn(s.get("worker_online"))}',
                f'• Signal router:      {yn(s.get("signal_router_healthy"))}',
                f'• Telegram bridge:    {yn(s.get("telegram_bridge_ready"))}',
                f'• Hermes/assistant: {yn(s.get("local_assistant_ready"))}',
                f'• Research ingestion: {yn(s.get("research_ingestion_ready"))}',
                f'• Pilot ready:        {yn(s.get("pilot_ready"))}',
            ]
            if s.get('last_error'):
                lines.append(f'\n⚠️ Last error: `{s["last_error"][:120]}`')
            if s.get('memory_usage_mb'):
                lines.append(f'• Memory: `{s["memory_usage_mb"]} MB`')
        else:
            lines.append(f'⚠️ Health check unavailable (HTTP {r2.status_code})')
    except Exception as e:
        lines.append(f'⚠️ Health check failed: `{e}`')

    return '\n'.join(lines)


HELP_TEXT = """\
*Hermes Status Bot — Commands*

`/status`    — processes + research pipeline
`/attention` — what needs attention right now
`/processes` — live launchd process check
`/research`  — research pipeline stats
`/agents`    — AI employee roster from Supabase
`/dashboard` — trading metrics + service health + link
`/coord`     — coordination summary
`/activity`  — recent coordination activity
`/tasks`     — pending coordination tasks (default: codex)
`/leadcheck` — run a safe lead check now
`/reputationcheck` — run a safe reputation check now
`/assign`    — assign task, e.g. `/assign codex: review logs`
`/ask <q>`   — ask via ChatGPT (Hermes OAuth)
`/help`      — this message

Natural language:
`status`
`what needs attention`
`show pending tasks`
`run lead check`
`run reputation check`
`show activity`
`coordination summary`
`show tasks for codex`
`assign task to codex: review logs`

_Any other non-slash message gets routed to ChatGPT._
"""

DISPATCH = {
    '/status':    lambda _args: cmd_status(),
    '/attention': cmd_attention,
    '/processes': lambda _args: cmd_processes(),
    '/research':  lambda _args: cmd_research(),
    '/agents':    lambda _args: cmd_agents(),
    '/dashboard': cmd_dashboard,
    '/coord':     cmd_coord,
    '/activity':  cmd_activity,
    '/tasks':     cmd_tasks,
    '/leadcheck': cmd_run_leads,
    '/reputationcheck': cmd_run_reputation,
    '/assign':    cmd_assign,
    '/ask':       cmd_ask,
    '/help':      lambda _args: HELP_TEXT,
}


def handle_coordination_text(text: str) -> str | None:
    raw = text.strip()
    normalized = raw.lower().strip()

    if normalized in {'show activity', 'activity'}:
        return cmd_activity('8')

    if normalized in {'status', 'ops snapshot', 'give me an ops snapshot', 'summarize system health'}:
        return cmd_status()

    if normalized in {'what needs attention', 'needs attention', 'attention'}:
        return cmd_attention()

    if normalized in {'coordination summary', 'show coordination summary', 'summary'}:
        return cmd_coord()

    if normalized.startswith('show tasks for '):
        agent = raw.split('for ', 1)[1].strip()
        return cmd_tasks(agent)

    if normalized in {'show pending tasks', 'show tasks', 'pending tasks'}:
        return cmd_tasks('hermes')

    if normalized in {'run lead check', 'lead check'}:
        return cmd_run_leads()

    if normalized in {'run reputation check', 'reputation check'}:
        return cmd_run_reputation()

    if normalized.startswith('assign task to '):
        payload = raw[len('assign task to '):].strip()
        return cmd_assign(payload)

    if normalized in {'coord help', 'coordination help'}:
        return HELP_TEXT

    return None


def handle(text: str):
    text = text.strip()
    if text.startswith('/'):
        head, _, rest = text.partition(' ')
        cmd = head.lower()
        handler = DISPATCH.get(cmd)
        if handler:
            try:
                reply = handler(rest)
            except Exception as e:
                reply = f'❌ Error running `{cmd}`: {e}'
        else:
            reply = f'Unknown command: `{cmd}`\nSend /help for available commands.'
    else:
        reply = handle_coordination_text(text) or hermes_chat(text)
    send(reply)


# ── Offset persistence (for --once mode) ───────────────────────────────────────

def _load_offset() -> int:
    try:
        with open(OFFSET_FILE, 'r') as f:
            return int(f.read().strip() or '0')
    except Exception:
        return 0

def _save_offset(offset: int) -> None:
    try:
        with open(OFFSET_FILE, 'w') as f:
            f.write(str(offset))
    except Exception as e:
        log.warning(f'Could not save offset: {e}')

# ── Main poll loop ─────────────────────────────────────────────────────────────

def main():
    if not HERMES_TOKEN:
        print('ERROR: HERMES_BOT_TOKEN not set in .env', flush=True)
        sys.exit(1)
    if not CHAT_ID:
        print('ERROR: TELEGRAM_CHAT_ID not set in .env', flush=True)
        sys.exit(1)

    once = '--once' in sys.argv

    if once:
        offset = _load_offset()
        try:
            updates = get_updates(offset)
            for u in updates:
                offset = u['update_id'] + 1
                msg = u.get('message') or u.get('edited_message')
                if not msg:
                    continue
                if str(msg.get('chat', {}).get('id')) != str(CHAT_ID):
                    continue
                text = msg.get('text', '')
                if not text:
                    continue
                log.info(f'Message: {text.strip()[:80]}')
                handle(text)
        except Exception as e:
            log.error(f'Poll error: {e}')
        finally:
            _save_offset(offset)
        return

    log.info(f'Hermes status bot starting (chat_id={CHAT_ID})')
    send('*Hermes online* 🟢\nSend /help for available commands.')

    offset = _load_offset()
    while True:
        try:
            updates = get_updates(offset)
            for u in updates:
                offset = u['update_id'] + 1
                msg = u.get('message') or u.get('edited_message')
                if not msg:
                    continue
                if str(msg.get('chat', {}).get('id')) != str(CHAT_ID):
                    continue
                text = msg.get('text', '')
                if not text:
                    continue
                log.info(f'Message: {text.strip()[:80]}')
                handle(text)
            _save_offset(offset)
        except KeyboardInterrupt:
            log.info('Stopped.')
            break
        except Exception as e:
            log.error(f'Poll loop error: {e}')

        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
