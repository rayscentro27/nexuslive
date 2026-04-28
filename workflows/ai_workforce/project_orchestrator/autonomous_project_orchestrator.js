#!/usr/bin/env node

import "../env.js";
import { readFileSync, writeFileSync } from "fs";
import { resolve } from "path";

import { dispatch } from "../workforce_dispatcher.js";
import { JOB_TYPE, APPROVAL_REQUIRED_JOBS } from "../workforce_job_types.js";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_KEY;

export const PROJECT_TYPE = Object.freeze({
  GRANT_PIPELINE: "grant_pipeline",
  OPPORTUNITY_PIPELINE: "opportunity_pipeline",
  CONTENT_PIPELINE: "content_pipeline",
  CRM_PIPELINE: "crm_pipeline",
  CREDIT_PIPELINE: "credit_pipeline",
  TRADING_PIPELINE: "trading_pipeline",
  OPS_PIPELINE: "ops_pipeline",
  CUSTOM_MULTI_ROLE: "custom_multi_role",
});

const DEFAULT_OWNER = "ray@nexus";

function nowIso() {
  return new Date().toISOString();
}

function getArg(args, flag, defaultValue = undefined) {
  const idx = args.indexOf(flag);
  return idx !== -1 ? args[idx + 1] : defaultValue;
}

function hasFlag(args, flag) {
  return args.includes(flag);
}

function loadProject(args) {
  const projectFile = getArg(args, "--project-file");
  const projectJson = getArg(args, "--project-json");

  if (!projectFile && !projectJson) {
    throw new Error("Provide --project-file <path> or --project-json '<json>'.");
  }

  const parsed = projectFile
    ? JSON.parse(readFileSync(resolve(process.cwd(), projectFile), "utf8"))
    : JSON.parse(projectJson);

  return normalizeProject(parsed);
}

function normalizeList(value) {
  if (!value) return [];
  return Array.isArray(value) ? value.filter(Boolean) : [value];
}

