"""
publisher.py — Nova Media social publisher.

Publishes approved content to Facebook Page and Instagram.
Never called automatically — only after human approval via stage_approve().

Usage:
    from content_employee.publisher import publish_content
    result = publish_content(content_id, platforms=['facebook', 'instagram'])
"""

import os
import json
import ssl
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

_ENV_PATH = Path(__file__).parent.parent / '.env'
if _ENV_PATH.exists():
    with open(_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())

GRAPH_BASE = 'https://graph.facebook.com/v19.0'
PAGE_ID = os.environ.get('META_PAGE_ID', '')
PAGE_TOKEN = os.environ.get('META_PAGE_ACCESS_TOKEN', '')
IG_ACCOUNT_ID = os.environ.get('META_INSTAGRAM_ACCOUNT_ID', '')
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_SERVICE_ROLE_KEY', '') or os.environ.get('SUPABASE_KEY', '')
CONTENT_OUTPUT_DIR = Path(os.environ.get('CONTENT_OUTPUT_DIR', str(Path.home() / 'nexus-ai' / 'content_employee' / 'output')))

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _api(method: str, path: str, data: dict = None, base: str = GRAPH_BASE) -> dict:
    url = f'{base}/{path}'
    payload = json.dumps(data).encode() if data else None
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx) as r:
            return {'ok': True, 'data': json.loads(r.read())}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {'ok': False, 'error': f'HTTP {e.code}: {body[:300]}'}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


# ── Supabase Storage upload ───────────────────────────────────────────────────

