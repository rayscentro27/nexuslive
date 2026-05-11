"""
video_engine.py — Visual asset fetcher for Nova Media.

Fetches relevant stock clips from Pexels by topic keywords,
downloads the best match, and returns the local path for ffmpeg assembly.
Falls back to NVIDIA AI image generation if no suitable clip is found.
"""

import os
import json
import ssl
import subprocess
import urllib.request
from pathlib import Path

_ENV_PATH = Path(__file__).parent.parent / '.env'
if _ENV_PATH.exists():
    with open(_ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, _, v = line.partition('=')
                os.environ.setdefault(k.strip(), v.strip())

PEXELS_KEY = os.environ.get('PEXELS_API_KEY', '')
NVIDIA_KEY = os.environ.get('NVIDIA_API_KEY', '')
CONTENT_OUTPUT_DIR = Path(os.environ.get('CONTENT_OUTPUT_DIR', str(Path.home() / 'nexus-ai' / 'content_employee' / 'output')))

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE

# Keywords to strip from topics for better Pexels results
_STOP_WORDS = {'you', 'your', 'need', 'how', 'why', 'what', 'the', 'a', 'an',
               'to', 'for', 'and', 'or', 'of', 'in', 'is', 'are', 'signs'}

NICHE_KEYWORDS = {
    'credit repair':   ['credit score', 'financial documents', 'money', 'finance', 'banking'],
    'finance':         ['money', 'banking', 'investment', 'financial planning'],
    'real estate':     ['house', 'property', 'keys', 'neighborhood'],
    'health':          ['fitness', 'wellness', 'healthy lifestyle'],
    'business':        ['office', 'entrepreneur', 'team meeting', 'success'],
    'marketing':       ['social media', 'digital marketing', 'laptop', 'analytics'],
}


def _search_pexels_videos(query: str, min_duration: int = 5, max_duration: int = 120) -> list:
    """Search Pexels for videos matching query. Returns list of video dicts."""
    if not PEXELS_KEY:
        return []
    url = f'https://api.pexels.com/videos/search?query={urllib.request.quote(query)}&per_page=10&orientation=portrait'
    r = subprocess.run(
        ['curl', '-s', '-H', f'Authorization: {PEXELS_KEY}', url],
        capture_output=True, text=True, timeout=15
    )
    try:
        data = json.loads(r.stdout)
        videos = data.get('videos', [])
        return [v for v in videos if min_duration <= v.get('duration', 0) <= max_duration]
    except Exception:
        return []


def _best_video_file(video: dict, target_height: int = 1920) -> str:
    """Pick the best quality video file URL from a Pexels video dict."""
    files = video.get('video_files', [])
    # Prefer portrait HD files
    portrait = [f for f in files if f.get('height', 0) >= 720]
    if portrait:
        return sorted(portrait, key=lambda f: f.get('height', 0), reverse=True)[0]['link']
    return files[0]['link'] if files else ''


def _download_video(url: str, dest: Path) -> bool:
    """Download a video file to dest path."""
    cmd = ['curl', '-sL', '-o', str(dest), url]
    r = subprocess.run(cmd, timeout=120, capture_output=True)
    return dest.exists() and dest.stat().st_size > 10000


def _generate_ai_background(topic: str, dest: Path) -> bool:
    """Generate a background image via NVIDIA API and save as JPEG."""
    if not NVIDIA_KEY:
        return False
    import base64
    url = 'https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl'
    prompt = (
        f'Professional cinematic background for a social media video about {topic}. '
        'Soft bokeh, modern, clean aesthetic, suitable as video background. '
        'No text, no people, photorealistic.'
    )
    payload = json.dumps({
        'text_prompts': [{'text': prompt, 'weight': 1}],
        'cfg_scale': 5, 'sampler': 'K_DPM_2_ANCESTRAL',
        'seed': 0, 'steps': 25, 'width': 1080, 'height': 1920,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={
        'Authorization': f'Bearer {NVIDIA_KEY}',
        'Content-Type': 'application/json', 'Accept': 'application/json',
    }, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx) as r:
            data = json.loads(r.read())
        img_b64 = data['artifacts'][0]['base64']
        dest.write_bytes(base64.b64decode(img_b64))
        return dest.exists()
    except Exception:
        return False


def fetch_background(topic: str, niche: str, content_id: str, duration: float = 30.0) -> dict:
    """
    Find and download the best background visual for a video.
    Returns: {ok, type, path, source}
    """
    out_dir = CONTENT_OUTPUT_DIR / content_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build search queries from topic + niche keywords
    topic_words = [w for w in topic.lower().split() if w not in _STOP_WORDS]
    queries = [
        ' '.join(topic_words[:3]),
        NICHE_KEYWORDS.get(niche.lower(), [niche])[0],
        niche,
    ]

    # Try Pexels video — short clips are fine, ffmpeg will loop them
    for query in queries:
        videos = _search_pexels_videos(query, min_duration=5, max_duration=120)
        if videos:
            best_url = _best_video_file(videos[0])
            dest = out_dir / 'background.mp4'
            if best_url and _download_video(best_url, dest):
                return {'ok': True, 'type': 'video', 'path': str(dest), 'source': 'pexels', 'query': query}

    # Fallback: AI-generated image
    dest = out_dir / 'background.jpg'
    if _generate_ai_background(topic, dest):
        return {'ok': True, 'type': 'image', 'path': str(dest), 'source': 'nvidia_ai'}

    return {'ok': False, 'error': 'No background found — will use solid color'}
