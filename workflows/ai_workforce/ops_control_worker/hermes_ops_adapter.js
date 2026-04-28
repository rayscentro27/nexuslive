import "../env.js";

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

export async function diagnoseWithHermes(snapshot) {
  if (!ENABLE_HERMES_OPS_DIAGNOSIS) return null;

  try {
    const raw = await callHermes([
      { role: "system", content: "You are Hermes. Return valid JSON only." },
      { role: "user", content: buildPrompt(snapshot) },
    ]);
    return extractJsonObject(raw);
  } catch {
    return null;
  }
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
}) {
  if (!ENABLE_HERMES_OPS_ACTIONS) return null;

  try {
    const raw = await callHermes([
      { role: "system", content: "You are Hermes. Return valid JSON only." },
      {
        role: "user",
        content: buildActionPrompt({ operator_intent, worker, allowed_actions }),
      },
    ], {
      max_tokens: 350,
      temperature: 0.1,
    });
    return extractJsonObject(raw);
  } catch {
    return null;
  }
}
