import "dotenv/config";

// ── SAFETY GUARD ──────────────────────────────────────────────────────────────
// RESEARCH ONLY. No trading, no broker connections.
// ─────────────────────────────────────────────────────────────────────────────

const HERMES_GATEWAY_URL = process.env.HERMES_GATEWAY_URL ?? "http://localhost:8642";
const HERMES_GATEWAY_TOKEN = process.env.HERMES_GATEWAY_TOKEN;

const SYSTEM_PROMPT = `You are a research intelligence analyst AI. Your job is to extract structured insights from transcripts across multiple business and financial research domains.

Return ONLY valid JSON with exactly this structure — no explanation, no markdown, no preamble:
{
  "summary": "2-3 sentence factual summary of the content",
  "claims": [
    {
      "claim_text": "specific, actionable claim or insight from the content",
      "claim_type": "strategy|workflow|warning|opportunity|framework",
      "confidence": 0.85,
      "topic": "trading|credit_repair|grant_research|business_opportunities|crm_automation|general_business_intelligence",
      "subtheme": "specific subtheme or null"
    }
  ],
  "key_points": ["key point 1", "key point 2", "key point 3"],
  "action_items": ["actionable step 1", "actionable step 2"],
  "risk_warnings": ["risk or warning 1"],
  "opportunity_notes": ["opportunity or business angle 1"]
}

Rules:
- Extract 4-10 specific, non-generic claims
- Each claim must be actionable or informative, not vague
- confidence is your certainty 0.0-1.0 that the claim is accurate and well-supported
- claim_type options: strategy (how to do something), workflow (step-by-step process), warning (risk or caution), opportunity (business or financial opportunity), framework (conceptual model)
- Do NOT add any text outside the JSON object`;

/**
 * Extract structured claims from a transcript using Hermes.
 * Falls back to keyword-based extraction if Hermes is unavailable.
 *
 * @param {Object} transcript - { title, transcript_text, topic, ... }
 * @param {string} topic - classified topic
 * @returns {Promise<Object>} structured extraction result
 */
export async function extractClaims(transcript, topic) {
  const text = transcript.transcript_text ?? "";

  if (!HERMES_GATEWAY_TOKEN) {
    console.log("[claims] No HERMES_GATEWAY_TOKEN — using keyword fallback extraction.");
    return keywordFallback(transcript, topic);
  }

  // Truncate to ~6000 chars to stay within token limits
  const truncated = text.length > 6000
    ? text.slice(0, 6000) + "\n\n[transcript truncated for analysis]"
    : text;

  const userMessage = `Topic domain: ${topic}
Source: ${transcript.source_name}
Title: ${transcript.title}

Transcript:
${truncated}

Extract all key claims, insights, tactics, warnings, and opportunities as JSON:`;

  try {
    const res = await fetch(`${HERMES_GATEWAY_URL}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${HERMES_GATEWAY_TOKEN}`,
      },
      body: JSON.stringify({
        model: "hermes",
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: userMessage },
        ],
        max_tokens: 2000,
        temperature: 0.2,
      }),
    });

    if (!res.ok) {
      console.log(`[claims] Hermes returned ${res.status} — falling back to keyword extraction.`);
      return keywordFallback(transcript, topic);
    }

    const data = await res.json();
    const content = data.choices?.[0]?.message?.content ?? "";

    // Parse JSON from response (handle markdown code fences if present)
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      console.log("[claims] No JSON found in Hermes response — using keyword fallback.");
      return keywordFallback(transcript, topic);
    }

    let parsed;
    try {
      parsed = JSON.parse(jsonMatch[0]);
    } catch {
      console.log("[claims] JSON parse failed — using keyword fallback.");
      return keywordFallback(transcript, topic);
    }

    // Ensure required fields exist
    parsed.claims = Array.isArray(parsed.claims) ? parsed.claims : [];
    parsed.key_points = Array.isArray(parsed.key_points) ? parsed.key_points : [];
    parsed.action_items = Array.isArray(parsed.action_items) ? parsed.action_items : [];
    parsed.risk_warnings = Array.isArray(parsed.risk_warnings) ? parsed.risk_warnings : [];
    parsed.opportunity_notes = Array.isArray(parsed.opportunity_notes) ? parsed.opportunity_notes : [];

    console.log(`[claims] Extracted ${parsed.claims.length} claim(s) via Hermes for: "${transcript.title}"`);
    return parsed;

  } catch (err) {
    console.log(`[claims] Hermes call failed (${err.message}) — using keyword fallback.`);
    return keywordFallback(transcript, topic);
  }
}

/**
 * Keyword-based fallback when Hermes is unavailable.
 * Produces basic structure from sentence splitting.
 */
function keywordFallback(transcript, topic) {
  const text = transcript.transcript_text ?? "";

  // Split into sentences and filter meaningful ones
  const sentences = text
    .split(/[.!?]+/)
    .map(s => s.trim())
    .filter(s => s.length > 40 && s.split(" ").length > 5);

  const claims = sentences.slice(0, 6).map(s => ({
    claim_text: s,
    claim_type: "strategy",
    confidence: 0.4,
    topic,
    subtheme: null,
  }));

  const summary = sentences.slice(0, 2).join(". ").trim();

  console.log(`[claims] Fallback extraction: ${claims.length} sentence(s) from "${transcript.title}"`);

  return {
    summary: summary || transcript.title,
    claims,
    key_points: sentences.slice(0, 3),
    action_items: [],
    risk_warnings: [],
    opportunity_notes: [],
  };
}
