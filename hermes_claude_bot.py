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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('hermes_claude_bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('HermesClaude')

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ALLOWED_CHAT_ID = str(os.getenv('TELEGRAM_CHAT_ID', ''))
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_BASE_URL = os.getenv('GROQ_BASE_URL', 'https://api.groq.com/openai/v1')
GROQ_MODEL = 'llama-3.3-70b-versatile'

TG_API = f'https://api.telegram.org/bot{BOT_TOKEN}'

SYSTEM_PROMPT = """You are Claude, an AI assistant connected to Raymond's Nexus AI system via Telegram.
You are helpful, concise, and aware that responses are read on a mobile device. Keep answers clear and practical.
You have context about the Nexus project — an AI agent system for trading, research, and business automation."""

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


def ask_groq(user_message):
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
        reply = ask_groq(text)
        log.info(f'Assistant: {reply[:80]}...')
        send_message(chat_id, reply)
    except Exception as e:
        log.error(f'Groq error: {e}')
        send_message(chat_id, f'⚠️ Error: {str(e)}')


def run():
    log.info(f'Starting Hermes Claude Bot (model: {GROQ_MODEL})')

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
