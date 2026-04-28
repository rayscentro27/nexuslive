"""
tooling_adapter.py — Provider-agnostic local tooling abstraction for Nova Media.

Wraps local free/built-in tools so the rest of the pipeline does not care
which specific tool is installed.  Add new providers here; the pipeline never
changes.

Available providers (detected at import time):
  transcript:   yt-dlp subtitle extraction  (free, installed)
  tts:          macOS say                    (free, built-in)
  tts_alt:      gTTS                         (free, needs install: pip install gtts)
  video_dl:     yt-dlp                       (free, installed)
  image:        NOT available (ffmpeg/Pillow not installed)
  assembly:     NOT available (ffmpeg not installed)

When a provider is missing, functions return a structured 'unavailable' result
rather than raising — callers can decide to skip, queue for manual review, or
wait for the tool to be installed.
"""

import os
import shutil
import subprocess
import urllib.request as _ureq
import json
from pathlib import Path
from typing import Optional
import lib.ssl_fix  # noqa — fixes HTTPS on macOS Python 3.14


# ── Provider capability detection ────────────────────────────────────────────

def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


TOOLS = {
    'yt_dlp':   _has('yt-dlp'),
    'ffmpeg':   _has('ffmpeg'),
    'ffprobe':  _has('ffprobe'),
    'say':      Path('/usr/bin/say').exists(),
}

try:
    import gtts as _gtts
    TOOLS['gtts'] = True
except ImportError:
    TOOLS['gtts'] = False

try:
    from PIL import Image as _PILImage
    TOOLS['pillow'] = True
except ImportError:
    TOOLS['pillow'] = False


def capabilities() -> dict:
    """Return current tool availability map."""
    return {
        **TOOLS,
        'transcript_extraction': TOOLS['yt_dlp'],
        'tts_local':             TOOLS['say'],
        'tts_cloud':             TOOLS['gtts'],
        'video_download':        TOOLS['yt_dlp'],
        'video_assembly':        TOOLS['ffmpeg'],
        'image_processing':      TOOLS['pillow'],
        'missing': [k for k, v in TOOLS.items() if not v],
    }


# ── Transcript extraction ─────────────────────────────────────────────────────

def extract_transcript_from_url(url: str, output_dir: str, lang: str = 'en') -> dict:
    """
    Download auto-generated or manual subtitles from a YouTube URL using yt-dlp.
    Returns: {ok, path, format, error}
    """
    if not TOOLS['yt_dlp']:
        return {'ok': False, 'error': 'yt-dlp not installed'}

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        'yt-dlp',
        '--write-auto-sub', '--sub-lang', lang,
        '--skip-download',
        '--sub-format', 'vtt',
        '-o', str(output_dir / '%(title)s.%(ext)s'),
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        vtt_files = list(output_dir.glob(f'*.{lang}.vtt'))
        if vtt_files:
            return {'ok': True, 'path': str(vtt_files[0]), 'format': 'vtt'}
        return {'ok': False, 'error': result.stderr[:300] or 'no_vtt_produced'}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'yt-dlp timeout'}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


def vtt_to_text(vtt_path: str) -> str:
    """Convert a .vtt subtitle file to clean plain text."""
    lines = []
    skip = True
    with open(vtt_path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('WEBVTT'):
                continue
            if '-->' in line:
                skip = False
                continue
            if not line:
                skip = True
                continue
            if not skip and line:
                lines.append(line)
    # Deduplicate consecutive repeated lines (yt-dlp rolls captions)
    deduped = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return ' '.join(deduped)


# ── Text-to-Speech ────────────────────────────────────────────────────────────

def tts_to_file(text: str, output_path: str, voice: str = 'Samantha') -> dict:
    """
    Convert text to speech audio file.
    Tries: macOS say → gTTS → unavailable.
    Returns: {ok, path, provider, error}
    """
    output_path = str(output_path)

    # macOS say (built-in, free, offline)
    if TOOLS['say']:
        try:
            cmd = ['say', '-v', voice, '-o', output_path, '--data-format=aiff', text]
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
            return {'ok': True, 'path': output_path, 'provider': 'macos_say'}
        except Exception as e:
            pass  # fall through to next provider

    # gTTS (free, needs network, writes mp3)
    if TOOLS['gtts']:
        try:
            import gtts as _gtts
            mp3_path = output_path.replace('.aiff', '.mp3').replace('.wav', '.mp3')
            if not mp3_path.endswith('.mp3'):
                mp3_path += '.mp3'
            tts = _gtts.gTTS(text=text, lang='en')
            tts.save(mp3_path)
            return {'ok': True, 'path': mp3_path, 'provider': 'gtts'}
        except Exception as e:
            return {'ok': False, 'error': f'gtts: {str(e)[:150]}', 'provider': 'gtts'}

    return {
        'ok': False,
        'error': 'No TTS provider available. Install: pip install gtts',
        'provider': None,
        'install_hint': 'pip install gtts',
    }


# ── Video download ────────────────────────────────────────────────────────────

def download_video(url: str, output_dir: str, quality: str = '720') -> dict:
    """
    Download a video for local editing or reference.
    Returns: {ok, path, error}
    """
    if not TOOLS['yt_dlp']:
        return {'ok': False, 'error': 'yt-dlp not installed'}

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        'yt-dlp',
        '-f', f'bestvideo[height<={quality}]+bestaudio/best[height<={quality}]',
        '-o', str(output_dir / '%(title)s.%(ext)s'),
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        files = [f for f in output_dir.iterdir() if f.is_file() and f.suffix in ('.mp4', '.webm', '.mkv')]
        if files:
            return {'ok': True, 'path': str(max(files, key=lambda f: f.stat().st_mtime))}
        return {'ok': False, 'error': result.stderr[:300] or 'no_video_file_produced'}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'error': 'yt-dlp timeout (>10min)'}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


# ── Hermes AI call ────────────────────────────────────────────────────────────

def _env(key: str, default: str = '') -> str:
    if default:
        return os.environ.get(key, default)
    return os.environ.get(key, '')


def hermes_generate(prompt: str, system: str = '', timeout: int = 60) -> dict:
    """
    Call Hermes local gateway for text generation.
    Returns: {ok, text, error}
    """
    url = _env('HERMES_GATEWAY_URL', 'http://localhost:8642') + '/v1/chat/completions'
    token = _env('HERMES_GATEWAY_TOKEN', '')

    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})

    payload = json.dumps({
        'model': 'hermes',
        'messages': messages,
        'max_tokens': 1200,
    }).encode()

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }

    try:
        req = _ureq.Request(url, data=payload, headers=headers, method='POST')
        with _ureq.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
        text = data['choices'][0]['message']['content'].strip()
        return {'ok': True, 'text': text}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200], 'text': ''}
