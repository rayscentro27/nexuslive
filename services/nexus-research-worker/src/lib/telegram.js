/**
 * lib/telegram.js — Telegram send helper for worker use.
 * Controlled per-call via the `enabled` option.
 * Never throws — Telegram failure must not break job execution.
 */

import { config }       from '../config.js';
import { createLogger } from '../logger.js';

const logger = createLogger('telegram');

export async function sendTelegram(text, { enabled = true } = {}) {
  if (!enabled) return;
  if (!config.telegramToken || !config.telegramChatId) return;
  try {
    const res = await fetch(
      `https://api.telegram.org/bot${config.telegramToken}/sendMessage`,
      {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          chat_id:    config.telegramChatId,
          text,
          parse_mode: 'Markdown',
        }),
        signal: AbortSignal.timeout(10_000),
      }
    );
    if (!res.ok) logger.warn('telegram_non_ok', { status: res.status });
  } catch (e) {
    logger.warn('telegram_failed', { error: e?.message });
  }
}
