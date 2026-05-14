import { createHash } from "crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "fs";
import { resolve } from "path";

const STATE_DIR = resolve(process.cwd(), "reports", "runtime");
const STATE_FILE = resolve(STATE_DIR, "telegram_spam_guard_state.json");

const COOLDOWN_SECONDS = parseInt(process.env.TELEGRAM_NOTIFICATION_COOLDOWN_SECONDS || "900", 10);
const MAX_PER_HOUR = parseInt(process.env.MAX_RESEARCH_NOTIFICATIONS_PER_HOUR || "6", 10);
const DISABLE_SPAM_NOTIFICATIONS = (process.env.DISABLE_RESEARCH_SPAM_NOTIFICATIONS || "false") === "true";

function _loadState() {
  if (!existsSync(STATE_FILE)) return { recent: {}, hourly: [] };
  try {
    const parsed = JSON.parse(readFileSync(STATE_FILE, "utf8"));
    return {
      recent: parsed?.recent && typeof parsed.recent === "object" ? parsed.recent : {},
      hourly: Array.isArray(parsed?.hourly) ? parsed.hourly : [],
    };
  } catch {
    return { recent: {}, hourly: [] };
  }
}

function _saveState(state) {
  mkdirSync(STATE_DIR, { recursive: true });
  writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

function _hash(eventType, text) {
  return createHash("sha256").update(`${eventType}::${String(text || "").trim().toLowerCase().slice(0, 400)}`).digest("hex").slice(0, 24);
}

export function shouldSendTelegram(eventType, text) {
  if (DISABLE_SPAM_NOTIFICATIONS) {
    return { ok: false, reason: "spam_notifications_disabled" };
  }
  const nowSec = Math.floor(Date.now() / 1000);
  const state = _loadState();
  state.hourly = state.hourly.filter((ts) => nowSec - Number(ts || 0) < 3600);
  if (state.hourly.length >= MAX_PER_HOUR) {
    _saveState(state);
    return { ok: false, reason: "hourly_cap" };
  }

  const digest = _hash(eventType, text);
  const last = Number(state.recent[digest] || 0);
  if (last > 0 && nowSec - last < Math.max(60, COOLDOWN_SECONDS)) {
    _saveState(state);
    return { ok: false, reason: "cooldown_duplicate" };
  }

  state.recent[digest] = nowSec;
  state.hourly.push(nowSec);
  _saveState(state);
  return { ok: true, reason: "ok", digest };
}
