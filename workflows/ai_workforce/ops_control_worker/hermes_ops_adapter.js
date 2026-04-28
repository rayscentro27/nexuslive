import "../env.js";
import { runOllamaFallback } from "../lib/ollamaFallback.js";

const HERMES_GATEWAY_URL = process.env.HERMES_GATEWAY_URL ?? "http://localhost:8642";
const HERMES_TOKEN = process.env.HERMES_GATEWAY_TOKEN ?? "";
const ENABLE_HERMES_OPS_DIAGNOSIS = (process.env.ENABLE_HERMES_OPS_DIAGNOSIS ?? "true") === "true";
const ENABLE_HERMES_OPS_ACTIONS = (process.env.ENABLE_HERMES_OPS_ACTIONS ?? "true") === "true";

function extractJsonObject(raw) {
  if (!raw) return null;

  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)```/i);
  const candidates = fenced ? [fenced[1], raw] : [raw];

  for (const candidate of candidates) {
    const trimmed = candidate.trim();
    try {
      return JSON.parse(trimmed);
    } catch {
      const match = trimmed.match(/\{[\s\S]*\}/);
      if (!match) continue;
      try {
        return JSON.parse(match[0]);
      } catch {
        continue;
      }
    }
  }

  return null;
}

function buildPrompt(snapshot) {
  return [
    "You are Hermes, the Nexus operations copilot.",
    "Analyze this worker/process snapshot and return JSON only.",
    "Do not propose destructive actions. Focus on diagnosis and the safest next step.",
    "",
    "Return exactly:",
    "{",
    '  "summary": "one sentence",',
    '  "health": "healthy|warning|critical",',
    '  "likely_issue": "short diagnosis",',
    '  "recommended_action": "short safe next step",',
    '  "confidence": 0-100',
    "}",
    "",
    `Snapshot:\n${JSON.stringify(snapshot, null, 2).slice(0, 4000)}`,
  ].join("\n");
}

async function callHermes(messages, { max_tokens = 300, temperature = 0.2 } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (HERMES_TOKEN) headers.Authorization = `Bearer ${HERMES_TOKEN}`;

  const res = await fetch(`${HERMES_GATEWAY_URL}/v1/chat/completions`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      model: "hermes",
      messages,
      max_tokens,
      temperature,
    }),
    signal: AbortSignal.timeout(30_000),
  });

  if (!res.ok) throw new Error(`Hermes ${res.status}`);
  const data = await res.json();
  return data?.choices?.[0]?.message?.content ?? "";
}

export async function diagnoseWithHermes(snapshot, { modelSource = "auto" } = {}) {
  if (!ENABLE_HERMES_OPS_DIAGNOSIS) return null;

  const prompt = buildPrompt(snapshot);
  let raw = null;

  // ── Try Hermes unless caller wants Netcup directly ────────────────────────
  if (modelSource !== "netcup_ollama") {
    try {
      raw = await callHermes([
        { role: "system", content: "You are Hermes. Return valid JSON only." },
        { role: "user", content: prompt },
      ]);
      if (raw) {
        console.log("[hermes_ops] Diagnosis: Hermes success");
        return extractJsonObject(raw);
      }
      console.warn("[hermes_ops] Diagnosis: Hermes returned empty response");
    } catch (err) {
      console.error("[hermes_ops] Diagnosis: Hermes failed —", err?.message ?? err);
    }
  }

  // ── Netcup Ollama fallback ────────────────────────────────────────────────
  if (modelSource === "netcup_ollama" || modelSource === "auto") {
    console.warn("[hermes_ops] Diagnosis: triggering Netcup Ollama fallback");
    const fb = await runOllamaFallback(
      `System: You are Hermes. Return valid JSON only.\n\n${prompt}`
    );
    if (fb.success) {
      console.log("[hermes_ops] Diagnosis: Netcup Ollama fallback succeeded");
      return extractJsonObject(fb.response);
    }
    console.error("[hermes_ops] Diagnosis: Netcup fallback failed —", fb.error);
  }

  return null;
}

function buildActionPrompt({ operator_intent, worker, allowed_actions }) {
  return [
    "You are Hermes, the Nexus operations copilot.",
    "Convert the operator's request into a safe control-plane action.",
    "Return JSON only. Pick exactly one action_type from the allowed list.",
    "Do not choose destructive or hidden machine actions.",
    "",
    `Allowed action_type values: ${allowed_actions.join(", ")}`,
    "",
    "Return exactly:",
    "{",
    '  "target_worker_id": "worker id",',
    '  "action_type": "one allowed action",',
    '  "payload": {},',
    '  "reason": "short explanation",',
    '  "confidence": 0-100',
    "}",
    "",
    `Worker context:\n${JSON.stringify(worker, null, 2).slice(0, 1500)}`,
    "",
    `Operator intent:\n${operator_intent}`,
  ].join("\n");
}

export async function proposeActionWithHermes({
  operator_intent,
  worker,
  allowed_actions,
  modelSource = "auto",
}) {
  if (!ENABLE_HERMES_OPS_ACTIONS) return null;

  const prompt = buildActionPrompt({ operator_intent, worker, allowed_actions });
  let raw = null;

  // ── Try Hermes unless caller wants Netcup directly ────────────────────────
  if (modelSource !== "netcup_ollama") {
    try {
      raw = await callHermes([
        { role: "system", content: "You are Hermes. Return valid JSON only." },
        { role: "user", content: prompt },
      ], { max_tokens: 350, temperature: 0.1 });

      if (raw) {
        console.log("[hermes_ops] Action: Hermes success");
        return extractJsonObject(raw);
      }
      console.warn("[hermes_ops] Action: Hermes returned empty response");
    } catch (err) {
      console.error("[hermes_ops] Action: Hermes failed —", err?.message ?? err);
    }
  }

  // ── Netcup Ollama fallback ────────────────────────────────────────────────
  if (modelSource === "netcup_ollama" || modelSource === "auto") {
    console.warn("[hermes_ops] Action: triggering Netcup Ollama fallback");
    const fb = await runOllamaFallback(
      `System: You are Hermes. Return valid JSON only.\n\n${prompt}`
    );
    if (fb.success) {
      console.log("[hermes_ops] Action: Netcup Ollama fallback succeeded");
      return extractJsonObject(fb.response);
    }
    console.error("[hermes_ops] Action: Netcup fallback failed —", fb.error);
  }

  return null;
}
