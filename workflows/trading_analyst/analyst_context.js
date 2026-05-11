/**
 * analyst_context.js
 * Gathers all context needed for the AI analyst to review a signal:
 *   - Latest market price snapshot for the symbol
 *   - Matching strategy entries from the research table
 *   - Recent research summaries (top 3 by relevance to symbol/strategy)
 *
 * Returns a structured context pack.
 */

import "dotenv/config";

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_KEY;

function headers() {
  return {
    "Content-Type": "application/json",
    "apikey": SUPABASE_KEY,
    "Authorization": `Bearer ${SUPABASE_KEY}`,
  };
}

async function fetchJson(url) {
  const res = await fetch(url, { headers: headers() });
  if (!res.ok) return null;
  const data = await res.json();
  return Array.isArray(data) ? data : null;
}

/**
 * Fetch latest price snapshot for this signal's symbol.
 * Oracle API stores symbols as EUR_USD; normalize for lookup.
 */
async function getMarketSnapshot(symbol) {
  const url = new URL(`${SUPABASE_URL}/rest/v1/market_price_snapshots`);
  url.searchParams.set("symbol", `eq.${symbol}`);
  url.searchParams.set("select", "symbol,bid,ask,mid,spread,created_at");
  url.searchParams.set("order", "created_at.desc");
  url.searchParams.set("limit", "1");

  const rows = await fetchJson(url.toString());
  return rows?.[0] ?? null;
}

/**
 * Fetch research summaries relevant to this signal.
 * Searches by strategy_id keyword and symbol in the title/content.
 * Returns top 3 most recent entries.
 */
async function getResearchContext(signal) {
  const url = new URL(`${SUPABASE_URL}/rest/v1/research`);
  url.searchParams.set("select", "id,title,content,created_at");
  url.searchParams.set("order", "created_at.desc");
  url.searchParams.set("limit", "3");

  const rows = await fetchJson(url.toString());
  if (!rows?.length) return [];

  // Simple relevance filter: prefer items that match strategy or symbol keywords
  const strategyKey = (signal.strategy_id || "").toLowerCase().replace(/_/g, " ");
  const symbolKey   = (signal.symbol || "").replace("_", "").toLowerCase(); // EUR_USD → eurusd

  const scored = rows.map((r) => {
    const text = `${r.title} ${r.content}`.toLowerCase();
    let score = 0;
    if (strategyKey && text.includes(strategyKey)) score += 2;
    if (symbolKey && text.includes(symbolKey))     score += 1;
    return { ...r, _score: score };
  });

  scored.sort((a, b) => b._score - a._score || 0);

  // Return top 3, strip score field, truncate content to 800 chars for prompt size
  return scored.slice(0, 3).map(({ _score, ...r }) => ({
    ...r,
    content: r.content?.slice(0, 800) ?? "",
  }));
}

/**
 * Build and return the full context pack for a signal.
 *
 * @param {Object} signal - row from tv_normalized_signals
 * @returns {Promise<{ signal, market_snapshot, strategy_context, research_context }>}
 */
export async function buildContextPack(signal) {
  if (!SUPABASE_URL || !SUPABASE_KEY) {
    throw new Error("SUPABASE_URL and SUPABASE_KEY are required");
  }

  const [market_snapshot, research_rows] = await Promise.all([
    getMarketSnapshot(signal.symbol),
    getResearchContext(signal),
  ]);

  // strategy_context: summary label derived from signal fields
  const strategy_context = signal.strategy_id
    ? `Strategy ID: ${signal.strategy_id}. Session: ${signal.session_label ?? "unknown"}. Source: ${signal.source ?? "tradingview"}.`
    : "No strategy ID provided.";

  // research_context: concatenated summaries for prompt injection
  const research_context = research_rows.length
    ? research_rows.map((r, i) => `[Research ${i + 1}] ${r.title}\n${r.content}`).join("\n\n")
    : "No matching research summaries available.";

  return {
    signal,
    market_snapshot,
    strategy_context,
    research_context,
  };
}
