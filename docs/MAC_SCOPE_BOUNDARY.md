# Mac Mini Scope Boundary

## Machine Roles

### Mac Mini — LOCAL AI OPERATIONS ONLY
This machine runs the Nexus AI workforce, research pipeline, and local decision-support workflows.

**Allowed on this machine:**
- OpenClaw gateway (port 18789) — AI reasoning engine
- AI employee identities and agent workflows
- Telegram bot alerts and monitoring
- Local Flask dashboard (port 3000) and Control Center (port 4000)
- Research pipeline: YouTube → transcripts → OpenClaw summaries → Supabase
- Signal review workflow: read tv_normalized_signals from Supabase, review proposals
- Risk office workflow: apply risk rules locally, send Telegram risk alerts
- Supabase read/write helpers (anon key for reads, service_role for writes)
- launchd automation for local services
- Local docs and scripts for the above

**NOT allowed on this machine:**
- Oracle VM deployment scripts
- SSH setup targeting Oracle VM
- GitHub SSH setup for remote deployment
- PM2 configuration for Oracle
- Nginx / Certbot / Oracle service management
- Tarballs or rsync bundles for Oracle
- Any file that assumes this Mac Mini SSHes to or deploys to the Oracle VM

---

### Oracle VM — API/BACKEND ONLY
Runs the public-facing intake API (`api.goclearonline.cc`).

- Repo: `nexus-oracle-api` (TypeScript / Fastify)
- Managed from: **Windows machine** (where dev/deploy work happens)
- Deployed via: Git clone on the Oracle VM, PM2, nginx reverse proxy
- This Mac Mini never touches the Oracle VM directly

---

### Windows Machine — REPO + DEV + DEPLOY
- Git repository management for `nexus-oracle-api`
- SSH access to Oracle VM
- PM2 deployments to Oracle VM
- Nginx / Certbot management on Oracle VM
- TradingView webhook configuration

---

## Data Flow Summary

```
TradingView alert
      │
      ▼
Oracle VM (api.goclearonline.cc)        ← Windows manages this
  nexus-oracle-api (Fastify)
      │ writes
      ▼
Supabase (shared data layer)
      │ reads
      ▼
Mac Mini (this machine)                 ← Ray manages this
  OpenClaw + AI workflows
  Signal review → Risk office → Telegram alerts
```

---

## Rule of Thumb

If a task involves `ssh oracle`, `pm2`, `nginx`, `certbot`, `scp`, `rsync` to the Oracle VM,
or deploying TypeScript/Node to a remote server — **it belongs on the Windows machine, not here.**
