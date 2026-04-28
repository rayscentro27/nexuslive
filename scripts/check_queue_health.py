#!/usr/bin/env python3
"""
Nexus Queue Health Check — detailed Supabase queue snapshot.
Usage: python3 ~/nexus-ai/scripts/check_queue_health.py
"""

import os
import sys
import json
import urllib.request
from datetime import datetime, timezone

# Load .env
_env = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env):
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())

SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

if not SUPABASE_URL or not SUPABASE_KEY:
    print('❌ SUPABASE_URL or SUPABASE_KEY not set')
    sys.exit(1)


def sb_get(path):
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={'apikey': SUPABASE_KEY, 'Authorization': f'Bearer {SUPABASE_KEY}'}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def fmt_time(iso):
    if not iso:
        return 'never'
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        delta = datetime.now(timezone.utc) - dt
        secs = int(delta.total_seconds())
        if secs < 60:   return f"{secs}s ago"
        if secs < 3600: return f"{secs//60}m ago"
        return f"{secs//3600}h ago"
    except Exception:
        return iso[:19]


now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')

print()
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print('  NEXUS QUEUE HEALTH')
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

# ── Queue depth by status ─────────────────────────────────────────────────────
print('\n▸ QUEUE DEPTH')
total = 0
for status in ['pending', 'leased', 'retry_wait', 'completed', 'failed']:
    rows = sb_get(f"job_queue?status=eq.{status}&select=id")
    n = len(rows)
    total += n if status not in ('completed',) else 0
    flag = '⚠️ ' if (status == 'failed' and n > 0) else '  '
    print(f"  {flag}{status:14s}: {n}")

# ── Priority breakdown (non-completed) ───────────────────────────────────────
print('\n▸ PENDING BY PRIORITY')
for priority, label in [(10, 'critical'), (5, 'normal'), (1, 'low'), (None, 'unset')]:
    if priority is not None:
        rows = sb_get(f"job_queue?status=in.(pending,retry_wait)&priority=eq.{priority}&select=id")
    else:
        rows = sb_get(f"job_queue?status=in.(pending,retry_wait)&priority=is.null&select=id")
    if rows:
        print(f"  {label:10s} (priority={priority or 'null'}): {len(rows)}")

# ── Stale leases ─────────────────────────────────────────────────────────────
print('\n▸ STALE LEASES')
stale = sb_get(f"job_queue?status=eq.leased&lease_expires_at=lt.{now_iso}&select=id,job_type,leased_at,worker_id")
if stale:
    print(f"  ⚠️  {len(stale)} stale lease(s):")
    for s in stale:
        print(f"     {s['job_type']} | leased {fmt_time(s['leased_at'])} | worker: {s.get('worker_id','?')}")
else:
    print('  ✅ No stale leases')

# ── Recent failures ──────────────────────────────────────────────────────────
print('\n▸ RECENT FAILURES (last 5)')
failed = sb_get("job_queue?status=eq.failed&order=updated_at.desc&limit=5&select=id,job_type,last_error,updated_at")
if failed:
    for f in failed:
        print(f"  ❌ {f['job_type']:30s} | {fmt_time(f['updated_at'])} | {str(f.get('last_error',''))[:80]}")
else:
    print('  ✅ No failed jobs')

# ── Recent completions ───────────────────────────────────────────────────────
print('\n▸ RECENT COMPLETIONS (last 5)')
done = sb_get("job_queue?status=eq.completed&order=completed_at.desc&limit=5&select=id,job_type,completed_at")
if done:
    for d in done:
        print(f"  ✅ {d['job_type']:30s} | {fmt_time(d['completed_at'])}")
else:
    print('  (none)')

# ── Worker heartbeats ────────────────────────────────────────────────────────
print('\n▸ WORKER HEARTBEATS')
hbs = sb_get("worker_heartbeats?select=worker_id,worker_type,status,in_flight_jobs,last_heartbeat_at,pid")
if hbs:
    for h in hbs:
        age = fmt_time(h.get('last_heartbeat_at'))
        secs_ago = 0
        try:
            dt = datetime.fromisoformat(h['last_heartbeat_at'].replace('Z', '+00:00'))
            secs_ago = int((datetime.now(timezone.utc) - dt).total_seconds())
        except Exception:
            pass
        flag = '⚠️ ' if secs_ago > 120 else '✅ '
        print(f"  {flag}{h['worker_id']:40s} | {h['status']:12s} | {h['in_flight_jobs']} jobs | seen {age} | PID {h.get('pid','?')}")
else:
    print('  ⚠️  No heartbeat rows found')

print()
print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
print()
