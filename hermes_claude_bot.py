#!/usr/bin/env python3
"""
Hermes Claude Bot — two-way Telegram bot powered by Groq/Llama 3
Supports AI chat + deploy/shell commands
"""

import os
import json
import time
import logging
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

from lib.telegram_role_config import get_chat_config, get_ops_config, get_reports_config, hermes_chat_enabled
from lib.model_router import get_provider, ModelRoutingError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('hermes_claude_bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('HermesClaude')

CHAT_CONFIG = get_chat_config()
BOT_TOKEN = CHAT_CONFIG.token
ALLOWED_CHAT_ID = str(CHAT_CONFIG.chat_id or '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_BASE_URL = os.getenv('GROQ_BASE_URL', 'https://api.groq.com/openai/v1')
GROQ_MODEL = os.getenv('GROQ_MODEL', '')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'deepseek/deepseek-chat')
MODEL_CONTEXT_LENGTH = int(os.getenv('MODEL_CONTEXT_LENGTH', '128000'))

TG_API = f'https://api.telegram.org/bot{BOT_TOKEN}'

SYSTEM_PROMPT = """You are Hermes, the AI Chief of Staff for Raymond's Nexus AI system.

Primary behavior:
- Be conversational for natural chat (greetings, quick questions, follow-ups).
- Use structured operational briefings only when asked for status/health/summary/metrics.
- Keep replies concise and practical.

If the user asks an operational question, include clear next action.
If the user sends casual conversation (e.g., 'good evening'), reply naturally first.

Do not invent data. If system state is unknown, say so and suggest the exact check command.

Nexus context:
- Trading engine: live OANDA forex trades, auto-trading enabled
- Research pipeline: YouTube/web research -> signals -> strategy candidates
- Credit/funding: helping users become fundable (B2B SaaS)
- Workers: orchestrator, research worker, monitoring, coordination, grant worker, strategy lab
- CEO mode: daily/weekly briefings, lead tracking, revenue tracking, alert engine"""

DEPLOY_TARGETS = {
    'nexuslive': {
        'dir': os.path.expanduser('~/nexuslive'),
        'build': 'npm run build',
        'deploy': 'npx netlify-cli deploy --prod --dir=dist',
        'desc': 'NexusLive frontend (Netlify)'
    },
    'oracle-api': {
        'dir': os.path.expanduser('~/nexus-oracle-api'),
        'build': 'npm run build',
        'deploy': None,
        'desc': 'Nexus Oracle API'
    },
    'nexus-ai': {
        'dir': os.path.expanduser('~/nexus-ai'),
        'build': None,
        'deploy': 'pm2 restart nexus-ai 2>/dev/null || python3 dashboard.py &',
        'desc': 'Nexus AI backend'
    },
}

conversation_history = []
_ROUTER_ERROR_WINDOW_SECONDS = int(os.getenv("HERMES_ROUTER_ERROR_WINDOW_SECONDS", "300"))
_ROUTER_ERROR_MAX_ALERTS = int(os.getenv("HERMES_ROUTER_ERROR_MAX_ALERTS", "1"))
_ROUTER_COOLDOWN_SECONDS = int(os.getenv("HERMES_ROUTER_COOLDOWN_SECONDS", "300"))
_ROUTER_MAX_ATTEMPTS = int(os.getenv("HERMES_ROUTER_MAX_ATTEMPTS", "2"))
_router_error_state: dict[str, dict[str, float | int]] = {}


def _task_for_chat(text: str) -> tuple[str, int]:
    t = text.lower().strip()
    if any(k in t for k in ("summarize today", "what happened today", "executive summary", "next best move")):
        return "premium_reasoning", 64000
    if any(k in t for k in ("analyze", "full log", "deep dive", "plan", "architecture")):
        return "planning", 64000
    if any(k in t for k in ("urgent", "critical", "incident", "security", "payment failure")):
        return "critical", 64000
    return "telegram_reply", 4000


def _should_alert_router_error(error_key: str) -> bool:
    now = time.time()
    state = _router_error_state.get(error_key) or {"count": 0, "window_start": now, "cooldown_until": 0.0}
    if now < float(state.get("cooldown_until", 0.0)):
        return False
    if now - float(state.get("window_start", now)) > _ROUTER_ERROR_WINDOW_SECONDS:
        state = {"count": 0, "window_start": now, "cooldown_until": 0.0}
    state["count"] = int(state.get("count", 0)) + 1
    if int(state["count"]) > _ROUTER_ERROR_MAX_ALERTS:
        state["cooldown_until"] = now + _ROUTER_COOLDOWN_SECONDS
        _router_error_state[error_key] = state
        return False
    _router_error_state[error_key] = state
    return True


def _router_admin_message(err: Exception) -> str:
    key = f"{type(err).__name__}:{str(err)[:120]}"
    if _should_alert_router_error(key):
        return "Hermes paused this task because the selected model context is too small. Send /reset once after config is fixed."
    return ""


def _trim_history_for_context(history: list[dict], budget_chars: int) -> list[dict]:
    kept: list[dict] = []
    total = 0
    for msg in reversed(history):
        content = str(msg.get("content") or "")
        if not content:
            continue
        cost = len(content)
        if kept and total + cost > budget_chars:
            break
        kept.append({"role": msg.get("role", "user"), "content": content[:3000]})
        total += min(cost, 3000)
    return list(reversed(kept))


def tg_get(method, params=None):
    r = requests.get(f'{TG_API}/{method}', params=params, timeout=10)
    return r.json()


def tg_post(method, payload):
    r = requests.post(f'{TG_API}/{method}', json=payload, timeout=10)
    return r.json()


def send_message(chat_id, text):
    tg_post('sendMessage', {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    })


def send_typing(chat_id):
    tg_post('sendChatAction', {'chat_id': chat_id, 'action': 'typing'})


def ask_groq(user_message, append_user: bool = True):
    if append_user:
        conversation_history.append({'role': 'user', 'content': user_message})

    # Keep last 20 messages to avoid token limits
    history = conversation_history[-20:]

    headers = {
        'Authorization': f'Bearer {GROQ_API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': GROQ_MODEL,
        'messages': [{'role': 'system', 'content': SYSTEM_PROMPT}] + history,
        'max_tokens': 1024,
        'temperature': 0.7
    }

    r = requests.post(f'{GROQ_BASE_URL}/chat/completions', headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    reply = r.json()['choices'][0]['message']['content']
    conversation_history.append({'role': 'assistant', 'content': reply})
    return reply


def ask_via_router(user_message):
    """Route Hermes chat through the model router; fall back to Groq path on failure."""
    conversation_history.append({'role': 'user', 'content': user_message})
    task_type, required_ctx = _task_for_chat(user_message)
    try:
        provider = get_provider(task_type=task_type, model_source='auto', min_context=required_ctx)
    except ModelRoutingError as e:
        log.error("Model routing error: %s", e)
        admin_msg = _router_admin_message(e)
        if admin_msg:
            return admin_msg
        return "Hermes is temporarily suppressing repeated model-configuration alerts. Please check model routing config."

    # Safety guard: never allow known 10K model for main Hermes workflows
    if (
        task_type in {"premium_reasoning", "planning", "critical", "funding_strategy", "credit_analysis"}
        and provider.get('name') == 'groq'
        and str(provider.get('model') or '') == 'llama-3.3-70b-versatile'
        and int(provider.get('max_context') or MODEL_CONTEXT_LENGTH) < 64000
    ):
        msg = _router_admin_message(ValueError("groq model context too small for main workflow"))
        return msg or "Hermes is temporarily suppressing repeated model-configuration alerts."

    provider_ctx = int(provider.get('max_context') or required_ctx)
    budget = max(1200, min(provider_ctx // 2, 24000))
    history = _trim_history_for_context(conversation_history, budget)

    if provider.get('format') != 'openai':
        return ask_groq(user_message, append_user=False)

    url = provider.get('url', '').rstrip('/')
    if not url:
        return ask_groq(user_message, append_user=False)
    if not url.endswith('/chat/completions'):
        url = f"{url}/chat/completions"

    headers = {'Content-Type': 'application/json'}
    key = provider.get('key', '')
    if key:
        headers['Authorization'] = f'Bearer {key}'

    payload = {
        'model': provider.get('model', GROQ_MODEL),
        'messages': [{'role': 'system', 'content': SYSTEM_PROMPT}] + history,
        'max_tokens': 1024,
        'temperature': 0.7,
    }

    attempts = 0
    last_err: Exception | None = None
    while attempts < _ROUTER_MAX_ATTEMPTS:
        attempts += 1
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=45)
            r.raise_for_status()
            reply = r.json()['choices'][0]['message']['content']
            conversation_history.append({'role': 'assistant', 'content': reply})
            return reply
        except ValueError as e:
            log.error("Non-retriable model config/value error: %s", e)
            admin_msg = _router_admin_message(e)
            return admin_msg or "Hermes paused this task due to model configuration constraints."
        except Exception as e:
            last_err = e
            if attempts >= _ROUTER_MAX_ATTEMPTS:
                break
            time.sleep(1)

    try:
        msg = str(last_err or "").lower()
        if any(k in msg for k in ('context', 'token', 'length', 'maximum')):
            log.warning('Context too large for provider=%s; retrying with compact history', provider.get('name'))
            compact_history = _trim_history_for_context(conversation_history, 2000)
            payload['messages'] = [{'role': 'system', 'content': SYSTEM_PROMPT}] + compact_history
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=35)
                r.raise_for_status()
                reply = r.json()['choices'][0]['message']['content']
                conversation_history.append({'role': 'assistant', 'content': reply})
                return reply
            except Exception as compact_err:
                log.warning('Compact retry failed (%s): %s', provider.get('name'), compact_err)

        log.warning(f'Router model call failed ({provider.get("name")}): {last_err}; falling back to Groq')
        try:
            return ask_groq(user_message, append_user=False)
        except Exception:
            return (
                "I can still help, but model capacity is tight right now. "
                "Try a shorter question or ask for a brief status summary first."
            )
    except Exception:
        return "Hermes paused this task because the selected model context is too small."


def run_shell(cmd, cwd=None, timeout=120):
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd,
            capture_output=True, text=True, timeout=timeout
        )
        out = (result.stdout + result.stderr).strip()
        return out[-3000:] if len(out) > 3000 else out, result.returncode
    except subprocess.TimeoutExpired:
        return '⏱ Command timed out', 1
    except Exception as e:
        return str(e), 1


def handle_deploy(chat_id, args):
    if not args:
        targets = '\n'.join([f'  `{k}` — {v["desc"]}' for k, v in DEPLOY_TARGETS.items()])
        send_message(chat_id, f'*Available deploy targets:*\n{targets}\n\nUsage: `/deploy <target>`')
        return

    target = args[0].lower()
    if target not in DEPLOY_TARGETS:
        send_message(chat_id, f'❌ Unknown target: `{target}`\nOptions: {", ".join(DEPLOY_TARGETS.keys())}')
        return

    cfg = DEPLOY_TARGETS[target]
    send_message(chat_id, f'🚀 Deploying *{target}*...')

    if cfg.get('build'):
        send_typing(chat_id)
        send_message(chat_id, f'📦 Building...')
        out, code = run_shell(cfg['build'], cwd=cfg['dir'])
        if code != 0:
            send_message(chat_id, f'❌ Build failed:\n```\n{out}\n```')
            return
        send_message(chat_id, f'✅ Build success')

    if cfg.get('deploy'):
        send_typing(chat_id)
        send_message(chat_id, f'☁️ Deploying...')
        out, code = run_shell(cfg['deploy'], cwd=cfg['dir'])
        status = '✅ Deployed!' if code == 0 else '❌ Deploy failed'
        send_message(chat_id, f'{status}\n```\n{out}\n```')
    else:
        send_message(chat_id, f'ℹ️ No deploy step configured for `{target}`. Build complete.')


def handle_run(chat_id, args):
    if not args:
        send_message(chat_id, 'Usage: `/run <shell command>`')
        return
    cmd = ' '.join(args)
    send_message(chat_id, f'⚙️ Running: `{cmd}`')
    send_typing(chat_id)
    out, code = run_shell(cmd, cwd=os.path.expanduser('~'))
    status = '✅' if code == 0 else f'❌ (exit {code})'
    output = out if out else '(no output)'
    send_message(chat_id, f'{status}\n```\n{output}\n```')


def handle_message(msg):
    chat_id = str(msg['chat']['id'])
    text = msg.get('text', '').strip()

    if not text:
        return

    # Security: only respond to your chat
    if ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID:
        log.warning(f'Ignored message from unauthorized chat_id: {chat_id}')
        return

    log.info(f'User: {text}')
    parts = text.split()
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == '/start':
        send_message(chat_id, '👋 *Hermes AI is online.*\n\n*Commands:*\n`/deploy <target>` — deploy a service\n`/run <cmd>` — run a shell command\n`/status` — bot status\n`/clear` — clear chat history\n\nOr just chat — I\'m powered by Groq/Llama 3.')
        return

    if cmd == '/clear':
        conversation_history.clear()
        send_message(chat_id, '🧹 Conversation history cleared.')
        return

    if cmd == '/status':
        send_message(chat_id, f'✅ *Hermes Claude Bot*\nModel: `{GROQ_MODEL}`\nMessages in context: {len(conversation_history)}\nDeploy targets: {", ".join(DEPLOY_TARGETS.keys())}')
        return

    if cmd == '/deploy':
        handle_deploy(chat_id, args)
        return

    if cmd == '/run':
        handle_run(chat_id, args)
        return

    send_typing(chat_id)

    try:
        reply = ask_via_router(text)
        log.info(f'Assistant: {reply[:80]}...')
        send_message(chat_id, reply)
    except Exception as e:
        log.error(f'Groq error: {e}')
        send_message(chat_id, f'⚠️ Error: {str(e)}')


def run():
    if not hermes_chat_enabled():
        log.warning('Hermes chat bot disabled by default; set ENABLE_HERMES_CHAT_BOT=true to enable.')
        return

    ops = get_ops_config()
    reports = get_reports_config()
    if not BOT_TOKEN:
        log.error('TELEGRAM_HERMES_CHAT_BOT_TOKEN is required when Hermes chat bot is enabled')
        return
    if BOT_TOKEN == ops.token:
        log.error('Hermes chat bot token must not match TELEGRAM_OPS_BOT_TOKEN')
        return
    if BOT_TOKEN == reports.token:
        log.error('Hermes chat bot token must not match TELEGRAM_REPORTS_BOT_TOKEN')
        return

    log.info(
        'Starting Hermes Claude Bot | groq_model=%s | openrouter_model=%s | model_context_length=%s | min_main_ctx=64000',
        GROQ_MODEL or '(unset)',
        OPENROUTER_MODEL,
        MODEL_CONTEXT_LENGTH,
    )

    # Verify bot
    me = tg_get('getMe')
    if not me.get('ok'):
        log.error(f'Bot token invalid: {me}')
        return
    log.info(f"Connected as @{me['result']['username']}")

    offset = None
    while True:
        try:
            params = {'timeout': 30, 'allowed_updates': ['message']}
            if offset:
                params['offset'] = offset

            updates = tg_get('getUpdates', params)

            if not updates.get('ok'):
                log.error(f'getUpdates failed: {updates}')
                time.sleep(5)
                continue

            for update in updates.get('result', []):
                offset = update['update_id'] + 1
                if 'message' in update:
                    handle_message(update['message'])

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            log.error(f'Poll error: {e}')
            time.sleep(5)


if __name__ == '__main__':
    run()
