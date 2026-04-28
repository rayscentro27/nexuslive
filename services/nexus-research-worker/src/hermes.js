/**
 * hermes.js — Optional Hermes refinement via Hermes.
 * Controlled by ENABLE_HERMES_REFINEMENT env flag.
 * Fail-safe: errors never fail the parent job.
 */

import { config }       from './config.js';
import { createLogger } from './logger.js';

export const VERSION = '1.0';

const logger = createLogger('hermes');

/**
 * Send base research result to Hermes for executive-style refinement.
 * Returns refined text, or null if disabled/unavailable.
 */
export async function refineWithHermes(baseResult) {
  if (!config.enableHermes) return null;

  try {
    const prompt =
      `You are a research analyst. Refine this raw research output into a concise, ` +
      `executive-style summary (3–5 bullet points max). Be direct and actionable.\n\n` +
      `Raw research:\n${JSON.stringify(baseResult, null, 2).slice(0, 1500)}`;

    const res = await fetch(`${config.hermesUrl}/v1/chat/completions`, {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        'Authorization': `Bearer ${config.hermesToken}`,
      },
      body: JSON.stringify({
        model:       config.hermesModel,
        messages:    [
          { role: 'system', content: 'You are a Nexus research analyst. Be concise.' },
          { role: 'user',   content: prompt },
        ],
        max_tokens:  400,
        temperature: 0.3,
      }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!res.ok) throw new Error(`Hermes ${res.status}`);
    const data = await res.json();
    const refined = data?.choices?.[0]?.message?.content ?? null;

    if (refined) {
      logger.info('hermes_refined', { length: refined.length });
    }
    return refined;
  } catch (e) {
    logger.warn('hermes_skipped', { error: e?.message });
    return null;
  }
}
