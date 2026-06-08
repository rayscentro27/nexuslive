#!/usr/bin/env python3
"""
nexus_system_map_scan.py — Phase 1 internal system inventory for Hermes task routing.

Builds a read-only map of:
  - git repos (path, remote, branch, commit, dirty, language, purpose, risk)
  - running processes / services (pid, port, status, owner repo, restart cmd, safety)
  - installed CLIs (version, path, category, cost/network risk, safe tasks)
  - AI providers / models (access method, local/cloud, health, cost, env-var NAMES only)
  - core data flows (input -> worker -> tables/files -> output, status, gaps)

SAFETY CONTRACT (hard rules — do not change without explicit approval):
  * READ-ONLY by default. Writes to Supabase ONLY with --apply.
  * Never restarts, kills, or installs anything.
  * Never prints secret VALUES — only reports env-var NAMES as present/missing.
  * Never runs trading / publishing / outreach / ad / deploy commands.
  * No destructive filesystem operations.

Usage:
  python3 scripts/nexus_system_map_scan.py --section all --dry-run
  python3 scripts/nexus_system_map_scan.py --section clis --dry-run --json
  python3 scripts/nexus_system_map_scan.py --section repos --dry-run
  python3 scripts/nexus_system_map_scan.py --section all --apply     # writes to Supabase

Outputs:
  reports/system_map/nexus_system_map_<timestamp>.md   (always)
  reports/system_map/nexus_system_map_<timestamp>.json (with --json)
  Supabase upserts                                     (with --apply only)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
REPO_ROOT = Path(__file__).resolve().parent.parent  # nexus-ai
REPORT_DIR = REPO_ROOT / "reports" / "system_map"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd, cwd=None, timeout=15):
    """Run a read-only shell command; return stdout (stripped) or '' on failure."""
    try:
        out = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def mask(value: str) -> str:
    """Never reveal a secret. Report only presence."""
    return "<set>" if value else "<missing>"


# ---------------------------------------------------------------------------
# Static knowledge: repo purposes, process safety, flow map
# ---------------------------------------------------------------------------

REPO_PURPOSES = {
    "nexus-ai": ("Nexus core platform: workers, trading-engine, telegram bot, Netlify functions, Supabase migrations", "nexus-core", "active", "secrets-present"),
    "nexuslive": ("Public web app (React/Vite) deployed to Netlify (goclearonline.cc)", "frontend", "active", "low"),
    "nexus-mobile": ("Expo/React Native mobile app", "mobile", "experimental", "low"),
    "nexus-claw3d": ("Claw3D evidence-guard / accountability integration", "intelligence", "active", "low"),
    "nexus-oracle-api": ("Oracle ARM instance API (nexus-llm-worker)", "infra", "active", "low"),
    "mac-mini-worker": ("Distributed worker node (Mac mini)", "worker", "active", "low"),
    "hermes-agent": ("Hermes agent runtime (vendored)", "hermes", "active", "secrets-present"),
    "hermes-office": ("Hermes office/workspace", "hermes", "active", "secrets-present"),
    "workspace": ("OpenClaw workspace (gateway disabled)", "tooling", "legacy", "review"),
}

# Process pattern -> (friendly name, owner repo, purpose, safety, can_restart, approval_required, restart_cmd)
PROCESS_RULES = [
    (r"hermes-gateway-adapter\.js", "hermes-gateway-adapter", "nexus-ai", "OpenAI-compatible bridge to local Hermes", "medium", True, False, "launchctl kickstart -k gui/$(id -u)/ai.hermes.gateway"),
    (r"hermes_cli\.main|/\.local/bin/hermes", "hermes-cli", ".hermes", "Hermes agent runtime (SOUL/USER/MEMORY/skills)", "medium", False, True, "recommend only"),
    (r"telegram_bot\.py", "telegram-bot", "nexus-ai", "Telegram interface to Hermes/Nexus", "medium", True, False, "launchctl kickstart -k gui/$(id -u)/com.raymonddavis.nexus.telegram"),
    (r"cloudflared tunnel", "cloudflared-tunnel", "system", "Cloudflare tunnels (Hermes gateway + trading)", "high", False, True, "recommend only — DNS/tunnel sensitive"),
    (r"ollama serve", "ollama", "system", "Local LLM server (qwen/gemma)", "low", True, False, "launchctl kickstart -k gui/$(id -u)/com.nexus.ollama"),
    (r"nexus_watcher_loop", "watcher-loop", "nexus-ai", "Autonomous watcher loop", "medium", True, False, "launchctl kickstart -k gui/$(id -u)/com.nexus.orchestrator"),
    (r"trading-engine/tournament_service\.py", "trading-tournament", "nexus-ai", "Strategy tournament (paper/demo)", "high", False, True, "recommend only — trading"),
    (r"trading-engine/auto_executor\.py", "trading-auto-executor", "nexus-ai", "Auto executor (DRY_RUN gated)", "high", False, True, "recommend only — trading"),
    (r"operations_center/scheduler\.py", "ops-scheduler", "nexus-ai", "Operations scheduler", "medium", True, False, "launchctl kickstart -k gui/$(id -u)/com.raymonddavis.nexus.scheduler"),
    (r"research_signal_bridge\.py", "research-signal-bridge", "nexus-ai", "Bridges research -> signals", "medium", True, False, "launchctl kickstart -k gui/$(id -u)/com.nexus.research-signal-bridge"),
    (r"nexus-research-worker", "research-worker", "nexus-ai", "Web/YouTube research worker", "medium", True, False, "launchctl kickstart -k gui/$(id -u)/com.nexus.research-worker"),
    (r"nexus-orchestrator", "orchestrator", "nexus-ai", "Service orchestrator", "medium", True, False, "launchctl kickstart -k gui/$(id -u)/com.nexus.orchestrator"),
    (r"signal-router/tradingview_router\.py", "signal-router", "nexus-ai", "TradingView signal router", "high", False, True, "recommend only — trading"),
    (r"signal_poller\.py", "signal-poller", "nexus-ai", "Signal poller (review)", "high", False, True, "recommend only — trading"),
    (r"dashboard\.py", "dashboard", "nexus-ai", "Internal dashboard", "low", True, False, "launchctl kickstart -k gui/$(id -u)/com.raymonddavis.nexus.dashboard"),
    (r"mac-mini-worker\.js", "mac-mini-worker", "mac-mini-worker", "Distributed worker node", "low", True, False, "launchctl kickstart -k gui/$(id -u)/com.nexus.mac-mini-worker"),
]

# CLI categorization: command -> (category, cost_risk, network_risk, can_local, safe_tasks, unsafe_tasks, approval_required)
CLI_RULES = {
    "claude": ("ai-coding", "medium", "high", False, "code edits, refactors, reviews", "unattended deploys", False),
    "codex": ("ai-coding", "medium", "high", False, "code generation, edits", "unattended deploys", False),
    "opencode": ("ai-coding", "medium", "high", True, "code tasks, local agent", "unattended deploys", False),
    "ollama": ("ai-local", "free", "none", True, "local inference, cheap classification", "large-context reasoning", False),
    "node": ("runtime", "free", "none", True, "run JS, build", "n/a", False),
    "npm": ("pkg-manager", "free", "medium", True, "install deps, run scripts", "global installs without review", False),
    "npx": ("pkg-manager", "free", "medium", True, "one-off tools", "arbitrary remote scripts", True),
    "python3": ("runtime", "free", "none", True, "run scripts", "n/a", False),
    "uv": ("pkg-manager", "free", "medium", True, "python envs/installs", "n/a", False),
    "git": ("vcs", "free", "medium", True, "version control", "force-push to main", False),
    "gh": ("vcs", "free", "medium", True, "PRs, issues, releases", "n/a", False),
    "netlify": ("deploy", "free", "high", False, "build, deploy preview", "prod deploy without approval", True),
    "supabase": ("db", "free", "high", False, "migrations, local db", "db reset / prod schema changes", True),
    "cloudflared": ("infra", "free", "high", False, "tunnel status", "DNS/tunnel changes", True),
    "docker": ("container", "free", "medium", True, "build/run containers", "n/a", False),
    "docker-compose": ("container", "free", "medium", True, "multi-container", "n/a", False),
    "yt-dlp": ("media", "free", "high", True, "download transcripts/media", "bulk scraping abuse", False),
    "ffmpeg": ("media", "free", "none", True, "media transcode", "n/a", False),
    "playwright": ("automation", "free", "high", True, "browser automation, scraping", "credentialed actions without approval", True),
    "wrangler": ("deploy", "free", "high", False, "cloudflare workers", "prod deploy without approval", True),
    "vercel": ("deploy", "free", "high", False, "deploy", "prod deploy without approval", True),
    "gemini": ("ai-coding", "medium", "high", False, "code/chat", "unattended deploys", False),
    "aider": ("ai-coding", "medium", "high", False, "code edits", "unattended deploys", False),
    "goose": ("ai-coding", "medium", "high", False, "agentic code", "unattended deploys", False),
    "openclaw": ("ai-coding", "medium", "high", True, "local agent", "unattended deploys", False),
}

CLI_LIST = list(CLI_RULES.keys()) + ["pnpm", "yarn", "pip", "n8n", "railway"]

# AI provider env-var names to probe (NAMES only, never values)
AI_PROVIDER_ENVS = {
    "OpenRouter": ("OPENROUTER_API_KEY", "cloud", "medium", "large", "general reasoning, fallback chain"),
    "Groq": ("GROQ_API_KEY", "cloud", "low", "medium", "fast cheap inference"),
    "Gemini": ("GEMINI_API_KEY", "cloud", "medium", "large", "multimodal, long context"),
    "Cohere": ("COHERE_API_KEY", "cloud", "medium", "medium", "embeddings/rerank"),
    "NVIDIA": ("NVIDIA_API_KEY", "cloud", "medium", "large", "hosted models"),
    "Ollama-local": ("OLLAMA_URL", "local", "free", "small", "cheap local classification"),
}

# Static data-flow map (architectural; not auto-discovered)
DATA_FLOWS = [
    {
        "name": "source_intake",
        "input": "YouTube / email / NotebookLM transcripts",
        "worker": "nexus_source_intake_router.py, youtube-channel-poller, email-pipeline",
        "stores": "transcript_queue, knowledge_items, knowledge_review_queue.json",
        "output": "Nexus OS sources / knowledge graph / content drafts",
        "status": "active (apply requires Ray approval)",
        "gaps": "bridge to nexus_os_sources is semi-manual",
        "owner_repo": "nexus-ai",
        "approval": "apply step requires Ray approval",
    },
    {
        "name": "revenue",
        "input": "Affiliate/content campaigns",
        "worker": "Revenue Hub (useCampaignActions), approval-notify",
        "stores": "nexus_os_revenue_campaigns, owner_approval_queue",
        "output": "manual apply/publish, tracking",
        "status": "active (5 campaigns)",
        "gaps": "no automated tracking of conversions yet",
        "owner_repo": "nexuslive + nexus-ai",
        "approval": "publish/apply requires Ray approval",
    },
    {
        "name": "content",
        "input": "Verified sources",
        "worker": "Content Studio (useContentActions), scoreContentItem",
        "stores": "nexus_os_content_items, nexus_os_content_sources",
        "output": "drafts -> compliance -> approval -> manual publish",
        "status": "active (12 drafts; 2 Business Credit Builder pending review)",
        "gaps": "publish is manual by design",
        "owner_repo": "nexuslive + nexus-ai",
        "approval": "publish requires Ray approval",
    },
    {
        "name": "hermes",
        "input": "User prompt (web/Telegram)",
        "worker": "hermes-chat netlify fn -> hermes-gateway-adapter -> Hermes CLI",
        "stores": "localStorage history, hermes_executive_memory, response reviews",
        "output": "conversational/evidence response",
        "status": "active (gateway healthy, 27 skills, SOUL/USER/MEMORY loaded)",
        "gaps": "system map not yet in evidence builder (this phase)",
        "owner_repo": "nexus-ai + nexuslive",
        "approval": "risky actions gated",
    },
    {
        "name": "trading",
        "input": "Strategies / TradingView signals",
        "worker": "vibe (research), tournament_service, signal-router, auto_executor (DRY_RUN)",
        "stores": "ranked_strategies (43), paper_trade_journal, signal logs",
        "output": "paper/demo only; Trading Ops view",
        "status": "demo-only; OANDA on placeholder key; receiver down by design",
        "gaps": "Vibe not wired to live Nexus flow; OANDA key is placeholder",
        "owner_repo": "nexus-ai",
        "approval": "live trading requires explicit Ray approval (default disabled)",
    },
    {
        "name": "research",
        "input": "Web / YouTube",
        "worker": "nexus-research-worker, research_signal_bridge",
        "stores": "research_artifacts, source_extractions, knowledge_items",
        "output": "bridged into Nexus OS sources/graph",
        "status": "active",
        "gaps": "dry-run recommended before large batches",
        "owner_repo": "nexus-ai",
        "approval": "apply limited batch",
    },
]

# Initial task routing rules (Phase 8)
ROUTING_RULES = [
    {"task_type": "frontend_ui_fix", "preferred_tool": "Claude Code / Codex / OpenCode", "fallback_tool": "opencode", "preferred_repo": "nexuslive", "required_context": "NEXUS_DESIGN.md, component path", "safety_gate": "build+deploy approval", "approval_required": True, "notes": "memoize hooks; verify build before deploy", "active": True},
    {"task_type": "supabase_migration", "preferred_tool": "Claude/Codex", "fallback_tool": "supabase cli", "preferred_repo": "nexus-ai", "required_context": "existing migrations, RLS policy", "safety_gate": "review before --apply", "approval_required": True, "notes": "additive only; no db reset", "active": True},
    {"task_type": "source_intake", "preferred_tool": "nexus_source_intake_router.py", "fallback_tool": "research worker", "preferred_repo": "nexus-ai", "required_context": "transcript queue", "safety_gate": "apply requires approval", "approval_required": True, "notes": "dry-run first", "active": True},
    {"task_type": "content_draft", "preferred_tool": "Content Studio / Hermes recommendation", "fallback_tool": "ollama", "preferred_repo": "nexuslive", "required_context": "verified sources", "safety_gate": "publish requires approval", "approval_required": True, "notes": "disclosure for affiliate; no earnings claims", "active": True},
    {"task_type": "trading_status", "preferred_tool": "trading status audit scripts", "fallback_tool": "Trading Ops view", "preferred_repo": "nexus-ai", "required_context": "ranked_strategies, paper journal", "safety_gate": "no execution", "approval_required": False, "notes": "read-only", "active": True},
    {"task_type": "trading_strategy_backtest", "preferred_tool": "vibe-trading", "fallback_tool": "tournament_service", "preferred_repo": "nexus-ai", "required_context": "strategy text, instrument", "safety_gate": "paper/demo only", "approval_required": False, "notes": "education only", "active": True},
    {"task_type": "live_trading", "preferred_tool": "none", "fallback_tool": "none", "preferred_repo": "nexus-ai", "required_context": "n/a", "safety_gate": "DISABLED", "approval_required": True, "notes": "explicit Ray approval required; default disabled", "active": False},
    {"task_type": "design_polish", "preferred_tool": "Claude Code (NEXUS_DESIGN.md)", "fallback_tool": "codex", "preferred_repo": "nexuslive", "required_context": "design tokens", "safety_gate": "deploy approval", "approval_required": True, "notes": "theme tokens, dark recolor", "active": True},
    {"task_type": "web_research", "preferred_tool": "research worker", "fallback_tool": "playwright", "preferred_repo": "nexus-ai", "required_context": "query", "safety_gate": "dry-run first", "approval_required": False, "notes": "limit batch size", "active": True},
    {"task_type": "youtube_research", "preferred_tool": "source intake router / youtube intelligence worker", "fallback_tool": "yt-dlp", "preferred_repo": "nexus-ai", "required_context": "channel/url", "safety_gate": "apply limited batch", "approval_required": True, "notes": "respect rate limits", "active": True},
    {"task_type": "cheap_classification", "preferred_tool": "ollama (qwen2.5/gemma3)", "fallback_tool": "groq", "preferred_repo": "nexus-ai", "required_context": "short prompt", "safety_gate": "local-only preferred", "approval_required": False, "notes": "cheapest path; keep local", "active": True},
]


# ---------------------------------------------------------------------------
# Section: REPOS
# ---------------------------------------------------------------------------

def detect_language(path: Path) -> tuple[str, str]:
    if (path / "package.json").exists():
        return ("JavaScript/TypeScript", "npm")
    if (path / "pyproject.toml").exists():
        return ("Python", "uv/pip")
    if (path / "requirements.txt").exists():
        return ("Python", "pip")
    if (path / "Cargo.toml").exists():
        return ("Rust", "cargo")
    if (path / "go.mod").exists():
        return ("Go", "go")
    return ("unknown", "unknown")


def scan_repos():
    # (base, maxdepth) — HOME scanned shallow (maxdepth 2) to stay fast; project
    # roots scanned a bit deeper. Avoids the slow full-HOME recursion that times out.
    bases = [
        (HOME, 2),
        (HOME / "Desktop", 3), (HOME / "Documents", 3), (HOME / "Projects", 3),
        (HOME / "AI", 3),
        (HOME / "nexus-ai", 2), (HOME / "nexuslive", 2),
        (HOME / "nexus-mobile", 2), (HOME / "nexus-claw3d", 2),
        (HOME / "nexus-oracle-api", 2), (HOME / "mac-mini-worker", 2),
        (HOME / ".hermes", 3), (HOME / ".openclaw", 3),
    ]
    seen = set()
    repos = []
    for base, depth in bases:
        if not base.exists():
            continue
        try:
            git_dirs = subprocess.run(
                ["find", str(base), "-maxdepth", str(depth), "-name", ".git", "-type", "d"],
                capture_output=True, text=True, timeout=20,
            ).stdout.splitlines()
        except Exception:
            git_dirs = []
        for gd in git_dirs:
            repo_path = str(Path(gd).parent)
            if repo_path in seen:
                continue
            seen.add(repo_path)
            name = Path(repo_path).name
            remote = run(["git", "-C", repo_path, "config", "--get", "remote.origin.url"])
            branch = run(["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"])
            commit = run(["git", "-C", repo_path, "rev-parse", "--short", "HEAD"])
            status = run(["git", "-C", repo_path, "status", "--porcelain"])
            dirty = bool(status)
            untracked = len([l for l in status.splitlines() if l.startswith("??")])
            lang, pm = detect_language(Path(repo_path))
            purpose, module, active_state, risk = REPO_PURPOSES.get(
                name, ("unknown", "unknown", "unknown", "review"))
            # Mask any remote that embeds credentials
            if remote and "@" in remote and "://" in remote:
                remote = re.sub(r"://[^@]+@", "://<redacted>@", remote)
            repos.append({
                "name": name, "path": repo_path, "remote_url": remote,
                "branch": branch, "latest_commit": commit, "dirty": dirty,
                "untracked_count": untracked, "language": lang, "package_manager": pm,
                "purpose": purpose, "module": module, "active_state": active_state,
                "risk_level": risk, "safe_for_hermes": active_state in ("active",) and risk != "secrets-present",
                "scanned_at": now_iso(),
            })
    return repos


# ---------------------------------------------------------------------------
# Section: PROCESSES
# ---------------------------------------------------------------------------

def scan_processes():
    ps = run(["ps", "axo", "pid,command"], timeout=20)
    # Port map from lsof
    port_map = {}
    lsof = run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], timeout=20)
    for line in lsof.splitlines()[1:]:
        cols = line.split()
        if len(cols) >= 9:
            pid = cols[1]
            m = re.search(r":(\d+)$", cols[8])
            if m:
                port_map.setdefault(pid, m.group(1))
    procs = []
    for line in ps.splitlines()[1:]:
        line = line.strip()
        m = re.match(r"(\d+)\s+(.*)", line)
        if not m:
            continue
        pid, cmd = m.group(1), m.group(2)
        for pattern, name, repo, purpose, safety, can_restart, approval, restart_cmd in PROCESS_RULES:
            if re.search(pattern, cmd):
                procs.append({
                    "name": name, "command": cmd[:200], "pid": int(pid),
                    "port": port_map.get(pid), "status": "running",
                    "repo_path": repo, "purpose": purpose, "risk_level": safety,
                    "restart_command": restart_cmd, "can_restart": can_restart,
                    "approval_required": approval, "hermes_can_query": True,
                    "scanned_at": now_iso(),
                })
                break
    # Note known services that are *configured* but may be stopped (from launchctl)
    found_names = {p["name"] for p in procs}
    return procs, found_names


# ---------------------------------------------------------------------------
# Section: CLIs
# ---------------------------------------------------------------------------

def cli_version(cmd, path):
    for flag in ("--version", "-v", "version"):
        out = run([cmd, flag], timeout=8)
        if out:
            return out.splitlines()[0][:80]
    return ""


def scan_clis():
    clis = []
    for cmd in CLI_LIST:
        path = shutil.which(cmd)
        installed = bool(path)
        cat, cost, net, local, safe_t, unsafe_t, approval = CLI_RULES.get(
            cmd, ("misc", "unknown", "unknown", False, "", "", False))
        version = cli_version(cmd, path) if installed else ""
        clis.append({
            "name": cmd, "command": cmd, "version": version, "path": path or "",
            "category": cat, "installed": installed,
            "health_status": "ok" if installed else "missing",
            "cost_risk": cost, "network_risk": net, "can_run_locally": local,
            "safe_tasks": safe_t, "unsafe_tasks": unsafe_t,
            "approval_required": approval, "scanned_at": now_iso(),
        })
    return clis


# ---------------------------------------------------------------------------
# Section: AI PROVIDERS
# ---------------------------------------------------------------------------

def load_env_names():
    """Collect env-var NAMES present in process env + nexus-ai/.env (never values)."""
    names = set(os.environ.keys())
    envf = REPO_ROOT / ".env"
    if envf.exists():
        for line in envf.read_text(errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                names.add(line.split("=", 1)[0].strip())
    return names


def scan_ai():
    names = load_env_names()
    providers = []
    for label, (env_name, loc, cost, ctx, best) in AI_PROVIDER_ENVS.items():
        present = env_name in names
        providers.append({
            "name": label, "access_method": f"env:{env_name}",
            "env_var_present": present, "local_or_cloud": loc,
            "cost_risk": cost, "context_size": ctx, "best_for": best,
            "health_status": "configured" if present else "not_configured",
            "tool_calling": "unknown", "approval_required": cost not in ("free",),
            "scanned_at": now_iso(),
        })
    # Ollama local models
    ollama_models = []
    if shutil.which("ollama"):
        out = run(["ollama", "list"], timeout=10)
        for line in out.splitlines()[1:]:
            if line.strip():
                ollama_models.append(line.split()[0])
    # Hermes config presence (names only)
    hermes_files = {f: (HOME / ".hermes" / f).exists()
                    for f in ("SOUL.md", "USER.md", "MEMORY.md", "config.yaml")}
    skills_dir = HOME / ".hermes" / "skills"
    hermes_skills = len(list(skills_dir.iterdir())) if skills_dir.exists() else 0
    return providers, ollama_models, hermes_files, hermes_skills


# ---------------------------------------------------------------------------
# Supabase write (only with --apply)
# ---------------------------------------------------------------------------

def supabase_upsert(table, rows, on_conflict=None):
    """Upsert rows via Supabase REST. Returns (ok, msg). Requires service creds in env/.env."""
    try:
        import requests  # noqa
    except Exception:
        return False, "requests not available"
    url = os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    # Fallback to .env
    if not (url and key):
        envf = REPO_ROOT / ".env"
        if envf.exists():
            for line in envf.read_text(errors="ignore").splitlines():
                if line.startswith("SUPABASE_URL=") and not url:
                    url = line.split("=", 1)[1].strip().strip('"')
                if line.startswith("SUPABASE_SERVICE_ROLE_KEY=") and not key:
                    key = line.split("=", 1)[1].strip().strip('"')
    if not (url and key):
        return False, "SUPABASE_URL / service key not found (skipping write)"
    import requests
    endpoint = f"{url}/rest/v1/{table}"
    params = {}
    if on_conflict:
        params["on_conflict"] = on_conflict
    headers = {
        "apikey": key, "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    try:
        r = requests.post(endpoint, params=params, headers=headers,
                          data=json.dumps(rows), timeout=30)
        if r.status_code in (200, 201, 204):
            return True, f"{len(rows)} rows -> {table}"
        return False, f"{table}: HTTP {r.status_code} {r.text[:120]}"
    except Exception as e:
        return False, f"{table}: {str(e)[:120]}"


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_markdown(data, ts):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    md = REPORT_DIR / f"nexus_system_map_{ts}.md"
    L = []
    L.append(f"# Nexus System Map — {ts}\n")
    L.append("_Read-only inventory for Hermes task routing. Secrets masked._\n")

    if "repos" in data:
        L.append("\n## Repositories\n")
        for r in data["repos"]:
            L.append(f"- **{r['name']}** (`{r['active_state']}`, risk={r['risk_level']}) — "
                     f"{r['purpose']}\n  - branch `{r['branch']}` @ `{r['latest_commit']}` "
                     f"{'(dirty)' if r['dirty'] else '(clean)'}, {r['untracked_count']} untracked, "
                     f"{r['language']}/{r['package_manager']}")

    if "processes" in data:
        L.append("\n## Running Processes / Services\n")
        for p in data["processes"]:
            port = f", port {p['port']}" if p.get("port") else ""
            L.append(f"- **{p['name']}** (pid {p['pid']}{port}) — {p['purpose']} "
                     f"[safety={p['risk_level']}, restart={'auto-ok' if p['can_restart'] else 'recommend-only'}, "
                     f"approval={'yes' if p['approval_required'] else 'no'}]")

    if "clis" in data:
        L.append("\n## CLIs\n")
        for c in data["clis"]:
            mark = "✓" if c["installed"] else "✗"
            L.append(f"- {mark} **{c['name']}** ({c['category']}) "
                     f"{c['version']} — cost={c['cost_risk']}, net={c['network_risk']}, "
                     f"local={c['can_run_locally']}, approval={'yes' if c['approval_required'] else 'no'}")

    if "ai" in data:
        L.append("\n## AI Providers / Models\n")
        for p in data["ai"]["providers"]:
            L.append(f"- **{p['name']}** ({p['local_or_cloud']}) — {p['health_status']}, "
                     f"cost={p['cost_risk']}, ctx={p['context_size']}, best_for={p['best_for']}")
        L.append(f"- **Ollama local models**: {', '.join(data['ai']['ollama_models']) or 'none'}")
        hf = data["ai"]["hermes_files"]
        L.append(f"- **Hermes files**: " +
                 ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in hf.items()) +
                 f", skills={data['ai']['hermes_skills']}")

    if "flows" in data:
        L.append("\n## Data Flows\n")
        for f in data["flows"]:
            L.append(f"### {f['name']}\n- input: {f['input']}\n- worker: {f['worker']}\n"
                     f"- stores: {f['stores']}\n- output: {f['output']}\n"
                     f"- status: {f['status']}\n- gaps: {f['gaps']}\n- approval: {f['approval']}")

    if "routing" in data:
        L.append("\n## Task Routing Rules\n")
        for r in data["routing"]:
            L.append(f"- **{r['task_type']}** -> {r['preferred_tool']} "
                     f"(fallback {r['fallback_tool']}, repo {r['preferred_repo']}, "
                     f"approval={'yes' if r['approval_required'] else 'no'}, gate={r['safety_gate']})")

    md.write_text("\n".join(L) + "\n")
    return md


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Nexus system map scanner (read-only by default)")
    ap.add_argument("--section", default="all",
                    choices=["repos", "processes", "clis", "ai", "flows", "all"])
    ap.add_argument("--apply", action="store_true", help="Write to Supabase (default: dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="Force dry-run (default)")
    ap.add_argument("--json", action="store_true", help="Also write JSON report")
    args = ap.parse_args()

    apply = args.apply and not args.dry_run
    sect = args.section
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = {}

    if sect in ("repos", "all"):
        data["repos"] = scan_repos()
    if sect in ("processes", "all"):
        procs, _ = scan_processes()
        data["processes"] = procs
    if sect in ("clis", "all"):
        data["clis"] = scan_clis()
    if sect in ("ai", "all"):
        providers, models, hfiles, hskills = scan_ai()
        data["ai"] = {"providers": providers, "ollama_models": models,
                      "hermes_files": hfiles, "hermes_skills": hskills}
    if sect in ("flows", "all"):
        data["flows"] = DATA_FLOWS
        data["routing"] = ROUTING_RULES

    md = write_markdown(data, ts)

    if args.json:
        jp = REPORT_DIR / f"nexus_system_map_{ts}.json"
        jp.write_text(json.dumps(data, indent=2, default=str))
        print(f"JSON: {jp}")

    print(f"Markdown report: {md}")
    print(f"Mode: {'APPLY (writing to Supabase)' if apply else 'DRY-RUN (no writes)'}")

    # Summary counts
    if "repos" in data:
        print(f"  repos: {len(data['repos'])}")
    if "processes" in data:
        print(f"  processes: {len(data['processes'])}")
    if "clis" in data:
        inst = sum(1 for c in data['clis'] if c['installed'])
        print(f"  clis: {inst}/{len(data['clis'])} installed")
    if "ai" in data:
        conf = sum(1 for p in data['ai']['providers'] if p['health_status'] == 'configured')
        print(f"  ai providers configured: {conf}/{len(data['ai']['providers'])}, "
              f"ollama models: {len(data['ai']['ollama_models'])}")

    if apply:
        print("\n-- Supabase writes --")
        writes = []
        if "repos" in data:
            # Map scanner fields -> nexus_system_repos schema (dirty bool -> status text).
            repo_rows = [{
                "name": r["name"], "path": r["path"], "remote_url": r["remote_url"],
                "branch": r["branch"], "latest_commit": r["latest_commit"],
                "status": "dirty" if r["dirty"] else "clean",
                "purpose": r["purpose"], "module": r["module"],
                "active_state": r["active_state"], "risk_level": r["risk_level"],
                "safe_for_hermes": r["safe_for_hermes"], "language": r["language"],
                "package_manager": r["package_manager"],
                "untracked_count": r["untracked_count"], "scanned_at": r["scanned_at"],
            } for r in data["repos"]]
            writes.append(("nexus_system_repos", repo_rows, "path"))
        if "processes" in data:
            # Dedupe by unique name within the batch (PostgREST rejects duplicate
            # conflict keys in one upsert). Prefer the row that has a port.
            by_name = {}
            for p in data["processes"]:
                prow = {
                    "name": p["name"], "command": p["command"], "pid": p["pid"],
                    "port": p["port"], "status": p["status"], "repo_path": p["repo_path"],
                    "purpose": p["purpose"], "restart_command": p["restart_command"],
                    "can_restart": p["can_restart"], "approval_required": p["approval_required"],
                    "risk_level": p["risk_level"], "hermes_can_query": p["hermes_can_query"],
                    "scanned_at": p["scanned_at"],
                }
                if p["name"] not in by_name or (p.get("port") and not by_name[p["name"]].get("port")):
                    by_name[p["name"]] = prow
            writes.append(("nexus_system_processes", list(by_name.values()), "name"))
        if "clis" in data:
            # Reuse nexus_cli_tools (additive columns) — map minimal fields
            cli_rows = [{
                "cli_key": c["name"], "command_name": c["command"],
                "description": f"{c['category']} CLI",
                "supported_task_types": [c["safe_tasks"]] if c["safe_tasks"] else [],
                "risk_level": c["network_risk"], "requires_approval": c["approval_required"],
                "is_enabled": c["installed"],
            } for c in data["clis"] if c["installed"]]
            writes.append(("nexus_cli_tools", cli_rows, "cli_key"))
        if "routing" in data:
            writes.append(("nexus_task_routing_rules", data["routing"], "task_type"))
        for table, rows, conflict in writes:
            ok, msg = supabase_upsert(table, rows, on_conflict=conflict)
            print(f"  [{'OK' if ok else 'SKIP'}] {msg}")
    else:
        print("\n(no Supabase writes — pass --apply after Ray approves)")


if __name__ == "__main__":
    main()
