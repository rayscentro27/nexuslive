#!/usr/bin/env node

import "../env.js";
import http from "http";
import { URL } from "url";

import {
  PROJECT_TYPE,
  buildProjectPlan,
  executeProjectPlan,
} from "./autonomous_project_orchestrator.js";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_KEY;
const PORT = Number(process.env.PORT ?? 3000);

const PROJECT_TYPES = Object.values(PROJECT_TYPE);

function nowIso() {
  return new Date().toISOString();
}

function normalizeList(value) {
  if (!value) return [];
  return Array.isArray(value) ? value.filter(Boolean) : [value];
}

function normalizeProject(project = {}) {
  return {
    id: project.id ?? null,
    name: project.name ?? project.project_name ?? "Untitled Nexus Project",
    owner: project.owner ?? "ray@nexus",
    project_type: project.project_type ?? PROJECT_TYPE.CUSTOM_MULTI_ROLE,
    objective: project.objective ?? "",
    deadline: project.deadline ?? null,
    priority: project.priority ?? "normal",
    autonomy_mode: project.autonomy_mode ?? "assisted",
    topics: normalizeList(project.topics),
    constraints: normalizeList(project.constraints),
    deliverables: normalizeList(project.deliverables),
    requested_roles: normalizeList(project.requested_roles),
    payload: project.payload ?? {},
    metadata: project.metadata ?? {},
  };
}

function validateProject(project) {
  const issues = [];

  if (!project.name?.trim()) issues.push("name is required");
  if (!project.objective?.trim()) issues.push("objective is required");
  if (!PROJECT_TYPES.includes(project.project_type)) {
    issues.push(`unsupported project_type: ${project.project_type}`);
  }

  return {
    valid: issues.length === 0,
    issues,
  };
}

function json(res, statusCode, payload) {
  res.writeHead(statusCode, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload, null, 2));
}

async function readJsonBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  return raw ? JSON.parse(raw) : {};
}

async function supabaseInsert(table, rows) {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error("Supabase credentials are not configured.");
  }

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

  if (!res.ok) {
    throw new Error(`Supabase INSERT ${table}: ${res.status} ${await res.text()}`);
  }

  return res.json();
}

async function supabaseSelect(path) {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error("Supabase credentials are not configured.");
  }

  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    headers: {
      apikey: SUPABASE_KEY,
      Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Supabase GET ${path}: ${res.status} ${await res.text()}`);
  }

  return res.json();
}

async function persistProjectAndRuns(project, plan, results = []) {
  const [projectRow] = await supabaseInsert("autonomous_projects", {
    project_name: project.name,
    project_type: project.project_type,
    objective: project.objective,
    owner: project.owner,
    priority: project.priority,
    autonomy_mode: project.autonomy_mode,
    status: results.length ? "validated" : "planned",
    deadline: project.deadline,
    constraints: project.constraints,
    deliverables: project.deliverables,
    requested_roles: project.requested_roles,
    metadata: {
      topics: project.topics,
      payload: project.payload,
      created_via: "nexus_control_api",
      created_at: nowIso(),
    },
  });

  if (plan.length) {
    await supabaseInsert("autonomous_project_runs", plan.map((job, idx) => ({
      project_id: projectRow.id,
      run_order: idx + 1,
      stage_name: job.stage,
      role_id: job.role,
      job_type: job.job,
      status: results[idx]?.status ?? "planned",
      approval_required: job.approval_required,
      rationale: job.rationale,
      payload: job.payload,
      execution_result: results[idx]?.result ?? {},
    })));
  }

  return projectRow;
}

async function handleCreateProject(req, res, url) {
  const body = await readJsonBody(req);
  const project = normalizeProject(body.project ?? body);
  const validation = validateProject(project);

  if (!validation.valid) {
    return json(res, 400, {
      ok: false,
      error: "invalid_project",
      issues: validation.issues,
    });
  }

  const execute = body.execute === true || url.searchParams.get("execute") === "true";
  const liveDispatch = body.live_dispatch === true || url.searchParams.get("live_dispatch") === "true";
  const skipApprovalJobs = body.skip_approval_jobs === true || url.searchParams.get("skip_approval_jobs") === "true";
  const persist = body.persist === true || url.searchParams.get("persist") === "true";

  const plan = buildProjectPlan(project);
  const results = execute
    ? await executeProjectPlan(plan, { liveDispatch, skipApprovalJobs })
    : [];

  let persistence = null;
  let persistenceError = null;

  if (persist) {
    try {
      persistence = await persistProjectAndRuns(project, plan, results);
    } catch (error) {
      persistenceError = error.message;
    }
  }

  return json(res, 200, {
    ok: true,
    project_name: project.name,
    project_type: project.project_type,
    execute,
    live_dispatch: liveDispatch,
    persisted: Boolean(persistence),
    persistence_error: persistenceError,
    project_id: persistence?.id ?? null,
    plan,
    results,
    generated_at: nowIso(),
  });
}

async function handleGetProject(res, projectId) {
  try {
    const [project] = await supabaseSelect(`autonomous_projects?id=eq.${projectId}&select=*`);
    const runs = await supabaseSelect(`autonomous_project_runs?project_id=eq.${projectId}&select=*&order=run_order.asc`);

    if (!project) {
      return json(res, 404, {
        ok: false,
        error: "not_found",
      });
    }

    return json(res, 200, {
      ok: true,
      project,
      runs,
    });
  } catch (error) {
    return json(res, 500, {
      ok: false,
      error: "lookup_failed",
      message: error.message,
    });
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

  try {
    if (req.method === "GET" && url.pathname === "/health") {
      return json(res, 200, {
        ok: true,
        service: "nexus-control-api",
        status: "healthy",
        project_types: PROJECT_TYPES,
        supabase_configured: Boolean(SUPABASE_URL && SUPABASE_KEY),
        timestamp: nowIso(),
      });
    }

    if (req.method === "GET" && url.pathname === "/project-types") {
      return json(res, 200, {
        ok: true,
        project_types: PROJECT_TYPES,
      });
    }

    if (req.method === "POST" && url.pathname === "/projects") {
      return await handleCreateProject(req, res, url);
    }

    if (req.method === "GET" && url.pathname.startsWith("/projects/")) {
      const projectId = url.pathname.split("/").filter(Boolean)[1];
      return await handleGetProject(res, projectId);
    }

    return json(res, 404, {
      ok: false,
      error: "not_found",
      path: url.pathname,
    });
  } catch (error) {
    return json(res, 500, {
      ok: false,
      error: "server_error",
      message: error.message,
    });
  }
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`[nexus-control-api] listening on 0.0.0.0:${PORT}`);
});