function normalizeProject(project = {}) {
  return {
    id: project.id ?? null,
    name: project.name ?? project.project_name ?? "Untitled Nexus Project",
    owner: project.owner ?? DEFAULT_OWNER,
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
  if (!Object.values(PROJECT_TYPE).includes(project.project_type)) {
    issues.push(`unsupported project_type: ${project.project_type}`);
  }

  return {
    valid: issues.length === 0,
    issues,
  };
}

function makeJob({ stage, role, job, payload = {}, rationale }) {
  return {
    stage,
    role,
    job,
    payload,
    rationale,
    approval_required: APPROVAL_REQUIRED_JOBS.has(job),
  };
}

function deriveResearchTopic(project) {
  if (project.topics.length === 1) return project.topics[0];

  switch (project.project_type) {
    case PROJECT_TYPE.GRANT_PIPELINE:
      return "grant_research";
    case PROJECT_TYPE.OPPORTUNITY_PIPELINE:
      return "business_opportunities";
    case PROJECT_TYPE.CRM_PIPELINE:
      return "crm_automation";
    case PROJECT_TYPE.CREDIT_PIPELINE:
      return "credit_repair";
    case PROJECT_TYPE.TRADING_PIPELINE:
      return "trading";
    default:
      return null;
  }
}

export function buildProjectPlan(project) {
  const sinceDays = Number(project.payload.since_days ?? 14);
  const minScore = Number(project.payload.min_score ?? 35);
  const researchTopic = deriveResearchTopic(project);
  const jobs = [];

  switch (project.project_type) {
    case PROJECT_TYPE.GRANT_PIPELINE:
      jobs.push(
        makeJob({
          stage: "research",
          role: "research_worker",
          job: JOB_TYPE.RESEARCH_ALL,
          payload: { topic: researchTopic, since_days: sinceDays, dry_run: false },
          rationale: "Gather fresh grant artifacts before scoring.",
        }),
        makeJob({
          stage: "analysis",
          role: "grant_worker",
          job: JOB_TYPE.GRANT_SCAN,
          payload: { since_days: sinceDays, min_score: minScore, dry_run: false },
          rationale: "Normalize and rank grant opportunities.",
        }),
        makeJob({
          stage: "brief",
          role: "grant_worker",
          job: JOB_TYPE.GRANT_BRIEF,
          payload: { since_days: sinceDays, min_score: minScore, dry_run: false },
          rationale: "Produce operator-facing summary of top grants.",
        }),
      );
      break;

    case PROJECT_TYPE.OPPORTUNITY_PIPELINE:
      jobs.push(
        makeJob({
          stage: "research",
          role: "research_worker",
          job: JOB_TYPE.RESEARCH_ALL,
          payload: { topic: researchTopic, since_days: sinceDays, dry_run: false },
          rationale: "Refresh business opportunity and CRM automation artifacts.",
        }),
        makeJob({
          stage: "analysis",
          role: "opportunity_worker",
          job: JOB_TYPE.OPPORTUNITY_SCAN,
          payload: { since_days: sinceDays, min_score: minScore, dry_run: false },
          rationale: "Score monetizable opportunities from current artifact set.",
        }),
        makeJob({
          stage: "brief",
          role: "opportunity_worker",
          job: JOB_TYPE.OPPORTUNITY_BRIEF,
          payload: { since_days: sinceDays, min_score: minScore, dry_run: false },
          rationale: "Summarize top opportunities and recurring niches.",
        }),
      );
      break;

    case PROJECT_TYPE.CONTENT_PIPELINE:
      jobs.push(
        makeJob({
          stage: "content_brief",
          role: "content_worker",
          job: JOB_TYPE.CONTENT_BRIEF_GENERATE,
          payload: { since_days: sinceDays, dry_run: false },
          rationale: "Turn current briefs and opportunities into a content plan.",
        }),
      );
      if (project.deliverables.includes("social_posts")) {
        jobs.push(
          makeJob({
            stage: "draft_social",
            role: "content_worker",
            job: JOB_TYPE.CONTENT_SOCIAL_DRAFT,
            payload: { since_days: sinceDays, dry_run: false },
            rationale: "Prepare social drafts for human review.",
          }),
        );
      }
      if (project.deliverables.includes("newsletter")) {
        jobs.push(
          makeJob({
            stage: "draft_newsletter",
            role: "content_worker",
            job: JOB_TYPE.CONTENT_NEWSLETTER_DRAFT,
            payload: { since_days: sinceDays, dry_run: false },
            rationale: "Prepare newsletter draft for human review.",
          }),
        );
      }
      break;

    case PROJECT_TYPE.CRM_PIPELINE:
      jobs.push(
        makeJob({
          stage: "research",
          role: "research_worker",
          job: JOB_TYPE.RESEARCH_ALL,
          payload: { topic: researchTopic, since_days: sinceDays, dry_run: false },
          rationale: "Refresh CRM automation research artifacts.",
        }),
        makeJob({
          stage: "crm_scan",
          role: "crm_copilot_worker",
          job: JOB_TYPE.CRM_WORKFLOW_SCAN,
          payload: { since_days: sinceDays, dry_run: false },
          rationale: "Identify workflow gaps and automation opportunities.",
        }),
        makeJob({
          stage: "crm_suggestions",
          role: "crm_copilot_worker",
          job: JOB_TYPE.CRM_SUGGESTION_GENERATE,
          payload: { since_days: sinceDays, dry_run: false },
          rationale: "Generate staff-facing CRM recommendations.",
        }),
      );
      break;

    case PROJECT_TYPE.CREDIT_PIPELINE:
      jobs.push(
        makeJob({
          stage: "research",
          role: "research_worker",
          job: JOB_TYPE.RESEARCH_ALL,
          payload: { topic: researchTopic, since_days: sinceDays, dry_run: false },
          rationale: "Refresh credit repair research artifacts.",
        }),
        makeJob({
          stage: "credit_scan",
          role: "credit_worker",
          job: JOB_TYPE.CREDIT_ARTIFACT_SCAN,
          payload: { since_days: sinceDays, dry_run: false },
          rationale: "Extract dispute strategies and policy updates.",
        }),
        makeJob({
          stage: "credit_policy",
          role: "credit_worker",
          job: JOB_TYPE.CREDIT_POLICY_REVIEW,
          payload: { since_days: sinceDays, dry_run: false },
          rationale: "Review legal/policy implications before drafting.",
        }),
      );
      if (project.deliverables.includes("dispute_draft")) {
        jobs.push(
          makeJob({
            stage: "credit_draft",
            role: "credit_worker",
            job: JOB_TYPE.CREDIT_DISPUTE_DRAFT,
            payload: { dry_run: false },
            rationale: "Generate PII-free dispute template draft.",
          }),
        );
      }
      break;

    case PROJECT_TYPE.TRADING_PIPELINE:
      jobs.push(
        makeJob({
          stage: "research",
          role: "research_worker",
          job: JOB_TYPE.RESEARCH_ALL,
          payload: { topic: researchTopic, since_days: sinceDays, dry_run: false },
          rationale: "Refresh trading research artifacts before strategy work.",
        }),
        makeJob({
          stage: "strategy_scan",
          role: "trading_research_worker",
          job: JOB_TYPE.TRADING_ARTIFACT_SCAN,
          payload: { since_days: sinceDays, dry_run: false },
          rationale: "Extract patterns and candidate trade frameworks.",
        }),
        makeJob({
          stage: "strategy_draft",
          role: "trading_research_worker",
          job: JOB_TYPE.TRADING_STRATEGY_DRAFT,
          payload: { since_days: sinceDays, dry_run: false },
          rationale: "Produce draft strategy proposal for human review.",
        }),
        makeJob({
          stage: "risk_review",
          role: "risk_compliance_worker",
          job: JOB_TYPE.RISK_PROPOSAL_REVIEW,
          payload: { dry_run: false },
          rationale: "Check proposal against risk rules after drafting.",
        }),
      );
      break;

    case PROJECT_TYPE.OPS_PIPELINE:
      jobs.push(
        makeJob({
          stage: "ops_health",
          role: "ops_monitoring_worker",
          job: JOB_TYPE.OPS_HEALTH_CHECK,
          payload: { dry_run: false },
          rationale: "Inspect worker/service health across the stack.",
        }),
        makeJob({
          stage: "ops_queue",
          role: "ops_monitoring_worker",
          job: JOB_TYPE.OPS_QUEUE_METRICS,
          payload: { dry_run: false },
          rationale: "Report queue depth and stale pipeline conditions.",
        }),
      );
      break;

    case PROJECT_TYPE.CUSTOM_MULTI_ROLE:
    default:
      for (const requestedRole of project.requested_roles) {
        if (requestedRole === "grant_worker") {
          jobs.push(
            makeJob({
              stage: "custom_grant_scan",
              role: requestedRole,
              job: JOB_TYPE.GRANT_SCAN,
              payload: { since_days: sinceDays, min_score: minScore, dry_run: false },
              rationale: "User-requested grant scan.",
            }),
          );
        } else if (requestedRole === "opportunity_worker") {
          jobs.push(
            makeJob({
              stage: "custom_opportunity_scan",
              role: requestedRole,
              job: JOB_TYPE.OPPORTUNITY_SCAN,
              payload: { since_days: sinceDays, min_score: minScore, dry_run: false },
              rationale: "User-requested opportunity scan.",
            }),
          );
        } else if (requestedRole === "content_worker") {
          jobs.push(
            makeJob({
              stage: "custom_content_brief",
              role: requestedRole,
              job: JOB_TYPE.CONTENT_BRIEF_GENERATE,
              payload: { since_days: sinceDays, dry_run: false },
              rationale: "User-requested content generation.",
            }),
          );
        }
      }
      break;
  }

  return jobs;
}

async function supabaseInsert(table, row) {
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
    body: JSON.stringify(Array.isArray(row) ? row : [row]),
  });

  if (!res.ok) {
    throw new Error(`Supabase INSERT ${table}: ${res.status} ${await res.text()}`);
  }

  return res.json();
}

