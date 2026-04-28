#!/usr/bin/env python3
"""
Nexus AI Control Center — Bloomberg-style master terminal.
Port: 4000 (localhost only)

Panels:
  AI Agents | Research Feed | Strategy Engine | Signals
  Leads     | Reputation    | Marketing       | System Health
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, render_template_string

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [CC] %(levelname)s %(message)s")
logger = logging.getLogger("ControlCenter")

app = Flask(__name__)

# ─────────────────────────────────────────────
# Data API routes
# ─────────────────────────────────────────────

def _safe(fn):
    try:
        return fn()
    except Exception as e:
        return {"error": str(e)}


@app.route("/api/health")
def api_health():
    from operations_center.operations_engine import get_system_health
    return jsonify(_safe(get_system_health))


@app.route("/api/research")
def api_research():
    from operations_center.operations_engine import check_research_brain
    from research.ai_research_brain import get_latest_strategies, get_status
    return jsonify({
        "brain": _safe(check_research_brain),
        "status": _safe(get_status),
        "latest_strategies": _safe(get_latest_strategies),
    })


@app.route("/api/signals")
def api_signals():
    from operations_center.hedge_fund_panel import get_panel_data
    return jsonify(_safe(get_panel_data))


@app.route("/api/leads")
def api_leads():
    from lead_intelligence.lead_scoring_engine import get_lead_summary
    return jsonify(_safe(get_lead_summary))


@app.route("/api/marketing")
def api_marketing():
    from marketing_automation.marketing_engine import get_marketing_summary, get_performance_metrics
    return jsonify({
        "summary": _safe(get_marketing_summary),
        "performance": _safe(get_performance_metrics),
    })


@app.route("/api/reputation")
def api_reputation():
    from reputation_engine.review_analyzer import get_reputation_summary
    return jsonify(_safe(get_reputation_summary))


@app.route("/api/scheduler")
def api_scheduler():
    from operations_center.scheduler import get_schedule_status
    return jsonify(_safe(get_schedule_status))


@app.route("/api/all")
def api_all():
    from operations_center.operations_engine import get_full_ops_report
    return jsonify(_safe(get_full_ops_report))


# ─────────────────────────────────────────────
# Bloomberg-style HTML terminal
# ─────────────────────────────────────────────

TERMINAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEXUS AI CONTROL CENTER</title>
<style>
  :root {
    --bg:       #0a0c0f;
    --panel:    #0f1318;
    --border:   #1e2530;
    --accent:   #f0a500;
    --green:    #00d4aa;
    --red:      #ff3b5c;
    --blue:     #2196f3;
    --purple:   #9c27b0;
    --text:     #c8d0db;
    --dim:      #5a6475;
    --header:   #141820;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  html,body { height:100%; background:var(--bg); color:var(--text);
              font-family:'Courier New',Courier,monospace; font-size:12px; }

  /* ── TOP BAR ── */
  #topbar {
    background:var(--header);
    border-bottom:2px solid var(--accent);
    padding:6px 16px;
    display:flex; align-items:center; justify-content:space-between;
  }
  #topbar .logo { color:var(--accent); font-size:15px; font-weight:bold; letter-spacing:3px; }
  #topbar .meta { color:var(--dim); font-size:11px; }
  #clock { color:var(--green); font-size:13px; font-weight:bold; }

  /* ── TAB NAV ── */
  #tabnav {
    background:var(--header);
    border-bottom:1px solid var(--border);
    display:flex; gap:0; overflow-x:auto;
  }
  .tab {
    padding:7px 18px; cursor:pointer; border-right:1px solid var(--border);
    color:var(--dim); font-size:11px; letter-spacing:1px; white-space:nowrap;
    transition:all .2s;
  }
  .tab:hover { background:#1a2030; color:var(--text); }
  .tab.active { color:var(--accent); background:var(--panel);
                border-bottom:2px solid var(--accent); }

  /* ── MAIN GRID ── */
  #workspace { display:flex; flex-direction:column; height:calc(100vh - 72px); }
  .page { display:none; padding:10px; gap:10px; height:100%; overflow:auto; }
  .page.active { display:grid; }
  .page.single { grid-template-columns:1fr; }
  .page.two    { grid-template-columns:1fr 1fr; }
  .page.three  { grid-template-columns:1fr 1fr 1fr; }
  .page.quad   { grid-template-columns:1fr 1fr; grid-template-rows:1fr 1fr; }

  /* ── PANELS ── */
  .panel {
    background:var(--panel); border:1px solid var(--border);
    border-radius:4px; overflow:hidden; display:flex; flex-direction:column;
    min-height:200px;
  }
  .panel-header {
    background:var(--header); padding:6px 10px;
    border-bottom:1px solid var(--border);
    display:flex; align-items:center; justify-content:space-between;
  }
  .panel-title { color:var(--accent); font-size:11px; font-weight:bold; letter-spacing:1px; }
  .panel-badge { font-size:10px; padding:1px 6px; border-radius:2px; }
  .badge-green { background:#003d2e; color:var(--green); }
  .badge-red   { background:#2d0f17; color:var(--red); }
  .badge-blue  { background:#0a1929; color:var(--blue); }
  .badge-amber { background:#1a1200; color:var(--accent); }
  .panel-body { padding:8px 10px; flex:1; overflow-y:auto; }

  /* ── METRICS ── */
  .metric-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(110px,1fr)); gap:6px; }
  .metric {
    background:#141820; border:1px solid var(--border);
    border-radius:3px; padding:8px; text-align:center;
  }
  .metric .val { font-size:22px; font-weight:bold; }
  .metric .lbl { color:var(--dim); font-size:10px; margin-top:2px; }
  .green { color:var(--green); }
  .red   { color:var(--red); }
  .amber { color:var(--accent); }
  .blue  { color:var(--blue); }
  .purple{ color:var(--purple); }

  /* ── STATUS DOTS ── */
  .dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:5px; }
  .dot-green  { background:var(--green); box-shadow:0 0 6px var(--green); }
  .dot-red    { background:var(--red);   box-shadow:0 0 6px var(--red); }
  .dot-amber  { background:var(--accent);box-shadow:0 0 6px var(--accent); }

  /* ── TABLES ── */
  .data-table { width:100%; border-collapse:collapse; }
  .data-table th { color:var(--dim); font-size:10px; text-align:left;
                   padding:4px 6px; border-bottom:1px solid var(--border); }
  .data-table td { padding:5px 6px; border-bottom:1px solid #151b24;
                   font-size:11px; vertical-align:top; }
  .data-table tr:hover td { background:#141c28; }

  /* ── FEED ── */
  .feed-item { padding:6px 0; border-bottom:1px solid #151b24; }
  .feed-item:last-child { border:none; }
  .feed-time { color:var(--dim); font-size:10px; }
  .feed-text { color:var(--text); margin-top:2px; line-height:1.5; }

  /* ── SENTIMENT BAR ── */
  .sent-bar { display:flex; height:14px; border-radius:3px; overflow:hidden; margin:6px 0; }
  .sent-bull { background:var(--green); }
  .sent-bear { background:var(--red); }
  .sent-neu  { background:var(--dim); }

  /* ── REFRESH BTN ── */
  .refresh-btn {
    background:none; border:1px solid var(--border); color:var(--dim);
    padding:2px 8px; border-radius:3px; cursor:pointer; font-family:inherit;
    font-size:10px; transition:all .2s;
  }
  .refresh-btn:hover { border-color:var(--accent); color:var(--accent); }

  /* ── FOOTER ── */
  #footer {
    position:fixed; bottom:0; left:0; right:0;
    background:var(--header); border-top:1px solid var(--border);
    padding:3px 14px; display:flex; gap:20px; align-items:center;
  }
  .footer-item { font-size:10px; color:var(--dim); }
  .footer-item span { color:var(--text); }

  /* SCROLLBAR */
  ::-webkit-scrollbar { width:4px; height:4px; }
  ::-webkit-scrollbar-track { background:var(--bg); }
  ::-webkit-scrollbar-thumb { background:var(--border); border-radius:2px; }
</style>
</head>
<body>

<!-- TOP BAR -->
<div id="topbar">
  <div class="logo">⬡ NEXUS AI CONTROL CENTER</div>
  <div class="meta">v2.0 | localhost | DRY_RUN=TRUE</div>
  <div id="clock">--:--:--</div>
</div>

<!-- TAB NAV -->
<div id="tabnav">
  <div class="tab active" onclick="showPage('overview')">OVERVIEW</div>
  <div class="tab" onclick="showPage('research')">RESEARCH BRAIN</div>
  <div class="tab" onclick="showPage('signals')">HEDGE FUND</div>
  <div class="tab" onclick="showPage('leads')">LEAD INTEL</div>
  <div class="tab" onclick="showPage('marketing')">MARKETING</div>
  <div class="tab" onclick="showPage('reputation')">REPUTATION</div>
  <div class="tab" onclick="showPage('health')">SYSTEM HEALTH</div>
  <div class="tab" onclick="showPage('scheduler')">SCHEDULER</div>
</div>

<!-- WORKSPACE -->
<div id="workspace">

  <!-- ── OVERVIEW ── -->
  <div id="page-overview" class="page quad active">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">⬡ AI AGENT STATUS</span>
        <button class="refresh-btn" onclick="loadAll()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="agents-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">📊 MARKET SENTIMENT</span>
        <span class="panel-badge badge-amber" id="sentiment-badge">—</span>
      </div>
      <div class="panel-body" id="sentiment-panel">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">🧠 RESEARCH FEED</span>
        <span class="panel-badge badge-blue" id="research-count">—</span>
      </div>
      <div class="panel-body" id="research-feed">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">🔔 ALERTS</span>
        <span class="panel-badge badge-red" id="alert-count">—</span>
      </div>
      <div class="panel-body" id="alerts-panel">Loading...</div>
    </div>
  </div>

  <!-- ── RESEARCH ── -->
  <div id="page-research" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🧠 RESEARCH PIPELINE STATUS</span></div>
      <div class="panel-body" id="research-status">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">📄 LATEST STRATEGY SUMMARIES</span></div>
      <div class="panel-body" id="strategy-feed">Loading...</div>
    </div>
  </div>

  <!-- ── SIGNALS / HEDGE FUND ── -->
  <div id="page-signals" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">📈 SIGNAL CANDIDATES</span>
        <span class="panel-badge badge-green">DRY RUN ✓</span>
      </div>
      <div class="panel-body" id="signals-table">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🌡 SENTIMENT ANALYSIS</span></div>
      <div class="panel-body" id="sentiment-detail">Loading...</div>
    </div>
  </div>

  <!-- ── LEADS ── -->
  <div id="page-leads" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">🔥 LEAD INTELLIGENCE</span></div>
      <div class="panel-body" id="leads-summary">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">⭐ HIGH-VALUE LEADS</span></div>
      <div class="panel-body" id="leads-table">Loading...</div>
    </div>
  </div>

  <!-- ── MARKETING ── -->
  <div id="page-marketing" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">📣 MARKETING PERFORMANCE</span></div>
      <div class="panel-body" id="marketing-summary">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">⭐ TOP TESTIMONIALS</span></div>
      <div class="panel-body" id="testimonials-feed">Loading...</div>
    </div>
  </div>

  <!-- ── REPUTATION ── -->
  <div id="page-reputation" class="page two" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">⭐ REPUTATION SCORE</span></div>
      <div class="panel-body" id="reputation-summary">Loading...</div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">⚠️ FLAGGED REVIEWS</span></div>
      <div class="panel-body" id="flagged-reviews">Loading...</div>
    </div>
  </div>

  <!-- ── SYSTEM HEALTH ── -->
  <div id="page-health" class="page single" style="display:none">
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">💻 SYSTEM HEALTH</span>
        <button class="refresh-btn" onclick="loadHealth()">↺ REFRESH</button>
      </div>
      <div class="panel-body" id="health-panel">Loading...</div>
    </div>
  </div>

  <!-- ── SCHEDULER ── -->
  <div id="page-scheduler" class="page single" style="display:none">
    <div class="panel">
      <div class="panel-header"><span class="panel-title">⏱ OPERATIONS SCHEDULER</span></div>
      <div class="panel-body" id="scheduler-panel">Loading...</div>
    </div>
  </div>

</div><!-- /workspace -->

<!-- FOOTER -->
<div id="footer">
  <div class="footer-item">STATUS: <span id="footer-status" class="green">ONLINE</span></div>
  <div class="footer-item">LAST UPDATE: <span id="footer-updated">—</span></div>
  <div class="footer-item">RESEARCH: <span id="footer-research">—</span></div>
  <div class="footer-item">SIGNALS: <span id="footer-signals">—</span></div>
  <div class="footer-item">LEADS: <span id="footer-leads">—</span></div>
  <div class="footer-item" style="margin-left:auto">⬡ NEXUS AI — DATA PRODUCER | NO BROKER EXECUTION</div>
</div>

<script>
// ── Clock ──
function tick() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'}) + '  ' +
    now.toTimeString().slice(0,8);
}
tick(); setInterval(tick, 1000);

// ── Tab routing ──
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.style.display='none');
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('page-'+name).style.display='grid';
  event.target.classList.add('active');
  loadPage(name);
}

function dot(up) {
  return `<span class="dot ${up?'dot-green':'dot-red'}"></span>`;
}
function badge(val, cls='green') {
  return `<span style="color:var(--${cls});font-weight:bold">${val}</span>`;
}
function ts(iso) {
  if(!iso) return '—';
  try { return new Date(iso).toLocaleString(); } catch(e) { return iso; }
}
function pct_bar(bull, bear, neu) {
  return `<div class="sent-bar">
    <div class="sent-bull" style="width:${bull}%"></div>
    <div class="sent-bear" style="width:${bear}%"></div>
    <div class="sent-neu"  style="width:${neu}%"></div>
  </div>
  <div style="display:flex;gap:14px;font-size:10px;color:var(--dim);margin-top:2px">
    <span><span class="green">▲</span> Bull ${bull}%</span>
    <span><span class="red">▼</span> Bear ${bear}%</span>
    <span><span style="color:var(--dim)">◆</span> Neu ${neu}%</span>
  </div>`;
}

// ── Fetch helpers ──
async function get(url) {
  const r = await fetch(url);
  return r.json();
}

// ── Loaders ──
async function loadHealth() {
  try {
    const d = await get('/api/health');
    const svcs = d.services || {};
    let rows = Object.entries(svcs).map(([k,v]) =>
      `<tr>
        <td>${dot(v.running)} ${v.name||k}</td>
        <td>${v.port ? ':'+v.port : '—'}</td>
        <td>${v.running ? badge('ONLINE','green') : badge('OFFLINE','red')}</td>
        <td style="color:var(--dim)">${v.pid||'—'}</td>
      </tr>`
    ).join('');
    document.getElementById('health-panel').innerHTML = `
      <table class="data-table">
        <thead><tr><th>SERVICE</th><th>PORT</th><th>STATUS</th><th>PID</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div style="margin-top:14px">
        <div style="color:var(--accent);font-size:10px;margin-bottom:6px">RESEARCH BRAIN</div>
        <table class="data-table">
          <tr><td>Status</td><td>${badge(d.research?.status||'?','amber')}</td></tr>
          <tr><td>Transcripts</td><td>${d.research?.transcripts||0}</td></tr>
          <tr><td>Summaries</td><td>${d.research?.summaries||0}</td></tr>
          <tr><td>Strategies</td><td>${d.research?.strategies||0}</td></tr>
          <tr><td>Last Run</td><td>${ts(d.research?.last_run)}</td></tr>
        </table>
      </div>`;

    // Footer
    const online = Object.values(svcs).filter(v=>v.running).length;
    document.getElementById('footer-status').textContent = online+'/'+Object.keys(svcs).length+' UP';
    document.getElementById('footer-updated').textContent = new Date().toTimeString().slice(0,8);
    document.getElementById('footer-research').textContent =
      (d.research?.strategies||0)+' strategies';
  } catch(e) {
    document.getElementById('health-panel').innerHTML = `<div class="red">Error: ${e}</div>`;
  }
}

async function loadAgents() {
  try {
    const d = await get('/api/health');
    const svcs = d.services||{};
    let html = '<div class="metric-grid">';
    const order = ['gateway','dashboard','signal_router','telegram','control_center'];
    order.forEach(k => {
      const v = svcs[k]||{};
      html += `<div class="metric">
        <div class="val ${v.running?'green':'red'}">${v.running?'●':'○'}</div>
        <div class="lbl">${(v.name||k).toUpperCase()}</div>
      </div>`;
    });
    html += '</div>';
    document.getElementById('agents-panel').innerHTML = html;
  } catch(e) {}
}

async function loadSentiment() {
  try {
    const d = await get('/api/signals');
    const s = d.market_sentiment||{};
    const dom = (s.dominant||'neutral').toUpperCase();
    document.getElementById('sentiment-badge').textContent = dom;
    document.getElementById('sentiment-panel').innerHTML = `
      <div class="metric-grid">
        <div class="metric"><div class="val ${s.dominant==='bullish'?'green':s.dominant==='bearish'?'red':'amber'}">${dom}</div><div class="lbl">MARKET BIAS</div></div>
        <div class="metric"><div class="val green">${s.bullish_pct||0}%</div><div class="lbl">BULLISH</div></div>
        <div class="metric"><div class="val red">${s.bearish_pct||0}%</div><div class="lbl">BEARISH</div></div>
        <div class="metric"><div class="val amber">${s.files_analyzed||0}</div><div class="lbl">ANALYZED</div></div>
      </div>
      ${pct_bar(s.bullish_pct||0, s.bearish_pct||0, s.neutral_pct||0)}
      <div style="margin-top:8px;color:var(--dim);font-size:10px">Updated: ${ts(s.updated)}</div>`;
    document.getElementById('footer-signals').textContent = d.strategy_count+' strategies';
  } catch(e) {}
}

async function loadResearchFeed() {
  try {
    const d = await get('/api/research');
    const strats = d.latest_strategies||[];
    document.getElementById('research-count').textContent = strats.length+' recent';
    let html = strats.map(s =>
      `<div class="feed-item">
        <div class="feed-time">${ts(s.modified)}</div>
        <div class="feed-text" style="color:var(--accent)">${s.title}</div>
        <div class="feed-text" style="font-size:11px">${s.content.slice(0,300)}...</div>
      </div>`
    ).join('') || '<div style="color:var(--dim)">No strategies yet. Run research pipeline.</div>';
    document.getElementById('research-feed').innerHTML = html;
  } catch(e) {}
}

async function loadAlerts() {
  try {
    const [leads, rep, mkt] = await Promise.all([
      get('/api/leads'), get('/api/reputation'), get('/api/marketing')
    ]);
    const items = [];
    (leads.recent_high_value||[]).forEach(l =>
      items.push({icon:'🔥',text:`High-Value Lead: ${l.name||'?'} (score ${l.score})`,cls:'amber'})
    );
    (rep.recent_flagged||[]).forEach(r =>
      items.push({icon:'⚠️',text:`Negative Review: ${(r.text||'').slice(0,80)}`,cls:'red'})
    );
    (mkt.summary?.negative_alerts||[]).forEach(m =>
      items.push({icon:'📣',text:`Negative Mention on ${m.platform}: ${(m.text||'').slice(0,60)}`,cls:'red'})
    );
    document.getElementById('alert-count').textContent = items.length+' alerts';
    document.getElementById('alerts-panel').innerHTML = items.length
      ? items.map(i=>`<div class="feed-item"><div class="feed-text ${i.cls}">${i.icon} ${i.text}</div></div>`).join('')
      : '<div style="color:var(--green)">✓ No active alerts</div>';
  } catch(e) {}
}

async function loadResearchPage() {
  try {
    const d = await get('/api/research');
    const st = d.status||{};
    document.getElementById('research-status').innerHTML = `
      <table class="data-table">
        <tr><td>Pipeline Status</td><td>${badge(st.pipeline_status||'idle','amber')}</td></tr>
        <tr><td>Transcripts</td><td>${badge(st.transcript_count||0,'blue')}</td></tr>
        <tr><td>Summaries</td><td>${badge(st.summary_count||0,'blue')}</td></tr>
        <tr><td>Strategies</td><td>${badge(st.strategy_count||0,'green')}</td></tr>
        <tr><td>Last Run</td><td>${ts(st.last_run)}</td></tr>
        <tr><td>Last Error</td><td style="color:var(--red)">${st.last_error||'None'}</td></tr>
      </table>`;
    const strats = d.latest_strategies||[];
    document.getElementById('strategy-feed').innerHTML = strats.map(s =>
      `<div class="feed-item">
        <div class="feed-time">${ts(s.modified)}</div>
        <div style="color:var(--accent);margin:3px 0">${s.title}</div>
        <div style="font-size:11px;white-space:pre-wrap;line-height:1.6">${s.content.slice(0,600)}...</div>
      </div>`
    ).join('') || '<div style="color:var(--dim)">No strategies yet.</div>';
  } catch(e) {}
}

async function loadSignalsPage() {
  try {
    const d = await get('/api/signals');
    const sigs = d.recent_signals||[];
    document.getElementById('signals-table').innerHTML = sigs.length ? `
      <table class="data-table">
        <thead><tr><th>ID</th><th>SOURCE</th><th>SENTIMENT</th><th>CONF</th><th>DRY RUN</th></tr></thead>
        <tbody>${sigs.slice(-15).reverse().map(s=>`<tr>
          <td style="color:var(--dim)">${s.id}</td>
          <td style="font-size:10px">${(s.source||'').slice(0,40)}</td>
          <td class="${s.sentiment==='bullish'?'green':s.sentiment==='bearish'?'red':'amber'}">${(s.sentiment||'').toUpperCase()}</td>
          <td>${s.confidence||0}%</td>
          <td class="green">✓</td>
        </tr>`).join('')}</tbody>
      </table>` : '<div style="color:var(--dim)">No signals yet.</div>';
    const s = d.market_sentiment||{};
    document.getElementById('sentiment-detail').innerHTML = `
      <div class="metric-grid" style="margin-bottom:12px">
        <div class="metric"><div class="val ${s.dominant==='bullish'?'green':s.dominant==='bearish'?'red':'amber'}">${(s.dominant||'?').toUpperCase()}</div><div class="lbl">BIAS</div></div>
        <div class="metric"><div class="val green">${s.bullish_pct||0}%</div><div class="lbl">BULL</div></div>
        <div class="metric"><div class="val red">${s.bearish_pct||0}%</div><div class="lbl">BEAR</div></div>
        <div class="metric"><div class="val amber">${s.neutral_pct||0}%</div><div class="lbl">NEUTRAL</div></div>
      </div>
      ${pct_bar(s.bullish_pct||0, s.bearish_pct||0, s.neutral_pct||0)}
      <div style="margin-top:14px;color:var(--amber);font-size:10px">⚠ SIGNAL ONLY — NO BROKER EXECUTION — DRY RUN ACTIVE</div>`;
  } catch(e) {}
}

async function loadLeadsPage() {
  try {
    const d = await get('/api/leads');
    document.getElementById('leads-summary').innerHTML = `
      <div class="metric-grid">
        <div class="metric"><div class="val blue">${d.total||0}</div><div class="lbl">TOTAL LEADS</div></div>
        <div class="metric"><div class="val green">${d.high_value||0}</div><div class="lbl">HIGH VALUE</div></div>
        <div class="metric"><div class="val amber">${d.medium||0}</div><div class="lbl">MEDIUM</div></div>
        <div class="metric"><div class="val dim">${d.low||0}</div><div class="lbl">LOW</div></div>
        <div class="metric"><div class="val purple">${d.avg_score||0}</div><div class="lbl">AVG SCORE</div></div>
      </div>
      ${Object.entries(d.source_distribution||{}).map(([k,v])=>
        `<div style="display:flex;justify-content:space-between;margin:4px 0;font-size:11px">
          <span style="color:var(--dim)">${k}</span><span>${v}</span>
        </div>`
      ).join('')}`;
    const hvl = d.recent_high_value||[];
    document.getElementById('leads-table').innerHTML = hvl.length ?
      `<table class="data-table">
        <thead><tr><th>NAME</th><th>SOURCE</th><th>INTEREST</th><th>SCORE</th></tr></thead>
        <tbody>${hvl.slice().reverse().map(l=>`<tr>
          <td class="amber">${l.name||'?'}</td>
          <td>${l.source||'?'}</td>
          <td style="font-size:10px">${l.interest||'?'}</td>
          <td class="green">${l.score}/100</td>
        </tr>`).join('')}</tbody>
      </table>` : '<div style="color:var(--dim)">No high-value leads yet.</div>';
    document.getElementById('footer-leads').textContent = (d.total||0)+' leads';
  } catch(e) {}
}

async function loadMarketingPage() {
  try {
    const d = await get('/api/marketing');
    const s = d.summary||{};
    const p = d.performance||{};
    document.getElementById('marketing-summary').innerHTML = `
      <div class="metric-grid" style="margin-bottom:10px">
        <div class="metric"><div class="val blue">${s.total_mentions||0}</div><div class="lbl">TOTAL MENTIONS</div></div>
        <div class="metric"><div class="val green">${(s.sentiment||{}).positive||0}</div><div class="lbl">POSITIVE</div></div>
        <div class="metric"><div class="val red">${(s.sentiment||{}).negative||0}</div><div class="lbl">NEGATIVE</div></div>
        <div class="metric"><div class="val">${p.testimonials_total||0}</div><div class="lbl">TESTIMONIALS</div></div>
      </div>
      <div style="color:var(--accent);font-size:10px;margin-bottom:6px">TOP INSIGHTS</div>
      ${(s.top_insights||[]).map(i=>`<div class="feed-item"><div class="feed-text">${i}</div></div>`).join('')
        || '<div style="color:var(--dim)">Add mentions to generate insights.</div>'}`;
    const tst = (s.testimonials||[]);
    document.getElementById('testimonials-feed').innerHTML = tst.length ?
      tst.slice().reverse().map(t =>
        `<div class="feed-item">
          <div class="feed-time">${t.platform||'?'} · ${t.author||'?'}</div>
          <div class="feed-text green">"${(t.text||'').slice(0,200)}"</div>
        </div>`
      ).join('') : '<div style="color:var(--dim)">No testimonials recorded yet.</div>';
  } catch(e) {}
}

async function loadReputationPage() {
  try {
    const d = await get('/api/reputation');
    document.getElementById('reputation-summary').innerHTML = `
      <div class="metric-grid">
        <div class="metric"><div class="val ${d.avg_score>=4?'green':d.avg_score>=3?'amber':'red'}">${d.avg_score||0}</div><div class="lbl">AVG SCORE</div></div>
        <div class="metric"><div class="val blue">${d.total_reviews||0}</div><div class="lbl">REVIEWS</div></div>
        <div class="metric"><div class="val green">${d.positive||0}</div><div class="lbl">POSITIVE</div></div>
        <div class="metric"><div class="val red">${d.negative||0}</div><div class="lbl">NEGATIVE</div></div>
        <div class="metric"><div class="val red">${d.flagged_count||0}</div><div class="lbl">FLAGGED</div></div>
      </div>
      <div style="margin-top:14px;color:var(--accent);font-size:10px">RECENT REVIEWS</div>
      ${(d.recent_reviews||[]).map(r=>
        `<div class="feed-item">
          <div class="feed-time">${r.source||'?'} · ${r.reviewer_name||'?'} · ${r.star_rating||'?'}★</div>
          <div class="feed-text ${r.sentiment==='positive'?'green':r.sentiment==='negative'?'red':''}">${(r.text||'').slice(0,150)}</div>
        </div>`
      ).join('') || '<div style="color:var(--dim)">No reviews yet.</div>'}`;
    const flagged = d.recent_flagged||[];
    document.getElementById('flagged-reviews').innerHTML = flagged.length ?
      flagged.map(r =>
        `<div class="feed-item">
          <div class="feed-time red">⚠️ ${r.source||'?'} — ${r.reviewer_name||'?'}</div>
          <div class="feed-text">${(r.text||'').slice(0,200)}</div>
          <div style="margin-top:6px;color:var(--blue);font-size:11px">SUGGESTED: ${(r.suggested_response||'').slice(0,150)}...</div>
        </div>`
      ).join('') : '<div style="color:var(--green)">✓ No flagged reviews</div>';
  } catch(e) {}
}

async function loadSchedulerPage() {
  try {
    const d = await get('/api/scheduler');
    document.getElementById('scheduler-panel').innerHTML = `
      <table class="data-table">
        <thead><tr><th>TASK</th><th>INTERVAL</th><th>LAST RUN</th><th>NEXT RUN</th></tr></thead>
        <tbody>${Object.entries(d).map(([k,v])=>`<tr>
          <td class="amber">${k.replace(/_/g,' ').toUpperCase()}</td>
          <td>${v.interval_hours}h</td>
          <td style="color:var(--dim)">${ts(v.last_run)}</td>
          <td>${v.next_run==='now (never run)'?badge('PENDING NOW','green'):ts(v.next_run)}</td>
        </tr>`).join('')}</tbody>
      </table>
      <div style="margin-top:14px;color:var(--dim);font-size:11px">
        Start scheduler: <span style="color:var(--accent)">python3 operations_center/scheduler.py</span>
      </div>`;
  } catch(e) {
    document.getElementById('scheduler-panel').innerHTML = `<div style="color:var(--dim)">Scheduler not running.</div>`;
  }
}

// ── Page routing ──
function loadPage(name) {
  const map = {
    overview:   () => { loadAgents(); loadSentiment(); loadResearchFeed(); loadAlerts(); },
    research:   loadResearchPage,
    signals:    loadSignalsPage,
    leads:      loadLeadsPage,
    marketing:  loadMarketingPage,
    reputation: loadReputationPage,
    health:     loadHealth,
    scheduler:  loadSchedulerPage,
  };
  if (map[name]) map[name]();
}

async function loadAll() { loadPage('overview'); }

// ── Auto-refresh every 30s ──
loadAll();
setInterval(loadAll, 30000);
</script>
</body>
</html>"""


