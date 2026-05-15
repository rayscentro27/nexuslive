/**
 * clients/telegram.js — Telegram alert sender.
 */

import { getEnv } from './supabase.js';

const TOKEN   = getEnv('TELEGRAM_BOT_TOKEN', '');
const CHAT_ID = getEnv('TELEGRAM_CHAT_ID', '');

export async function notify(text) {
  if (!TOKEN || !CHAT_ID) return;
  if ((process.env.TELEGRAM_AUTO_REPORTS_ENABLED || 'false') !== 'true') {
    console.log('telegram_policy denied=true reason=manual_only_default');
    return;
  }
  try {
    await fetch(`https://api.telegram.org/bot${TOKEN}/sendMessage`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ chat_id: CHAT_ID, text, parse_mode: 'Markdown' }),
      signal:  AbortSignal.timeout(10_000),
    });
  } catch { /* non-critical */ }
}