async function persistProjectPlan(project, plan, results = []) {
  const projectRow = {
    project_name: project.name,
    project_type: project.project_type,
    objective: project.objective,
    owner: project.owner,
    priority: project.priority,
    autonomy_mode: project.autonomy_mode,
    status: "planned",
    deadline: project.deadline,
    constraints: project.constraints,
    deliverables: project.deliverables,
    requested_roles: project.requested_roles,
    metadata: {
      topics: project.topics,
      payload: project.payload,
      plan_size: plan.length,
      created_via: "autonomous_project_orchestrator",
      created_at: nowIso(),
    },
  };

  const [projectInserted] = await supabaseInsert("autonomous_projects", projectRow);

  const runRows = plan.map((job, idx) => ({
    project_id: projectInserted.id,
    run_order: idx + 1,
    stage_name: job.stage,
    role_id: job.role,
    job_type: job.job,
    status: results[idx]?.status ?? "planned",
    approval_required: job.approval_required,
    rationale: job.rationale,
    payload: job.payload,
    execution_result: results[idx]?.result ?? {},
  }));

  if (runRows.length) {
    await supabaseInsert("autonomous_project_runs", runRows);
  }

  return {
    project_id: projectInserted.id,
    run_count: runRows.length,
  };
}

export async function executeProjectPlan(plan, options = {}) {
  const {
    liveDispatch = false,
    skipApprovalJobs = false,
  } = options;

  const results = [];

  for (const item of plan) {
    if (item.approval_required && !skipApprovalJobs) {
      results.push({
        role: item.role,
        job: item.job,
        status: "awaiting_approval",
        result: {
          skipped: true,
          reason: "approval_required",
        },
      });
      continue;
    }

    try {
      const result = await dispatch({
        role: item.role,
        job: item.job,
        payload: item.payload,
        skipApprovalGate: skipApprovalJobs,
        dryRun: !liveDispatch,
      });
      results.push({
        role: item.role,
        job: item.job,
        status: liveDispatch ? "completed" : "validated",
        result,
      });
    } catch (error) {
      results.push({
        role: item.role,
        job: item.job,
        status: "failed",
        result: {
          error: error.message,
        },
      });
    }
  }

  return results;
}

