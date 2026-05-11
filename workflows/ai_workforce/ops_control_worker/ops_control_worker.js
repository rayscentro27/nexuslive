#!/usr/bin/env node

import "../env.js";
import { execFileSync } from "child_process";
import { existsSync } from "fs";
import { diagnoseWithHermes, proposeActionWithHermes } from "./hermes_ops_adapter.js";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_KEY;
const AUTO_RECOVERY_REQUESTED_BY = "ops-control-worker:auto-recovery";
const AUTO_RECOVERY_HEARTBEAT_STALE_MINUTES = parseInt(
  process.env.AUTO_RECOVERY_HEARTBEAT_STALE_MINUTES ?? "10",
  10,
);
const AUTO_RECOVERY_RESTART_COOLDOWN_MINUTES = parseInt(
  process.env.AUTO_RECOVERY_RESTART_COOLDOWN_MINUTES ?? "30",
  10,
);

const ALLOWED_ACTIONS = new Set([
  "restart_service",
  "pause_worker",
  "resume_worker",
  "update_schedule",
  "set_maintenance_mode",
]);

function nowIso() {
  return new Date().toISOString();
}

function minutesSince(iso) {
  if (!iso) return null;
  const ts = new Date(iso).getTime();
  if (Number.isNaN(ts)) return null;
  return Math.max(0, Math.round((Date.now() - ts) / 60_000));
}

async function supabaseGet(path) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
    },
  });
  if (!res.ok) throw new Error(`Supabase GET ${path}: ${res.status} ${await res.text()}`);
  return res.json();
}

