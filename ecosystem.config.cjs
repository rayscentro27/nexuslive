/**
 * Nexus AI Wealth — PM2 Ecosystem Configuration
 *
 * Services managed by PM2:
 *   nexus-watchers   — Persistent intelligence watcher loop (10-min cycle)
 *   nexus-executor   — Daily task orchestration loop (5-min cycle)
 *
 * Services managed by launchd (NOT started from this config):
 *   Hermes gateway   — com.nexus.hermes (port 8642)
 *   OpenClaw         — port 18789
 *   Telegram bot     — com.raymonddavis.nexus.telegram
 *                      (telegram_bot.py has a duplicate-run guard; start via launchd only)
 *
 * Safety: NEXUS_DRY_RUN=true always | LIVE_TRADING=false
 *
 * Usage:
 *   pm2 start ecosystem.config.js         # start all services
 *   pm2 restart ecosystem.config.js       # restart all
 *   pm2 stop ecosystem.config.js          # stop all
 *   pm2 logs                              # tail all logs
 *   pm2 monit                             # live dashboard
 *   pm2 save                              # persist for startup
 */

const NEXUS_ROOT = "/Users/raymonddavis/nexus-ai";
const PYTHON     = "python3";
const LOG_DIR    = `${NEXUS_ROOT}/logs`;

// Shared env loaded for all processes — process.env overrides .env values
const SHARED_ENV = {
  NEXUS_DRY_RUN: "true",
  LIVE_TRADING: "false",
  REAL_MONEY_TRADING: "false",
  TRADING_LIVE_EXECUTION_ENABLED: "false",
  PYTHONDONTWRITEBYTECODE: "1",
  PYTHONUNBUFFERED: "1",
  PYTHONPATH: NEXUS_ROOT,
};

module.exports = {
  apps: [

    // ── Claw3D Hermes Gateway Adapter ────────────────────────────────────────
    // Bridges Claw3D WebSocket protocol → Hermes HTTP on port 8642
    {
      name: "nexus-claw3d-adapter",
      script: "node",
      args: "server/hermes-gateway-adapter.js",
      cwd: "/Users/raymonddavis/nexus-claw3d",
      interpreter: "none",
      env: {
        HERMES_API_URL: "http://localhost:8642",
        HERMES_API_KEY: "a29d9fd7b6c34b91a5e80f1f20260422c1a87e1139bb4f58",
        HERMES_ADAPTER_PORT: "18790",
        HERMES_AGENT_NAME: "Hermes",
      },

      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
      restart_delay: 5000,
      watch: false,

      out_file: `${LOG_DIR}/pm2-claw3d-adapter.out.log`,
      error_file: `${LOG_DIR}/pm2-claw3d-adapter.err.log`,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      merge_logs: true,
      max_memory_restart: "256M",
      instances: 1,
      exec_mode: "fork",
    },

    // ── Claw3D 3D Office ─────────────────────────────────────────────────────
    {
      name: "nexus-claw3d",
      script: "node",
      args: "server/index.js",
      cwd: "/Users/raymonddavis/nexus-claw3d",
      interpreter: "none",
      env: { NODE_ENV: "production", PORT: "3001" },

      autorestart: true,
      max_restarts: 10,
      min_uptime: "15s",
      restart_delay: 5000,
      watch: false,

      out_file: `${LOG_DIR}/pm2-claw3d.out.log`,
      error_file: `${LOG_DIR}/pm2-claw3d.err.log`,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      merge_logs: true,
      max_memory_restart: "512M",
      instances: 1,
      exec_mode: "fork",
    },

    // ── Watcher Loop ─────────────────────────────────────────────────────────
    {
      name: "nexus-watchers",
      script: PYTHON,
      args: "-m lib.nexus_watcher_loop",
      cwd: NEXUS_ROOT,
      interpreter: "none",
      env: SHARED_ENV,

      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      restart_delay: 10000,
      watch: false,

      out_file: `${LOG_DIR}/pm2-watchers.out.log`,
      error_file: `${LOG_DIR}/pm2-watchers.err.log`,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      merge_logs: true,

      max_memory_restart: "256M",
      instances: 1,
      exec_mode: "fork",
    },

    // ── Executor Loop ─────────────────────────────────────────────────────────
    {
      name: "nexus-executor",
      script: PYTHON,
      args: "-m lib.executor_loop",
      cwd: NEXUS_ROOT,
      interpreter: "none",
      env: SHARED_ENV,

      autorestart: true,
      max_restarts: 15,
      min_uptime: "10s",
      restart_delay: 15000,
      watch: false,

      out_file: `${LOG_DIR}/pm2-executor.out.log`,
      error_file: `${LOG_DIR}/pm2-executor.err.log`,
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      merge_logs: true,

      max_memory_restart: "256M",
      instances: 1,
      exec_mode: "fork",
    },

  ],
};