function summarizePlan(project, plan, results = []) {
  return {
    project_name: project.name,
    project_type: project.project_type,
    objective: project.objective,
    priority: project.priority,
    autonomy_mode: project.autonomy_mode,
    topics: project.topics,
    deliverables: project.deliverables,
    constraints: project.constraints,
    plan,
    results,
    generated_at: nowIso(),
  };
}

function printSummary(summary) {
  console.log(JSON.stringify(summary, null, 2));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);

  if (hasFlag(args, "--help")) {
    console.log([
      "Usage: node project_orchestrator/autonomous_project_orchestrator.js --project-file <path> [options]",
      "",
      "Options:",
      "  --project-file <path>   Path to project JSON spec",
      "  --project-json <json>   Inline project JSON",
      "  --execute               Run through workforce_dispatcher",
      "  --live-dispatch         Invoke workers for real (default execute mode is validation only)",
      "  --skip-approval-jobs    Execute approval-gated jobs after explicit human sign-off",
      "  --persist               Save project + plan rows to Supabase",
      "  --write-plan <path>     Write the generated summary JSON to disk",
      "  --help                  Show this help",
    ].join("\n"));
    process.exit(0);
  }

  const project = loadProject(args);
  const validation = validateProject(project);
  if (!validation.valid) {
    console.error(`[project-orchestrator] Invalid project spec: ${validation.issues.join("; ")}`);
    process.exit(1);
  }

  const plan = buildProjectPlan(project);
  const execute = hasFlag(args, "--execute");
  const liveDispatch = hasFlag(args, "--live-dispatch");
  const skipApprovalJobs = hasFlag(args, "--skip-approval-jobs");
  const shouldPersist = hasFlag(args, "--persist");
  const writePlanPath = getArg(args, "--write-plan");

  const results = execute
    ? await executeProjectPlan(plan, { liveDispatch, skipApprovalJobs })
    : [];

  const summary = summarizePlan(project, plan, results);

  if (writePlanPath) {
    writeFileSync(resolve(process.cwd(), writePlanPath), JSON.stringify(summary, null, 2));
  }

  if (shouldPersist) {
    try {
      summary.persistence = await persistProjectPlan(project, plan, results);
    } catch (error) {
      summary.persistence_error = error.message;
    }
  }

  printSummary(summary);
}