async function supabasePatch(table, values, filters) {
  const filterQuery = new URLSearchParams(filters).toString();
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}?${filterQuery}`, {
    method: "PATCH",
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify(values),
  });
  if (!res.ok) throw new Error(`Supabase PATCH ${table}: ${res.status} ${await res.text()}`);
  return res.json();
}

async function supabaseInsert(table, rows) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
      Prefer: "return=representation",
    },
    body: JSON.stringify(Array.isArray(rows) ? rows : [rows]),
  });
  if (!res.ok) throw new Error(`Supabase INSERT ${table}: ${res.status} ${await res.text()}`);
  return res.json();
}

function tryLaunchctlList() {
  try {
    return execFileSync("launchctl", ["list"], {
      encoding: "utf8",
      timeout: 10_000,
      maxBuffer: 1024 * 1024,
    });
  } catch {
    return "";
  }
}

function launchctlDomainLabel(label) {
  return `gui/${process.getuid()}/${label}`;
}

function resolvePlistPath(label) {
  const path = `/Users/raymonddavis/Library/LaunchAgents/${label}.plist`;
  return existsSync(path) ? path : null;
}

function runLaunchctl(args) {
  return execFileSync("launchctl", args, {
    encoding: "utf8",
    timeout: 20_000,
    maxBuffer: 1024 * 1024,
  });
}

function isLaunchdLoaded(label) {
  const raw = tryLaunchctlList();
  return raw.includes(label);
}

function applyLaunchdAction(action, worker) {
  const label = worker.runtime_label;
  if (!label) {
    return {
      applied_to_launchd: false,
      reason: "worker has no runtime_label",
    };
  }

  const domainLabel = launchctlDomainLabel(label);
  const plistPath = resolvePlistPath(label);
  const loadedBefore = isLaunchdLoaded(label);

  try {
    switch (action.action_type) {
      case "pause_worker": {
        if (loadedBefore) {
          runLaunchctl(["bootout", domainLabel]);
        }
        return {
          applied_to_launchd: true,
          label,
          operation: "bootout",
          loaded_before: loadedBefore,
          loaded_after: isLaunchdLoaded(label),
        };
      }
      case "resume_worker": {
        if (!loadedBefore) {
          if (!plistPath) {
            return {
              applied_to_launchd: false,
              label,
              reason: "missing plist path for bootstrap",
            };
          }
          runLaunchctl(["bootstrap", `gui/${process.getuid()}`, plistPath]);
        }
        runLaunchctl(["kickstart", "-k", domainLabel]);
        return {
          applied_to_launchd: true,
          label,
          operation: loadedBefore ? "kickstart" : "bootstrap+kickstart",
          loaded_before: loadedBefore,
          loaded_after: isLaunchdLoaded(label),
          plist_path: plistPath,
        };
      }
      case "restart_service": {
        if (loadedBefore) {
          runLaunchctl(["bootout", domainLabel]);
        }
        if (!plistPath) {
          return {
            applied_to_launchd: false,
            label,
            reason: "missing plist path for restart bootstrap",
          };
        }
        runLaunchctl(["bootstrap", `gui/${process.getuid()}`, plistPath]);
        runLaunchctl(["kickstart", "-k", domainLabel]);
        return {
          applied_to_launchd: true,
          label,
          operation: "bootout+bootstrap+kickstart",
          loaded_before: loadedBefore,
          loaded_after: isLaunchdLoaded(label),
          plist_path: plistPath,
        };
      }
      default:
        return {
          applied_to_launchd: false,
          label,
          reason: "action is control-plane only",
        };
    }
  } catch (error) {
    return {
      applied_to_launchd: false,
      label,
      error: error?.message ?? String(error),
      loaded_before: loadedBefore,
      loaded_after: isLaunchdLoaded(label),
    };
  }
}

function collectRuntimeLabels(raw, rows) {
  return rows.map((row) => {
    const runtimeLabel = row.runtime_label ?? null;
    const listed = runtimeLabel ? raw.includes(runtimeLabel) : false;
    return {
      worker_id: row.worker_id,
      worker_type: row.worker_type,
      runtime_label: runtimeLabel,
      listed_in_launchctl: listed,
      desired_state: row.desired_state,
      enabled: row.enabled,
      maintenance_mode: row.maintenance_mode,
      schedule_seconds: row.schedule_seconds,
      control_mode: row.control_mode,
      notes: row.notes,
    };
  });
}

function attachHeartbeatState(rows, heartbeats) {
  const byId = new Map(heartbeats.map((hb) => [hb.worker_id, hb]));
  return rows.map((row) => {
    const hb = byId.get(row.worker_id) ?? byId.get(row.worker_id.replace(/^research-orchestrator-/, "")) ?? null;
    return {
      ...row,
      heartbeat_status: hb?.status ?? null,
      last_heartbeat_at: hb?.last_heartbeat_at ?? null,
      heartbeat_metadata: hb?.metadata ?? {},
    };
  });
}

function computeHealth(row) {
  if (row.maintenance_mode) return "maintenance";
  if (row.enabled === false) return "disabled";
  if (row.desired_state === "running" && row.runtime_label && !row.listed_in_launchctl) return "warning";
  if (
    row.desired_state === "running"
    && row.schedule_seconds == null
    && row.last_heartbeat_at
    && minutesSince(row.last_heartbeat_at) > AUTO_RECOVERY_HEARTBEAT_STALE_MINUTES
  ) {
    return "warning";
  }
  if (row.desired_state === "running" && row.heartbeat_status && row.heartbeat_status !== "running" && row.heartbeat_status !== "idle") {
    return "warning";
  }
  return "healthy";
}

export async function collectControlPlaneSnapshot() {
  const [controlRows, heartbeatRows] = await Promise.all([
    supabaseGet("worker_control_plane?select=*&order=worker_id.asc"),
    supabaseGet("worker_heartbeats?select=worker_id,status,last_heartbeat_at,metadata&order=last_heartbeat_at.desc"),
  ]);

  const launchctlRaw = tryLaunchctlList();
  const runtimeRows = collectRuntimeLabels(launchctlRaw, controlRows);
  return attachHeartbeatState(runtimeRows, heartbeatRows).map((row) => ({
    ...row,
    computed_health: computeHealth(row),
  }));
}

function shouldAutoRecover(row) {
  return Boolean(
    row.enabled !== false
    && row.maintenance_mode !== true
    && row.desired_state === "running"
    && row.control_mode === "automatic"
    && row.runtime_label,
  );
}

function buildAutoRecoveryReason(row) {
  if (!row.listed_in_launchctl) {
    return {
      recovery_reason: "runtime_missing",
      detail: "runtime label missing from launchctl",
    };
  }

  const heartbeatAgeMinutes = minutesSince(row.last_heartbeat_at);
  if (
    row.schedule_seconds == null
    && row.last_heartbeat_at
    && heartbeatAgeMinutes != null
    && heartbeatAgeMinutes > AUTO_RECOVERY_HEARTBEAT_STALE_MINUTES
  ) {
    return {
      recovery_reason: "stale_heartbeat",
      detail: `heartbeat stale for ${heartbeatAgeMinutes}m`,
    };
  }

  if (row.heartbeat_status && row.heartbeat_status !== "running" && row.heartbeat_status !== "idle") {
    return {
      recovery_reason: "unhealthy_heartbeat_status",
      detail: `heartbeat status reported ${row.heartbeat_status}`,
    };
  }

  return null;
}

function hasRecentRestartAction(row, recentActions) {
  return recentActions.some((action) => {
    if (action.target_worker_id !== row.worker_id) return false;
    if (action.action_type !== "restart_service") return false;
    const ageMinutes = minutesSince(action.requested_at);
    if (ageMinutes == null || ageMinutes > AUTO_RECOVERY_RESTART_COOLDOWN_MINUTES) return false;
    return ["pending", "validated", "executed"].includes(action.status);
  });
}

export async function autoRecoverWorkers({ apply = false, snapshot = null } = {}) {
  const rows = snapshot ?? await collectControlPlaneSnapshot();
  const recentActions = await supabaseGet(
    "worker_control_actions?select=target_worker_id,action_type,status,requested_by,requested_at&order=requested_at.desc&limit=200",
  );
  const recoveries = [];

  for (const row of rows) {
    if (!shouldAutoRecover(row)) continue;

    const reason = buildAutoRecoveryReason(row);
    if (!reason) continue;

    if (hasRecentRestartAction(row, recentActions)) {
      recoveries.push({
        worker_id: row.worker_id,
        runtime_label: row.runtime_label,
        action_type: "restart_service",
        recovery_reason: reason.recovery_reason,
        detail: reason.detail,
        status: "cooldown_skip",
      });
      continue;
    }

    const action = {
      target_worker_id: row.worker_id,
      action_type: "restart_service",
      payload: {
        recovery_reason: reason.recovery_reason,
        runtime_label: row.runtime_label,
      },
      requested_by: AUTO_RECOVERY_REQUESTED_BY,
      reason: `Automatic recovery: ${reason.detail}`,
    };
    const validation = validateAction(action);

    if (!validation.valid) {
      recoveries.push({
        worker_id: row.worker_id,
        runtime_label: row.runtime_label,
        action_type: action.action_type,
        recovery_reason: reason.recovery_reason,
        detail: reason.detail,
        status: "blocked",
        validation,
      });
      continue;
    }

    const inserted = apply ? await requestAction(action) : null;
    recoveries.push({
      worker_id: row.worker_id,
      runtime_label: row.runtime_label,
      action_type: action.action_type,
      recovery_reason: reason.recovery_reason,
      detail: reason.detail,
      status: apply ? "queued" : "suggested",
      inserted,
    });
  }

  return recoveries;
}

export function validateAction(action) {
  const issues = [];
  if (!action.target_worker_id) issues.push("missing target_worker_id");
  if (!action.action_type) issues.push("missing action_type");
  if (action.action_type && !ALLOWED_ACTIONS.has(action.action_type)) {
    issues.push(`unsupported action_type: ${action.action_type}`);
  }
  if ((action.action_type === "update_schedule") && typeof action.payload?.schedule_seconds !== "number") {
    issues.push("update_schedule requires numeric payload.schedule_seconds");
  }
  if ((action.action_type === "set_maintenance_mode") && typeof action.payload?.maintenance_mode !== "boolean") {
    issues.push("set_maintenance_mode requires boolean payload.maintenance_mode");
  }

  return {
    valid: issues.length === 0,
    issues,
    reviewed_at: nowIso(),
  };
}

function buildControlPlanePatch(action) {
  switch (action.action_type) {
    case "pause_worker":
      return {
        enabled: false,
        desired_state: "paused",
        maintenance_mode: false,
        last_changed_at: nowIso(),
        last_changed_by: action.approved_by ?? action.requested_by ?? "ops-control-worker",
      };
    case "resume_worker":
      return {
        enabled: true,
        desired_state: "running",
        maintenance_mode: false,
        last_changed_at: nowIso(),
        last_changed_by: action.approved_by ?? action.requested_by ?? "ops-control-worker",
      };
    case "update_schedule":
      return {
        schedule_seconds: action.payload.schedule_seconds,
        last_changed_at: nowIso(),
        last_changed_by: action.approved_by ?? action.requested_by ?? "ops-control-worker",
      };
    case "set_maintenance_mode":
      return {
        maintenance_mode: action.payload.maintenance_mode,
        desired_state: action.payload.maintenance_mode ? "maintenance" : "running",
        last_changed_at: nowIso(),
        last_changed_by: action.approved_by ?? action.requested_by ?? "ops-control-worker",
      };
    default:
      return null;
  }
}

export async function validatePendingActions({ apply = false } = {}) {
  const actions = await supabaseGet("worker_control_actions?select=*&status=eq.pending&order=requested_at.asc&limit=50");
  const results = [];

  for (const action of actions) {
    const validation = validateAction(action);
    const nextStatus = validation.valid ? "validated" : "blocked";
    results.push({
      id: action.id,
      target_worker_id: action.target_worker_id,
      action_type: action.action_type,
      status: nextStatus,
      validation_result: validation,
    });

    if (apply) {
      await supabasePatch(
        "worker_control_actions",
        {
          status: nextStatus,
          validation_result: validation,
          updated_at: nowIso(),
        },
        { id: `eq.${action.id}` },
      );
    }
  }

  return results;
}

export async function executeValidatedActions({ apply = false } = {}) {
  const snapshot = await collectControlPlaneSnapshot();
  const workersById = new Map(snapshot.map((row) => [row.worker_id, row]));
  const actions = await supabaseGet(
    "worker_control_actions?select=*&status=eq.validated&order=requested_at.asc&limit=50"
  );
  const results = [];

  for (const action of actions) {
    const patch = buildControlPlanePatch(action);
    const worker = workersById.get(action.target_worker_id) ?? null;
    const result = {
      id: action.id,
      target_worker_id: action.target_worker_id,
      action_type: action.action_type,
    };

    if (!patch) {
      result.status = "awaiting_manual_execution";
      result.execution_result = {
        applied_to_control_plane: false,
        reason: "action requires a human or future launchd executor",
        reviewed_at: nowIso(),
      };
    } else {
      const launchdResult = worker ? applyLaunchdAction(action, worker) : {
        applied_to_launchd: false,
        reason: "worker not found in snapshot",
      };
      result.status = "executed";
      result.execution_result = {
        applied_to_control_plane: true,
        applied_to_launchd: launchdResult.applied_to_launchd ?? false,
        launchd_result: launchdResult,
        patch,
        executed_at: nowIso(),
      };
    }

    results.push(result);

    if (apply) {
      if (patch) {
        await supabasePatch(
          "worker_control_plane",
          patch,
          { worker_id: `eq.${action.target_worker_id}` },
        );
      }

      await supabasePatch(
        "worker_control_actions",
        {
          status: result.status,
          execution_result: result.execution_result,
          executed_at: nowIso(),
          updated_at: nowIso(),
        },
        { id: `eq.${action.id}` },
      );
    }
  }

  return results;
}

export async function diagnoseWorker(workerId, { useHermes = false } = {}) {
  const snapshot = await collectControlPlaneSnapshot();
  const worker = snapshot.find((row) => row.worker_id === workerId);
  if (!worker) {
    throw new Error(`Unknown worker_id: ${workerId}`);
  }

  const diagnosis = {
    worker,
    summary: `${worker.worker_id} is ${worker.computed_health}`,
    likely_issue: worker.computed_health === "warning"
      ? "desired running state does not fully match runtime/heartbeat state"
      : "no obvious issue detected",
    recommended_action: worker.computed_health === "warning"
      ? "inspect launchd status and recent logs before any restart"
      : "no action required",
  };

  if (!useHermes) return diagnosis;

  const hermes = await diagnoseWithHermes(diagnosis);
  return { ...diagnosis, hermes };
}

export async function requestAction({
  target_worker_id,
  action_type,
  payload = {},
  requested_by = "operator",
  reason = null,
}) {
  const inserted = await supabaseInsert("worker_control_actions", {
    target_worker_id,
    action_type,
    payload,
    requested_by,
    status: "pending",
    validation_result: {},
    execution_result: reason ? { requested_reason: reason } : {},
  });

  return inserted[0] ?? null;
}

export async function requestActionWithHermes({
  worker_id,
  operator_intent,
  requested_by = "operator",
}) {
  const snapshot = await collectControlPlaneSnapshot();
  const worker = snapshot.find((row) => row.worker_id === worker_id);
  if (!worker) throw new Error(`Unknown worker_id: ${worker_id}`);

  const proposal = await proposeActionWithHermes({
    operator_intent,
    worker,
    allowed_actions: [...ALLOWED_ACTIONS],
  });

  const fallbackProposal = (() => {
    const text = operator_intent.toLowerCase();
    if (text.includes("pause")) {
      return {
        target_worker_id: worker_id,
        action_type: "pause_worker",
        payload: {},
        reason: operator_intent,
        confidence: 55,
      };
    }
    if (text.includes("resume") || text.includes("unpause")) {
      return {
        target_worker_id: worker_id,
        action_type: "resume_worker",
        payload: {},
        reason: operator_intent,
        confidence: 55,
      };
    }
    if (text.includes("maintenance")) {
      return {
        target_worker_id: worker_id,
        action_type: "set_maintenance_mode",
        payload: { maintenance_mode: true },
        reason: operator_intent,
        confidence: 50,
      };
    }
    const scheduleMatch = text.match(/(\d+)\s*(second|seconds|minute|minutes|hour|hours)/);
    if (text.includes("schedule") || text.includes("interval")) {
      let schedule_seconds = null;
      if (scheduleMatch) {
        const amount = Number(scheduleMatch[1]);
        const unit = scheduleMatch[2];
        if (unit.startsWith("second")) schedule_seconds = amount;
        if (unit.startsWith("minute")) schedule_seconds = amount * 60;
        if (unit.startsWith("hour")) schedule_seconds = amount * 3600;
      }
      if (schedule_seconds) {
        return {
          target_worker_id: worker_id,
          action_type: "update_schedule",
          payload: { schedule_seconds },
          reason: operator_intent,
          confidence: 50,
        };
      }
    }
    return null;
  })();

  const usableProposal = proposal ?? fallbackProposal;
  if (!usableProposal) {
    throw new Error("Hermes did not return a usable action proposal");
  }

  const action = {
    target_worker_id: usableProposal.target_worker_id ?? worker_id,
    action_type: usableProposal.action_type,
    payload: usableProposal.payload ?? {},
    requested_by,
    reason: usableProposal.reason ?? operator_intent,
  };

  const validation = validateAction(action);
  if (!validation.valid) {
    return { proposal: usableProposal, validation, inserted: null };
  }

  const inserted = await requestAction(action);
  return { proposal: usableProposal, validation, inserted, hermes_available: Boolean(proposal) };
}

export async function runOpsControlWorker({
  quiet = false,
  auto_recover = false,
  apply_auto_recovery = false,
  validate_actions = false,
  apply_validation = false,
  execute_actions = false,
  apply_execution = false,
  diagnose = null,
  use_hermes = false,
  request_action = null,
  target = null,
  action_type = null,
  requested_by = "operator",
} = {}) {
  if (diagnose) {
    const result = await diagnoseWorker(diagnose, { useHermes: use_hermes });
    if (!quiet) console.log(JSON.stringify(result, null, 2));
    return result;
  }

  if (request_action) {
    if (!target) throw new Error("--request-action requires --target <worker_id>");
    const result = use_hermes
      ? await requestActionWithHermes({
          worker_id: target,
          operator_intent: request_action,
          requested_by,
        })
      : await requestAction({
          target_worker_id: target,
          action_type,
          payload: {},
          requested_by,
          reason: request_action,
        });
    if (!quiet) console.log(JSON.stringify(result, null, 2));
    return result;
  }

  const snapshot = await collectControlPlaneSnapshot();
  const result = { snapshot };

  if (auto_recover) {
    result.auto_recovery = await autoRecoverWorkers({
      apply: apply_auto_recovery,
      snapshot,
    });
  }

  if (validate_actions) {
    result.validations = await validatePendingActions({ apply: apply_validation });
  }

  if (execute_actions) {
    result.executions = await executeValidatedActions({ apply: apply_execution });
  }

  if (!quiet) console.log(JSON.stringify(result, null, 2));
  return result;
}

const args = process.argv.slice(2);
const isDirect = process.argv[1]?.endsWith("ops_control_worker.js");

function getArg(flag, fallback = null) {
  const index = args.indexOf(flag);
  return index !== -1 ? args[index + 1] : fallback;
}

if (args.includes("--help")) {
  console.log([
    "Usage: node ops_control_worker.js [options]",
    "",
    "Options:",
    "  --diagnose <worker_id>     Diagnose one worker/service",
    "  --use-hermes              Ask Hermes for read-only diagnosis help",
    "  --request-action <text>   Draft/queue a control action from operator intent",
    "  --target <worker_id>      Target worker/service for --request-action",
    "  --action-type <type>      Direct action type when not using Hermes",
    "  --requested-by <name>     Actor name for queued action (default: operator)",
    "  --auto-recover            Suggest safe restart_service actions for unhealthy automatic workers",
    "  --apply-auto-recovery     Persist suggested auto-recovery actions to Supabase",
    "  --validate-actions        Validate pending worker_control_actions",
    "  --apply-validation        Persist validated/blocked statuses back to Supabase",
    "  --execute-actions         Execute validated actions against the control plane",
    "  --apply-execution         Persist execution results back to Supabase",
    "  --quiet                   Suppress pretty console output",
    "  --help                    Show this help",
  ].join("\n"));
  process.exit(0);
}

if (isDirect) {
  runOpsControlWorker({
    quiet: args.includes("--quiet"),
    auto_recover: args.includes("--auto-recover"),
    apply_auto_recovery: args.includes("--apply-auto-recovery"),
    validate_actions: args.includes("--validate-actions"),
    apply_validation: args.includes("--apply-validation"),
    execute_actions: args.includes("--execute-actions"),
    apply_execution: args.includes("--apply-execution"),
    diagnose: getArg("--diagnose", null),
    use_hermes: args.includes("--use-hermes"),
    request_action: getArg("--request-action", null),
    target: getArg("--target", null),
    action_type: getArg("--action-type", null),
    requested_by: getArg("--requested-by", "operator"),
  }).catch((err) => {
    console.error(`[ops-control-worker] Fatal: ${err.message}`);
    if (process.env.DEBUG) console.error(err.stack);
    process.exit(1);
  });
}
