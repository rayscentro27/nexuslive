#!/bin/bash
# ============================================================
# Nexus AI — Full Status: Employees + Processes + Research
# Usage: bash scripts/ai_status.sh
# ============================================================

set -a; source "$(dirname "$0")/../.env" 2>/dev/null; set +a

SUPABASE_REST_BASE="${SUPABASE_URL%/}/rest/v1"
NOW=$(date '+%Y-%m-%d %H:%M:%S %Z')

divider() { printf '%.0s─' {1..70}; echo; }
header()  { echo; divider; printf "  %s\n" "$1"; divider; }

echo
echo "  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗"
echo "  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝"
echo "  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗"
echo "  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║"
echo "  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║"
echo "  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
echo "  AI Workforce & Process Monitor"
echo "  $NOW"

# ── 1. AI EMPLOYEES ─────────────────────────────────────────
header "🤖  AI EMPLOYEES"
python3 - <<'PYEOF'
import os, json, urllib.request

KEY  = os.environ.get('SUPABASE_KEY','')
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
BASE = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ''

def fetch(path):
    if not BASE or not KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY missing")
    req = urllib.request.Request(
        f"{BASE}/{path}",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

try:
    agents = fetch("agents?select=name,role,division,status&order=division.asc,name.asc")
    scorecards = {r['agent_id']: r for r in fetch("v_agent_metrics?select=*")}

    divs = {}
    for a in agents:
        div = a.get('division') or 'Other'
        divs.setdefault(div, []).append(a)

    status_icon = {'active': '🟢', 'testing': '🟡', 'inactive': '🔴', 'idle': '⚪'}

    for div, members in sorted(divs.items()):
        print(f"\n  [{div}]")
        for a in members:
            icon = status_icon.get(a['status'], '⚪')
            print(f"    {icon}  {a['name']:<35} {a['role']}")

    active  = sum(1 for a in agents if a['status'] == 'active')
    testing = sum(1 for a in agents if a['status'] == 'testing')
    print(f"\n  Total: {len(agents)} agents  |  Active: {active}  |  Testing: {testing}")
except Exception as e:
    if "404" in str(e):
        print("  ℹ️  Agent directory tables are not present on this Supabase project.")
    else:
        print(f"  ⚠️  Could not fetch agents: {e}")
PYEOF

# ── 2. LIVE PROCESSES ────────────────────────────────────────
header "⚙️   LIVE PROCESSES"
python3 - <<'PYEOF'
import os, subprocess, urllib.request
import json
from datetime import datetime, timezone

def llm_base_url():
    return (
        os.environ.get("NEXUS_LLM_BASE_URL")
        or os.environ.get("OPENROUTER_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or ""
    ).rstrip("/")

def llm_models_endpoint():
    base = llm_base_url()
    if not base:
        return None
    if base.endswith("/v1") or base.endswith("/api/v1"):
        return f"{base}/models"
    return f"{base}/v1/models"

services = [
    ("ai.hermes.gateway",                 "Hermes Gateway",         None,  None, "logs/hermes-status.log"),
    ("com.nexus.orchestrator",            "Orchestrator",           None,  None, "logs/nexus-orchestrator.log"),
    ("com.nexus.mac-mini-worker",         "Mac Mini Worker",        None,  None, None),
    ("com.nexus.coordination-worker",     "Coordination Worker",    None,  None, "logs/coordination_worker.log"),
    ("com.nexus.research-worker",         "Research Worker",        None,  None, "logs/nexus-research-worker.log"),
    ("com.nexus.ops-control-worker",      "Ops Control Worker",     None,  None, "logs/ops-control-worker.log"),
    ("com.nexus.opportunity-worker",      "Opportunity Worker",     None,  None, "logs/opportunity-worker.log"),
    ("com.nexus.grant-worker",            "Grant Worker",           None,  None, "logs/grant-worker.log"),
    ("com.nexus.research-orchestrator-transcript", "Transcript Orchestrator", None, None, "logs/research-orchestrator-transcript.log"),
    ("com.nexus.research-orchestrator-grants-browser", "Grants Browser Orchestrator", None, None, "logs/research-orchestrator-grants-browser.log"),
    ("com.nexus.signal-router",           "Signal Router",          8000,  "http://127.0.0.1:8000/health", None),
    ("com.nexus.signal-review",           "Signal Review Poller",   None,  None, "logs/signal_review.log"),
    ("com.nexus.trading-engine",          "Trading Engine",         5000,  "http://127.0.0.1:5000/health", None),
    ("com.raymonddavis.nexus.telegram",   "Telegram Monitor",       None,  None, None),
    ("com.raymonddavis.nexus.dashboard",  "Dashboard",              3000,  "http://127.0.0.1:3000/api/metrics", None),
    ("com.raymonddavis.nexus.scheduler",  "Scheduler",              None,  None, None),
    ("com.nexus.strategy-lab",            "Strategy Lab",           None,  None, None),
]

if llm_models_endpoint():
    services.insert(1, ("", "Configured LLM API", None, llm_models_endpoint(), None))

raw = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
launchd = {}
for line in raw.splitlines():
    parts = line.split('\t')
    if len(parts) == 3:
        pid, exit_code, label = parts
        launchd[label.strip()] = {"pid": pid.strip(), "exit": exit_code.strip()}

def launchctl_details(label):
    raw = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
        capture_output=True, text=True
    ).stdout
    return raw or ""

def check_http(url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=4) as r:
            return True, r.status
    except urllib.error.HTTPError as e:
        # A models endpoint returning auth-required still proves the gateway is reachable.
        return e.code in (200, 401), e.code
    except Exception:
        return False, None

def recent_degraded_hits(path):
    if not path or not os.path.exists(path):
        return 0
    try:
        with open(path, 'r', errors='ignore') as f:
            lines = f.readlines()[-120:]
    except Exception:
        return 0
    patterns = (
        'degraded',
        'rate_limited',
        'rate limit',
        'transient',
        'heartbeat_degraded',
        'fetch_degraded',
        'poll_degraded',
        'claim_degraded',
        'complete_degraded',
        'tick_degraded',
    )
    hits = 0
    for line in lines:
        text = line.lower()
        if any(pattern in text for pattern in patterns):
            hits += 1
    return hits

def table_exists(table):
    base = os.environ.get('SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('SUPABASE_KEY', '')
    if not base or not key:
        return None
    try:
        req = urllib.request.Request(
            f"{base}/rest/v1/{table}?select=*&limit=1",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=4) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return None
    except Exception:
        return None

strategy_lab_schema = {
    "strategy_scores": table_exists("strategy_scores"),
    "hermes_review_queue": table_exists("hermes_review_queue"),
    "demo_accounts": table_exists("demo_accounts"),
}

def fetch_json(path):
    base = os.environ.get('SUPABASE_URL', '').rstrip('/')
    key = os.environ.get('SUPABASE_KEY', '')
    if not base or not key:
        return None
    try:
        req = urllib.request.Request(
            f"{base}/rest/v1/{path}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.loads(r.read())
    except Exception:
        return None

def parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:
        return None

strategy_lab_queue = fetch_json(
    "hermes_review_queue?select=status,last_error,processed_at&order=processed_at.desc.nullslast,created_at.desc&limit=8"
) or []
strategy_lab_reviews = fetch_json(
    "hermes_reviews?select=created_by,created_at&order=created_at.desc&limit=8"
) or []

recent_rate_limits = 0
for row in strategy_lab_queue:
    err = (row.get('last_error') or '').lower()
    ts = parse_ts(row.get('processed_at'))
    if 'rate_limited' in err and ts and (datetime.now(timezone.utc) - ts).total_seconds() < 3600:
        recent_rate_limits += 1

recent_ai_reviews = 0
recent_fallback_reviews = 0
for row in strategy_lab_reviews:
    ts = parse_ts(row.get('created_at'))
    if not ts or (datetime.now(timezone.utc) - ts).total_seconds() >= 21600:
        continue
    if row.get('created_by') == 'hermes_review_worker':
        recent_ai_reviews += 1
    elif row.get('created_by') == 'hermes_review_fallback':
        recent_fallback_reviews += 1

print()
for service in services:
    label, name, port, endpoint, log_path = service
    row = launchd.get(label, {"pid": "-", "exit": "-"})
    pid = row["pid"]
    running = pid not in ('-', '') if label else False
    details_raw = launchctl_details(label) if label and not running else ""
    scheduled = (not running) and ("run interval =" in details_raw or "RunAtLoad = false" in details_raw)
    degraded_hits = recent_degraded_hits(log_path)
    healthy = None
    code = None
    if endpoint:
        healthy, code = check_http(endpoint)
    if running:
        if healthy is False:
            icon = '🟡'
        elif degraded_hits:
            icon = '🟡'
        else:
            icon = '✅'
    elif scheduled and row["exit"] == "0":
        icon = '🟡' if degraded_hits else '🕒'
    elif endpoint and healthy:
        icon = '✅'
    elif endpoint and healthy is False:
        icon = '🟡'
    else:
        icon = '❌'
    port_str = f":{port}" if port else "  "
    pid_str  = f"PID {pid}" if running else (f"scheduled | last exit {row['exit']}" if scheduled else f"exit {row['exit']}")
    if not label and endpoint:
        pid_str = "remote api"
    detail = pid_str
    if endpoint:
        detail += f" | http {code if code is not None else 'down'}"
    if degraded_hits:
        detail += f" | degraded recently: {degraded_hits}"

    if label == "com.nexus.strategy-lab":
        missing = [name for name, present in strategy_lab_schema.items() if present is False]
        if missing:
            detail += f" | schema missing: {','.join(missing)}"
        elif recent_ai_reviews:
            detail += f" | reviews ok: {recent_ai_reviews} ai"
            if recent_fallback_reviews:
                detail += f", {recent_fallback_reviews} fallback"
            if recent_rate_limits:
                detail += f" | rate-limited recently: {recent_rate_limits}"
        elif recent_fallback_reviews:
            detail += f" | fallback reviews: {recent_fallback_reviews}"
            if recent_rate_limits:
                detail += f" | rate-limited recently: {recent_rate_limits}"
        elif recent_rate_limits:
            detail += f" | degraded: recent rate limits {recent_rate_limits}"

    print(f"  {icon}  {name:<28} {port_str:<6}  {detail}")
PYEOF

# ── 3. WORKER HEARTBEATS ─────────────────────────────────────
header "💓  WORKER HEARTBEATS"
python3 - <<'PYEOF'
import os, json, urllib.request
from datetime import datetime, timezone

KEY  = os.environ.get('SUPABASE_KEY','')
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
BASE = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ''

MANAGED_WORKERS = {
    "nexus-orchestrator-1": "core",
    "nexus-research-worker": "core",
    "coordination_worker": "scheduled",
    "grant-worker": "scheduled",
    "opportunity-worker": "scheduled",
    "ops-control-worker": "scheduled",
    "research-orchestrator-transcript": "scheduled",
    "research-orchestrator-grants-browser": "scheduled",
}

try:
    if not BASE or not KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY missing")
    req = urllib.request.Request(
        f"{BASE}/worker_heartbeats?select=worker_id,worker_type,status,in_flight_jobs,last_heartbeat_at&order=last_heartbeat_at.desc&limit=8",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        rows = json.loads(r.read())

    now = datetime.now(timezone.utc)
    print()
    for r in rows:
        ts = r.get('last_heartbeat_at') or r.get('last_seen_at','')
        worker_id = r.get('worker_id', '')
        worker_class = MANAGED_WORKERS.get(worker_id, 'external')
        try:
            dt  = datetime.fromisoformat(ts.replace('Z','+00:00'))
            age = int((now - dt).total_seconds() / 60)
            if worker_class == 'external':
                if age < 60:
                    ago, icon = f"{age}m ago", "⚪"
                else:
                    ago, icon = f"{age//60}h ago", "⚪"
            else:
                if   age < 2:    ago, icon = "live",       "🟢"
                elif age < 60:   ago, icon = f"{age}m ago", "🟡"
                else:            ago, icon = f"{age//60}h ago","🔴"
        except:
            ago, icon = "?", "⚪"

        jobs = r.get('in_flight_jobs', 0) or 0
        suffix = ""
        if worker_class == 'scheduled':
            suffix = " | interval worker"
        elif worker_class == 'external':
            suffix = " | external/unmanaged heartbeat"
        print(f"  {icon}  {r['worker_type']:<28} {ago:<12}  jobs in flight: {jobs}{suffix}")
except Exception as e:
    print(f"  ⚠️  {e}")
PYEOF

# ── 4. RESEARCH PIPELINE ─────────────────────────────────────
header "🧠  RESEARCH PIPELINE"
python3 - <<'PYEOF'
import os, json, urllib.request
from datetime import datetime, timezone

KEY  = os.environ.get('SUPABASE_KEY','')
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
BASE = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ''
RES  = os.path.expanduser("~/nexus-ai/research-engine")

# Local counts
for label, path, ext in [
    ("Channels   ", f"{RES}/channels/trading_channels.json", None),
    ("Transcripts", f"{RES}/transcripts", ".vtt"),
    ("Summaries  ", f"{RES}/summaries",   ".summary"),
    ("Strategies ", f"{RES}/strategies",  ".summary"),
]:
    if ext is None:
        try:
            with open(path) as f:
                n = len(json.load(f).get('channels', []))
            print(f"  📁  {label}: {n} configured")
        except: print(f"  📁  {label}: ?")
    else:
        try:
            n = len([x for x in os.listdir(path) if x.endswith(ext)])
            print(f"  📄  {label}: {n} files")
        except: print(f"  📄  {label}: ?")

# Supabase research rows
try:
    if not BASE or not KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY missing")
    req = urllib.request.Request(
        f"{BASE}/research?select=id,created_at&order=created_at.desc&limit=1",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        rows = json.loads(r.read())

    req2 = urllib.request.Request(
        f"{BASE}/research?select=id",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}", "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"}
    )
    with urllib.request.urlopen(req2, timeout=10) as r:
        total = r.headers.get('Content-Range','?/?').split('/')[-1]

    latest = rows[0]['created_at'][:10] if rows else 'never'
    print(f"  ☁️   Supabase research: {total} rows  |  latest: {latest}")
except Exception as e:
    print(f"  ☁️   Supabase research: error ({e})")
PYEOF

# ── 5. RECENT AGENT RUNS ─────────────────────────────────────
header "📋  RECENT AGENT RUNS"
python3 - <<'PYEOF'
import os, json, urllib.request

KEY  = os.environ.get('SUPABASE_KEY','')
SUPABASE_URL = os.environ.get('SUPABASE_URL', '').rstrip('/')
BASE = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ''

try:
    if not BASE or not KEY:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY missing")
    req = urllib.request.Request(
        f"{BASE}/agent_run_summaries?select=agent_name,run_status,headline,created_at&order=created_at.desc&limit=6",
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        rows = json.loads(r.read())

    icons = {'completed':'✅','failed':'❌','running':'🔄','error':'🔴'}
    print()
    for r in rows:
        icon     = icons.get(r['run_status'], '⚪')
        headline = (r['headline'] or '')[:55]
        date     = r['created_at'][:10]
        print(f"  {icon}  {r['agent_name']:<28} {date}  {headline}")
    if not rows:
        print("  No recent runs found.")
except Exception as e:
    if "404" in str(e):
        print("  ℹ️  agent_run_summaries is not present on this Supabase project.")
    else:
        print(f"  ⚠️  {e}")
PYEOF

echo
divider
echo "  Run 'bash scripts/ai_status.sh' any time to refresh."
divider
echo
