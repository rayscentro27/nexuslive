/**
 * clients/hermes.js — Hermes AI completions client.
 * Used by handlers that need AI synthesis.
 */

import { getEnv } from './supabase.js';

const BASE_URL = getEnv('HERMES_GATEWAY_URL', 'http://localhost:8642');
const TOKEN    = getEnv('HERMES_GATEWAY_TOKEN', '');

export async function complete(prompt, systemPrompt = 'You are a Nexus AI analyst.', maxTokens = 400) {
  const res = await fetch(`${BASE_URL}/v1/chat/completions`, {
    method:  'POST',
    headers: {
      'Content-Type':  'application/json',
      'Authorization': `Bearer ${TOKEN}`,
    },
    body: JSON.stringify({
      model:    'hermes',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user',   content: prompt },
      ],
      max_tokens:  maxTokens,
      temperature: 0.3,
    }),
    signal: AbortSignal.timeout(45_000),
  });

  if (!res.ok) throw new Error(`Hermes ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return data?.choices?.[0]?.message?.content ?? '';
}