@app.route("/api/route-job", methods=["POST"])
def api_route_job():
    """
    Submit a task for CEO auto-routing.

    Body (JSON): {"message": "...", "channel": "admin_portal"}
    Returns: {"event_id": "uuid", "status": "pending"} or {"error": "..."}
    """
    from flask import request as flask_request
    from lib.event_intake import submit_ceo_route_request

    try:
        body    = flask_request.get_json(silent=True) or {}
        message = (body.get("message") or "").strip()
        if not message:
            return jsonify({"error": "message is required"}), 400

        result = submit_ceo_route_request(
            message=message,
            source="admin_portal",
            channel=body.get("channel", "control_center"),
            client_id=body.get("client_id"),
            metadata=body.get("metadata"),
        )
        status_code = 400 if "error" in result else 200
        return jsonify(result), status_code
    except Exception as exc:
        logger.exception("route-job error")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/drafts")
def api_drafts():
    """
    List workflow_outputs rows with status='pending_review' and
    workflow_type='ceo_routed_draft' — drafts waiting for admin approval.

    Query params:
        limit  (int, default 20)
        role   (str, optional — filter by subject_type)
    """
    from flask import request as flask_request
    import urllib.request as _urllib_req

    limit = flask_request.args.get("limit", 20, type=int)
    role  = flask_request.args.get("role", "")

    def _fetch_drafts():
        supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            return {"error": "Supabase not configured"}

        filters = (
            "workflow_outputs"
            "?workflow_type=eq.ceo_routed_draft"
            "&status=eq.pending_review"
            f"&order=created_at.desc"
            f"&limit={limit}"
            "&select=id,subject_type,summary,priority,created_at,raw_output"
        )
        if role:
            filters += f"&subject_type=eq.{role}"

        url = f"{supabase_url}/rest/v1/{filters}"
        headers = {
            "apikey":        supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type":  "application/json",
        }
        req = _urllib_req.Request(url, headers=headers)
        try:
            import json as _json
            with _urllib_req.urlopen(req, timeout=10) as r:
                rows = _json.loads(r.read()) or []
            return {"drafts": rows, "count": len(rows)}
        except Exception as exc:
            return {"error": str(exc), "drafts": []}

    return jsonify(_safe(_fetch_drafts))


@app.route("/")
def index():
    return render_template_string(TERMINAL_HTML)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=4000)
    p.add_argument("--debug", action="store_true")
    args = p.parse_args()
    logger.info(f"🚀 Nexus Control Center starting on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
