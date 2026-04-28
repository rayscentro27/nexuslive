/**
 * lab_context.js
 * Assembles a full context pack for AI analysis:
 *   - Latest market price snapshot (OANDA)
 *   - Research summaries (top 3, keyword-matched)
 *   - Strategy library entry (if exists)
 *   - Options Greeks context (if options asset_type)
 *   - Vector memory / research claims (graceful empty fallback)
 */

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

function h() {
  return {
    "Content-Type": "application/json",
    "apikey":        SUPABASE_KEY,
    "Authorization": `Bearer ${SUPABASE_KEY}`,
  };
}

async function safeFetch(url) {
  try {
    const res = await fetch(url, { headers: h() });
    if (!res.ok) return [];
    const d = await res.json();
    return Array.isArray(d) ? d : [];
  } catch { return []; }
}

// ── Market snapshot ───────────────────────────────────────────────────────────

async function getMarketSnapshot(symbol) {
  const url = new URL(`${SUPABASE_URL}/rest/v1/market_price_snapshots`);
  url.searchParams.set("symbol", `eq.${symbol}`);
  url.searchParams.set("select", "symbol,bid,ask,mid,spread,created_at");
  url.searchParams.set("order",  "created_at.desc");
  url.searchParams.set("limit",  "1");
  const rows = await safeFetch(url.toString());
  return rows[0] ?? null;
}

// ── Research summaries ────────────────────────────────────────────────────────

async function getResearch(signal) {
  const url = new URL(`${SUPABASE_URL}/rest/v1/research`);
  url.searchParams.set("select", "title,content,created_at");
  url.searchParams.set("order",  "created_at.desc");
  url.searchParams.set("limit",  "6");
  const rows = await safeFetch(url.toString());

  const stratKey  = (signal.strategy_id ?? "").toLowerCase().replace(/_/g, " ");
  const symbolKey = (signal.symbol ?? "").replace("_", "").toLowerCase();

  return rows
    .map((r) => {
      const txt = `${r.title} ${r.content}`.toLowerCase();
      const score = (stratKey && txt.includes(stratKey) ? 3 : 0)
                  + (symbolKey && txt.includes(symbolKey) ? 1 : 0);
      return { ...r, _score: score };
    })
    .sort((a, b) => b._score - a._score)
    .slice(0, 3)
    .map(({ _score, content, ...r }) => ({
      ...r,
      content: (content ?? "").slice(0, 900),
    }));
}

// ── Strategy library ──────────────────────────────────────────────────────────

async function getStrategyEntry(strategyId) {
  if (!strategyId) return null;
  const url = new URL(`${SUPABASE_URL}/rest/v1/strategy_library`);
  url.searchParams.set("select", "*");
  url.searchParams.set("limit",  "1");
  const rows = await safeFetch(url.toString());
  return rows[0] ?? null;
}

// ── Research claims / artifacts ───────────────────────────────────────────────

async function getResearchClaims(symbol) {
  const url = new URL(`${SUPABASE_URL}/rest/v1/research_claims`);
  url.searchParams.set("select", "claim,source,created_at");
  url.searchParams.set("order",  "created_at.desc");
  url.searchParams.set("limit",  "5");
  return await safeFetch(url.toString());
}

// ── Options Greeks context ────────────────────────────────────────────────────
// No Webull/broker connection. Generates estimated context from signal data only.

function buildOptionsGreeksContext(signal) {
  const entry = Number(signal.entry_price ?? 0);
  const sl    = Number(signal.stop_loss   ?? 0);
  const tp    = Number(signal.take_profit ?? 0);

  // Estimate rough premium range from SL/TP distance
  const maxLoss   = Math.abs(entry - sl).toFixed(4);
  const maxGain   = Math.abs(tp - entry).toFixed(4);

  return {
    note:             "Greeks are estimated context — no broker API connected.",
    underlying:       signal.symbol,
    strategy_type:    signal.strategy_id ?? "unknown",
    premium_estimate: `$${maxLoss} max risk / $${maxGain} max gain per unit`,
    delta_guidance:   "Long calls/puts: delta 0.40–0.60 (near ATM). Spreads: net delta near zero.",
    theta_note:       "Theta decay accelerates inside 21 DTE. Prefer entry at 30–45 DTE for spreads.",
    vega_note:        "High IV environment favors premium-selling strategies (covered call, CSP, IC).",
    iv_context:       "Check current IV rank before entry. IV > 50th percentile favors sell strategies.",
    webull_note:      "Execute manually in Webull. This system produces proposals only — no auto-execution.",
  };
}

// ── Main context builder ──────────────────────────────────────────────────────

export async function buildContextPack(signal) {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error("SUPABASE_URL and SUPABASE_KEY required");
  }

  const [snapshot, researchRows, strategyEntry, claims] = await Promise.all([
    getMarketSnapshot(signal.symbol),
    getResearch(signal),
    getStrategyEntry(signal.strategy_id),
    getResearchClaims(signal.symbol),
  ]);

  const researchContext = researchRows.length
    ? researchRows.map((r, i) => `[${i + 1}] ${r.title}\n${r.content}`).join("\n\n")
    : "No matching research summaries found.";

  const strategyContext = strategyEntry
    ? JSON.stringify(strategyEntry).slice(0, 600)
    : `Strategy ID: ${signal.strategy_id ?? "none"}. No library entry found.`;

  const claimsContext = claims.length
    ? claims.map((c) => `• ${c.claim ?? JSON.stringify(c)}`).join("\n")
    : "No research claims available.";

  const optionsContext = signal.asset_type === "options"
    ? buildOptionsGreeksContext(signal)
    : null;

  return {
    signal,
    snapshot,
    researchContext,
    strategyContext,
    claimsContext,
    optionsContext,
  };
}