def upload_to_supabase(local_path: str, remote_name: str, bucket: str = 'content-media') -> dict:
    """Upload a file to Supabase Storage and return the public URL."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {'ok': False, 'error': 'Supabase credentials not set'}

    path = Path(local_path)
    if not path.exists():
        return {'ok': False, 'error': f'File not found: {local_path}'}

    content_type = 'video/mp4' if local_path.endswith('.mp4') else 'application/octet-stream'
    upload_url = f'{SUPABASE_URL}/storage/v1/object/{bucket}/{remote_name}'

    cmd = [
        'curl', '-s', '-X', 'POST', upload_url,
        '-H', f'apikey: {SUPABASE_KEY}',
        '-H', f'Authorization: Bearer {SUPABASE_KEY}',
        '-H', f'Content-Type: {content_type}',
        '-H', 'x-upsert: true',
        '--data-binary', f'@{local_path}',
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    try:
        data = json.loads(r.stdout)
        if 'Key' in data or 'path' in data or data.get('Id'):
            public_url = f'{SUPABASE_URL}/storage/v1/object/public/{bucket}/{remote_name}'
            return {'ok': True, 'url': public_url}
        return {'ok': False, 'error': r.stdout[:300]}
    except Exception:
        return {'ok': False, 'error': f'Upload failed: {r.stdout[:200]}'}


# ── Facebook publishing ───────────────────────────────────────────────────────

def post_to_facebook(content_id: str, caption: str, video_path: str = None) -> dict:
    """Post a video or text update to the Facebook Page."""
    if not PAGE_ID or not PAGE_TOKEN:
        return {'ok': False, 'error': 'META_PAGE_ID or META_PAGE_ACCESS_TOKEN not set'}

    if video_path and Path(video_path).exists():
        cmd = [
            'curl', '-s', '-X', 'POST',
            f'{GRAPH_BASE}/{PAGE_ID}/videos',
            '-F', f'access_token={PAGE_TOKEN}',
            '-F', f'description={caption}',
            '-F', f'file=@{video_path}',
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        try:
            data = json.loads(r.stdout)
            if 'id' in data:
                return {'ok': True, 'platform': 'facebook', 'post_id': data['id']}
            return {'ok': False, 'platform': 'facebook', 'error': r.stdout[:300]}
        except Exception:
            return {'ok': False, 'platform': 'facebook', 'error': r.stdout[:200]}
    else:
        result = _api('POST', f'{PAGE_ID}/feed?access_token={PAGE_TOKEN}', {'message': caption})
        if result['ok'] and 'id' in result.get('data', {}):
            return {'ok': True, 'platform': 'facebook', 'post_id': result['data']['id']}
        return {'ok': False, 'platform': 'facebook', 'error': result.get('error')}


# ── Instagram publishing ──────────────────────────────────────────────────────

def post_to_instagram(content_id: str, caption: str, video_path: str = None) -> dict:
    """Post a Reel to Instagram. Uploads video to Supabase first to get a public URL."""
    if not IG_ACCOUNT_ID or not PAGE_TOKEN:
        return {'ok': False, 'error': 'META_INSTAGRAM_ACCOUNT_ID or META_PAGE_ACCESS_TOKEN not set'}

    if not video_path or not Path(video_path).exists():
        return {'ok': False, 'error': 'Video file required for Instagram Reels'}

    # Step 1: Upload to Supabase to get public URL
    remote_name = f'{content_id}/reel.mp4'
    upload = upload_to_supabase(video_path, remote_name)
    if not upload['ok']:
        return {'ok': False, 'platform': 'instagram', 'error': f'Storage upload failed: {upload["error"]}'}

    video_url = upload['url']

    # Step 2: Create Instagram media container
    container = _api('POST', f'{IG_ACCOUNT_ID}/media?access_token={PAGE_TOKEN}', {
        'media_type': 'REELS',
        'video_url': video_url,
        'caption': caption,
    })
    if not container['ok']:
        return {'ok': False, 'platform': 'instagram', 'error': f'Container creation failed: {container["error"]}'}

    creation_id = container['data'].get('id')
    if not creation_id:
        return {'ok': False, 'platform': 'instagram', 'error': 'No creation_id returned'}

    # Step 3: Wait for video to process then publish
    for attempt in range(12):
        time.sleep(10)
        status = _api('GET', f'{creation_id}?fields=status_code&access_token={PAGE_TOKEN}')
        code = status.get('data', {}).get('status_code', '')
        if code == 'FINISHED':
            break
        if code == 'ERROR':
            return {'ok': False, 'platform': 'instagram', 'error': f'Instagram video processing failed. Status: {status.get("data")}'}

    publish = _api('POST', f'{IG_ACCOUNT_ID}/media_publish?access_token={PAGE_TOKEN}', {
        'creation_id': creation_id,
    })
    if publish['ok'] and 'id' in publish.get('data', {}):
        return {'ok': True, 'platform': 'instagram', 'post_id': publish['data']['id'], 'video_url': video_url}
    return {'ok': False, 'platform': 'instagram', 'error': publish.get('error')}


# ── Main publish entry point ──────────────────────────────────────────────────

def publish_content(content_id: str, platforms: list = None) -> dict:
    """
    Publish approved content to specified platforms.
    Only call after human approval — never auto-publish.
    """
    if platforms is None:
        platforms = ['facebook', 'instagram']

    out_dir = CONTENT_OUTPUT_DIR / content_id
    video_path = str(out_dir / 'final.mp4') if (out_dir / 'final.mp4').exists() else None

    script_path = out_dir / 'script.txt'
    caption = script_path.read_text().strip() if script_path.exists() else f'Content ID: {content_id}'

    results = {}

    if 'facebook' in platforms:
        results['facebook'] = post_to_facebook(content_id, caption, video_path)

    if 'instagram' in platforms:
        results['instagram'] = post_to_instagram(content_id, caption, video_path)

    return results


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python3 -m content_employee.publisher <content_id> [facebook,instagram]')
        sys.exit(1)
    cid = sys.argv[1]
    plats = sys.argv[2].split(',') if len(sys.argv) > 2 else ['facebook', 'instagram']
    result = publish_content(cid, plats)
    print(json.dumps(result, indent=2))
