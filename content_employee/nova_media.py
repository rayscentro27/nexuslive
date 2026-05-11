"""
nova_media.py — Nova Media worker identity and batch runner.

Nova Media is the Mac Mini content employee.
Role: content research, scripting, narration, asset manifests.
Output: structured Supabase records + local audio/asset files.
Default: everything goes to 'needs_review' — Nova never auto-publishes.

Run:
  python3 -m content_employee.nova_media --type instagram_reel --topic "3 signs you need a credit repair plan" --niche "credit repair"
  python3 -m content_employee.nova_media --batch batch.json
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
import lib.ssl_fix  # noqa — fixes HTTPS on macOS Python 3.14

sys.path.insert(0, str(Path(__file__).parent.parent))

_env_path = Path(__file__).parent.parent / '.env'
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())

from content_employee.content_pipeline import run_pipeline, stage_approve
from content_employee.tooling_adapter import capabilities

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [NOVA_MEDIA] %(levelname)s %(message)s',
)
logger = logging.getLogger('NovaMed')

# ── Identity ──────────────────────────────────────────────────────────────────

NOVA_PROFILE = {
    'name':    'Nova Media',
    'role':    'Content Employee',
    'node':    'Mac Mini',
    'mission': (
        'Produce platform-ready short-form and long-form content scripts, '
        'narration audio, and structured asset manifests for Instagram, TikTok, '
        'and YouTube. Never auto-publish. All outputs go to review first.'
    ),
    'cost_model':  'free-first (OpenClaw + macOS say + yt-dlp)',
    'outputs':     ['Supabase records', 'local audio files', 'asset manifests'],
    'gated_steps': ['publish'],
}

VALID_TYPES = ['instagram_reel', 'tiktok_short', 'youtube_short', 'youtube_training']


# ── Telegram alert ────────────────────────────────────────────────────────────

def _send_telegram(message: str):
    import urllib.request, urllib.parse
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        return
    try:
        payload = json.dumps({'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


# ── Single content run ────────────────────────────────────────────────────────

def produce(
    topic: str,
    content_type: str,
    niche: str,
    platforms: list = None,
    voice: str = 'Samantha',
) -> dict:
    """
    Produce one content piece end-to-end.
    Returns pipeline result dict.
    """
    if content_type not in VALID_TYPES:
        return {'ok': False, 'error': f'Invalid content_type: {content_type}. Valid: {VALID_TYPES}'}

    if platforms is None:
        platforms = _default_platforms(content_type)

    logger.info(f'Nova Media starting: {content_type} | "{topic}" | niche={niche}')

    caps = capabilities()
    if caps['missing']:
        logger.warning(f'Missing optional tools (non-blocking): {caps["missing"]}')

    result = run_pipeline(
        topic=topic,
        content_type=content_type,
        niche=niche,
        target_platforms=platforms,
        tts_voice=voice,
        requested_by='nova_media',
    )

    content_id = result.get('content_id', '?')
    audio_ok   = result.get('audio_ready', False)
    manual_asm = result.get('manual_assembly_required', True)

    msg = (
        f'<b>Nova Media — Content Ready for Review</b>\n'
        f'<b>ID:</b> <code>{content_id}</code>\n'
        f'<b>Type:</b> {content_type}\n'
        f'<b>Topic:</b> {topic}\n'
        f'<b>Niche:</b> {niche}\n'
        f'<b>Audio:</b> {"✅" if audio_ok else "❌ manual"}\n'
        f'<b>Assembly:</b> {"⚠️ manual (install ffmpeg)" if manual_asm else "✅"}\n'
        f'<b>Status:</b> needs_review — awaiting your approval'
    )
    _send_telegram(msg)

    logger.info(
        f'Pipeline complete | content_id={content_id} | '
        f'audio={audio_ok} | manual_assembly={manual_asm}'
    )
    return result


def _default_platforms(content_type: str) -> list:
    return {
        'instagram_reel': ['instagram'],
        'tiktok_short':   ['tiktok'],
        'youtube_short':  ['youtube'],
        'youtube_training': ['youtube'],
    }.get(content_type, ['instagram'])


# ── Batch run ────────────────────────────────────────────────────────────────

def run_batch(batch_path: str) -> list:
    """
    Run multiple content requests from a JSON file.
    File format:
      [
        {"topic": "...", "content_type": "instagram_reel", "niche": "..."},
        ...
      ]
    """
    with open(batch_path) as f:
        items = json.load(f)

    results = []
    for i, item in enumerate(items):
        logger.info(f'Batch item {i+1}/{len(items)}: {item.get("topic","?")}')
        r = produce(
            topic=item['topic'],
            content_type=item.get('content_type', 'instagram_reel'),
            niche=item.get('niche', 'general'),
            platforms=item.get('platforms'),
            voice=item.get('voice', 'Samantha'),
        )
        results.append({'input': item, 'result': r})

    return results


# ── Capabilities report ──────────────────────────────────────────────────────

def report_capabilities():
    caps = capabilities()
    print('\n=== Nova Media — Tooling Capabilities ===')
    for k, v in caps.items():
        if k == 'missing':
            continue
        icon = '✅' if v else '❌'
        print(f'  {icon}  {k}')
    if caps['missing']:
        print(f'\nMissing tools: {", ".join(caps["missing"])}')
        print('To enable full assembly: brew install ffmpeg')
        print('To enable cloud TTS:     pip install gtts')
    print()


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Nova Media — content production worker')
    parser.add_argument('--topic',   help='Content topic')
    parser.add_argument('--type',    dest='content_type', choices=VALID_TYPES, default='instagram_reel')
    parser.add_argument('--niche',   default='financial education')
    parser.add_argument('--voice',   default='Samantha', help='macOS say voice')
    parser.add_argument('--batch',   help='Path to batch JSON file')
    parser.add_argument('--caps',    action='store_true', help='Print tooling capabilities')
    parser.add_argument('--approve', help='Approve a content_id for publish-ready')

    args = parser.parse_args()

    if args.caps:
        report_capabilities()
        return

    if args.approve:
        r = stage_approve(args.approve, approved_by='founder')
        print(json.dumps(r, indent=2))
        return

    if args.batch:
        results = run_batch(args.batch)
        print(json.dumps(results, indent=2, default=str))
        return

    if not args.topic:
        parser.error('--topic is required (or use --batch or --caps or --approve)')

    result = produce(
        topic=args.topic,
        content_type=args.content_type,
        niche=args.niche,
        voice=args.voice,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
