"""
content_pipeline.py — Nova Media content production pipeline.

Stages:
  1. topic_intake      — receive topic + target platform
  2. script_generation — OpenClaw generates short-form script
  3. transcript_gen    — script → narration text (cleaned, timed)
  4. tts_generation    — narration → audio file (macOS say / gTTS)
  5. asset_generation  — placeholder: stills, b-roll, captions (manual or future tool)
  6. assembly          — placeholder: ffmpeg assembly (needs ffmpeg)
  7. review            — status set to 'needs_review', stored in Supabase
  8. publish_ready     — after human approval, status = 'publish_ready'

Supported content types:
  instagram_reel       — 30-60s, hook + value + CTA
  tiktok_short         — 15-60s, pattern interrupt + loop hook
  youtube_short        — 60s max, single insight
  youtube_training     — 5-15min, structured teaching format

Cost model:
  - Script generation: OpenClaw (local/free via Codex OAuth)
  - TTS: macOS say (free, built-in) or gTTS (free, network)
  - Assembly: manual or future ffmpeg (needs install)
  - NO paid video AI APIs by default — pluggable via tooling_adapter
"""

import os
import json
import hashlib
import urllib.request as _ureq
import urllib.error as _uerr
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .tooling_adapter import hermes_generate, tts_to_file, capabilities
import lib.ssl_fix  # noqa — fixes HTTPS on macOS Python 3.14


# ── Config ────────────────────────────────────────────────────────────────────

def _env(key: str, default: str = '') -> str:
    return os.environ.get(key, default)


CONTENT_OUTPUT_DIR = Path(_env('CONTENT_OUTPUT_DIR', str(Path.home() / 'nexus-ai' / 'content_employee' / 'output')))
CONTENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SUPABASE_URL = _env('SUPABASE_URL', '')
SUPABASE_KEY = _env('SUPABASE_SERVICE_ROLE_KEY', '') or _env('SUPABASE_KEY', '')


# ── Format-specific script prompts ───────────────────────────────────────────

FORMAT_PROMPTS = {
    'instagram_reel': """\
Write a 30-60 second Instagram Reel script about: {topic}
Niche: {niche}
Format:
- Hook (3-5 seconds): bold opening statement or question
- Value (20-40 seconds): 3 tight points, no fluff
- CTA (5 seconds): one clear action
Output: plain narration text only, no stage directions, no hashtags.
Target length: ~120 words.""",

    'tiktok_short': """\
Write a 15-60 second TikTok script about: {topic}
Niche: {niche}
Format:
- Pattern interrupt hook (first 2 seconds): surprising or counter-intuitive
- Main insight: 1-2 punchy points
- Loop hook at end: tease next part or restate opening
Output: plain narration text only, no stage directions.
Target length: ~80 words.""",

    'youtube_short': """\
Write a 60-second YouTube Short script about: {topic}
Niche: {niche}
Format:
- Hook: one sentence that earns the next 55 seconds
- Single core insight explained simply
- One-sentence close
Output: plain narration text only.
Target length: ~130 words.""",

    'youtube_training': """\
Write a structured YouTube training video script about: {topic}
Niche: {niche}
Format:
- Intro (30s): who this is for and what they'll get
- Section 1: core concept (~2 min)
- Section 2: common mistakes (~2 min)
- Section 3: step-by-step process (~3 min)
- Outro: recap + subscribe CTA (~30s)
Output: plain narration text only, section headers as [SECTION: name].
Target length: ~900 words.""",
}


# ── Supabase helpers ──────────────────────────────────────────────────────────

def _supabase(method: str, path: str, payload: Optional[dict] = None, extra_headers: Optional[dict] = None) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {'ok': False, 'error': 'supabase_not_configured'}
    url = SUPABASE_URL.rstrip('/') + path
    data = json.dumps(payload).encode() if payload else None
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation',
    }
    if method == 'PATCH':
        headers['Prefer'] = 'return=minimal'
    if extra_headers:
        headers.update(extra_headers)
    try:
        req = _ureq.Request(url, data=data, headers=headers, method=method)
        with _ureq.urlopen(req, timeout=10) as r:
            body = r.read()
            return {'ok': True, 'data': json.loads(body) if body else []}
    except _uerr.HTTPError as e:
        return {'ok': False, 'error': f'HTTP {e.code}: {e.read()[:200].decode()}'}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


def _upsert_content_request(record: dict) -> dict:
    return _supabase('POST', '/rest/v1/content_drafts?on_conflict=content_id', record,
                     extra_headers={'Prefer': 'resolution=merge-duplicates,return=representation'})


def _update_content_request(content_id: str, patch: dict) -> dict:
    path = f'/rest/v1/content_drafts?id=eq.{content_id}'
    return _supabase('PATCH', path, patch)


def _insert_script(record: dict) -> dict:
    return _supabase('POST', '/rest/v1/content_scripts', record)


def _insert_tts_asset(record: dict) -> dict:
    return _supabase('POST', '/rest/v1/content_assets', record)


# ── Stage 1: Topic Intake ─────────────────────────────────────────────────────

def stage_topic_intake(
    topic: str,
    content_type: str,
    niche: str,
    target_platforms: list,
    requested_by: str = 'nova_media',
) -> dict:
    """
    Create a content request record in Supabase.
    Returns: {ok, content_id, record}
    """
    if content_type not in FORMAT_PROMPTS:
        return {
            'ok': False,
            'error': f'Unknown content_type: {content_type}. Valid: {list(FORMAT_PROMPTS.keys())}',
        }

    content_id = hashlib.sha256(
        f'{topic}:{content_type}:{niche}:{datetime.utcnow().date()}'.encode()
    ).hexdigest()[:16]

    record = {
        'content_id':       content_id,
        'topic':            topic,
        'content_type':     content_type,
        'niche':            niche,
        'target_platforms': target_platforms,
        'requested_by':     requested_by,
        'status':           'topic_received',
        'created_at':       datetime.now(timezone.utc).isoformat(),
        'updated_at':       datetime.now(timezone.utc).isoformat(),
    }

    result = _upsert_content_request(record)
    if not result['ok']:
        import logging as _log
        _log.getLogger(__name__).warning('Supabase tracking unavailable (continuing locally): %s', result.get('error',''))

    return {'ok': True, 'content_id': content_id, 'record': record}


# ── Stage 2: Script Generation ────────────────────────────────────────────────

def stage_script_generation(content_id: str, topic: str, content_type: str, niche: str) -> dict:
    """
    Generate script via OpenClaw. Stores to content_scripts table.
    Returns: {ok, script_id, script_text}
    """
    prompt_template = FORMAT_PROMPTS.get(content_type)
    if not prompt_template:
        return {'ok': False, 'error': f'No prompt template for {content_type}'}

    prompt = prompt_template.format(topic=topic, niche=niche)

    system = (
        "You are Nova Media, an AI content employee. "
        "You create crisp, high-value short-form scripts for financial education and coaching niches. "
        "Write conversational, direct narration. No filler. No generic phrases like 'In today's video'."
    )

    result = hermes_generate(prompt, system=system)

    if not result['ok']:
        # Fallback: template-based script if OpenClaw is unavailable
        script_text = _fallback_script(topic, content_type, niche)
        result = {'ok': True, 'text': script_text, 'provider': 'fallback_template'}
    else:
        result['provider'] = 'hermes'

    script_text = result['text']
    script_id = hashlib.sha256(f'{content_id}:script'.encode()).hexdigest()[:16]

    record = {
        'script_id':    script_id,
        'content_id':   content_id,
        'content_type': content_type,
        'script_text':  script_text,
        'provider':     result.get('provider', 'hermes'),
        'word_count':   len(script_text.split()),
        'status':       'draft',
        'created_at':   datetime.now(timezone.utc).isoformat(),
    }

    _insert_script(record)
    _update_content_request(content_id, {'status': 'script_generated', 'updated_at': datetime.now(timezone.utc).isoformat()})

    return {'ok': True, 'script_id': script_id, 'script_text': script_text}


def _fallback_script(topic: str, content_type: str, niche: str) -> str:
    """Minimal template script when OpenClaw is unavailable."""
    return (
        f"Here's what you need to know about {topic}. "
        f"In the {niche} space, this is one of the most overlooked principles. "
        f"Most people get this wrong because they focus on the surface level. "
        f"Here is the key insight: master the fundamentals before chasing tactics. "
        f"If this resonated, follow for more {niche} content."
    )


# ── Stage 3: Transcript Preparation ──────────────────────────────────────────

def stage_transcript_generation(content_id: str, script_text: str) -> dict:
    """
    Clean and segment the script into narration-ready transcript.
    No external tools needed — pure text processing.
    Returns: {ok, transcript_text, segments}
    """
    # Clean script: remove section headers, trim whitespace
    lines = []
    for line in script_text.split('\n'):
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            continue  # skip section markers
        if line:
            lines.append(line)

    transcript_text = ' '.join(lines)

    # Split into ~10-word segments for timing hints
    words = transcript_text.split()
    segments = []
    chunk_size = 10
    for i in range(0, len(words), chunk_size):
        chunk = ' '.join(words[i:i + chunk_size])
        segments.append({'index': len(segments), 'text': chunk})

    _update_content_request(content_id, {
        'status': 'transcript_ready',
        'updated_at': datetime.now(timezone.utc).isoformat(),
    })

    return {'ok': True, 'transcript_text': transcript_text, 'segments': segments}


# ── Stage 4: TTS Audio Generation ────────────────────────────────────────────

def stage_tts_generation(content_id: str, transcript_text: str, voice: str = 'Samantha') -> dict:
    """
    Convert transcript to audio using available local TTS provider.
    Saves audio file locally; records asset in content_assets table.
    Returns: {ok, audio_path, provider}
    """
    audio_dir = CONTENT_OUTPUT_DIR / content_id
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_path = str(audio_dir / 'narration.aiff')

    result = tts_to_file(transcript_text, audio_path, voice=voice)

    asset_record = {
        'content_id':  content_id,
        'asset_type':  'audio_narration',
        'local_path':  result.get('path', audio_path),
        'provider':    result.get('provider', 'none'),
        'status':      'ready' if result['ok'] else 'failed',
        'error':       result.get('error', ''),
        'created_at':  datetime.now(timezone.utc).isoformat(),
    }
    _insert_tts_asset(asset_record)

    if result['ok']:
        _update_content_request(content_id, {
            'status': 'audio_ready',
            'updated_at': datetime.now(timezone.utc).isoformat(),
        })

    return result


# ── Stage 5: Asset Generation (scaffold) ──────────────────────────────────────

def stage_asset_generation(content_id: str, content_type: str) -> dict:
    """
    Scaffold for future: image stills, b-roll, caption overlays.
    Currently: generates a structured asset manifest for manual production.
    Requires: ffmpeg (not installed), Pillow (not installed), or future video API.
    """
    caps = capabilities()

    manifest = {
        'content_id':      content_id,
        'required_assets': _asset_manifest(content_type),
        'tooling_ready':   caps['video_assembly'],
        'missing_tools':   caps['missing'],
        'manual_required': not caps['video_assembly'],
        'note': (
            'Asset assembly requires ffmpeg. Install: brew install ffmpeg. '
            'Until then, produce assets manually using this manifest.'
            if not caps['video_assembly'] else
            'ffmpeg available — wire up assembly in stage_assembly().'
        ),
    }

    # Write manifest to local file for manual reference
    manifest_path = CONTENT_OUTPUT_DIR / content_id / 'asset_manifest.json'
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2))

    _update_content_request(content_id, {
        'status': 'assets_manifest_ready',
        'metadata': json.dumps({'asset_manifest_path': str(manifest_path)}),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    })

    return {'ok': True, 'manifest': manifest, 'manifest_path': str(manifest_path)}


def _asset_manifest(content_type: str) -> list:
    base = [
        {'type': 'background', 'description': 'Clean branded background (1080x1920 for Reels/Shorts, 1920x1080 for YouTube)'},
        {'type': 'logo_overlay', 'description': 'Brand logo in corner, 10% opacity'},
        {'type': 'captions', 'description': 'Word-level captions burned in or as .srt sidecar'},
    ]
    if content_type in ('instagram_reel', 'tiktok_short', 'youtube_short'):
        base += [
            {'type': 'hook_text_overlay', 'description': 'Bold text overlay for first 3 seconds'},
            {'type': 'cta_endcard', 'description': 'Follow / Subscribe end card 2s'},
        ]
    if content_type == 'youtube_training':
        base += [
            {'type': 'chapter_titles', 'description': 'Text overlay at each chapter marker'},
            {'type': 'b_roll', 'description': 'Screen recordings or stock clips per section'},
            {'type': 'thumbnail', 'description': '1280x720 thumbnail with face + text'},
        ]
    return base


# ── Stage 6: Assembly (scaffold — requires ffmpeg) ────────────────────────────

def stage_assembly(content_id: str) -> dict:
    """
    Assemble narration audio + background into final.mp4 using ffmpeg.
    Background priority: background.mp4 > background.jpg > generated solid color.
    Output: <content_output_dir>/<content_id>/final.mp4
    """
    caps = capabilities()
    if not caps['video_assembly']:
        return {
            'ok': False,
            'status': 'manual_required',
            'reason': 'ffmpeg not installed',
            'install_hint': 'brew install ffmpeg',
            'message': (
                'Assembly is manual. Use the asset manifest + narration audio to produce '
                'the video in CapCut, DaVinci Resolve, or any editor. '
                'Upload final file to content_output_dir and update status to needs_review.'
            ),
        }

    out_dir = CONTENT_OUTPUT_DIR / content_id
    out_path = out_dir / 'final.mp4'

    # Find narration audio (prefer mp3, fallback aiff)
    audio_path = None
    for candidate in ('narration.mp3', 'narration.aiff'):
        p = out_dir / candidate
        if p.exists():
            audio_path = p
            break
    if not audio_path:
        return {'ok': False, 'status': 'no_audio', 'reason': 'No narration audio found — run TTS stage first'}

    # Use provided background.mp4/jpg if present, otherwise generate solid black
    bg_video = out_dir / 'background.mp4'
    bg_image = out_dir / 'background.jpg'

    import subprocess as _sp

    try:
        if bg_video.exists():
            # Loop background video to match audio length, re-encode for compatibility
            cmd = [
                'ffmpeg', '-y',
                '-stream_loop', '-1', '-i', str(bg_video),
                '-i', str(audio_path),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k',
                '-map', '0:v:0', '-map', '1:a:0',
                '-shortest', '-movflags', '+faststart',
                str(out_path),
            ]
        elif bg_image.exists():
            # Loop static image for duration of audio
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1', '-i', str(bg_image),
                '-i', str(audio_path),
                '-c:v', 'libx264', '-tune', 'stillimage', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart',
                str(out_path),
            ]
        else:
            # No background — generate branded solid color (1080x1920 portrait for Reels/Shorts)
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi', '-i', 'color=c=0x1a1a2e:size=1080x1920:rate=30',
                '-i', str(audio_path),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k',
                '-shortest', '-movflags', '+faststart',
                str(out_path),
            ]

        proc = _sp.Popen(cmd, stdout=_sp.PIPE, stderr=_sp.PIPE)
        try:
            stdout, stderr = proc.communicate(timeout=120)
        except _sp.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return {'ok': False, 'status': 'timeout', 'reason': 'ffmpeg killed after 2min limit'}

        if proc.returncode != 0:
            return {
                'ok': False, 'status': 'ffmpeg_error',
                'reason': stderr.decode(errors='replace')[-400:] if stderr else 'ffmpeg failed',
            }

        return {
            'ok': True,
            'status': 'assembled',
            'path': str(out_path),
            'audio_source': str(audio_path),
            'background': 'provided' if (bg_video.exists() or bg_image.exists()) else 'generated',
        }

    except _sp.TimeoutExpired:
        return {'ok': False, 'status': 'timeout', 'reason': 'ffmpeg timed out'}
    except Exception as e:
        return {'ok': False, 'status': 'error', 'reason': str(e)[:200]}


# ── Stage 7: Review → Publish-Ready ──────────────────────────────────────────

def stage_set_review(content_id: str) -> dict:
    """Mark content as needs_review. Human must approve before publish_ready."""
    result = _update_content_request(content_id, {
        'status': 'needs_review',
        'updated_at': datetime.now(timezone.utc).isoformat(),
    })
    return {'ok': result['ok'], 'status': 'needs_review'}


def stage_approve(content_id: str, approved_by: str) -> dict:
    """
    Human approval step. Sets status to publish_ready.
    NEVER auto-called by the worker — must be triggered externally.
    """
    result = _update_content_request(content_id, {
        'status':      'publish_ready',
        'approved_by': approved_by,
        'approved_at': datetime.now(timezone.utc).isoformat(),
        'updated_at':  datetime.now(timezone.utc).isoformat(),
    })
    return {'ok': result['ok'], 'status': 'publish_ready'}


# ── Full pipeline runner ──────────────────────────────────────────────────────

def run_pipeline(
    topic: str,
    content_type: str,
    niche: str,
    target_platforms: list,
    tts_voice: str = 'Samantha',
    requested_by: str = 'nova_media',
) -> dict:
    """
    Run stages 1-7 for a single content request.
    Returns a full pipeline result dict.
    """
    results = {}

    # Stage 1
    r1 = stage_topic_intake(topic, content_type, niche, target_platforms, requested_by)
    results['topic_intake'] = r1
    if not r1['ok']:
        return results
    content_id = r1['content_id']

    # Stage 2
    r2 = stage_script_generation(content_id, topic, content_type, niche)
    results['script_generation'] = r2
    if not r2['ok']:
        results['blocked_at'] = 'script_generation'
        return results

    # Stage 3
    r3 = stage_transcript_generation(content_id, r2['script_text'])
    results['transcript_generation'] = r3

    # Stage 4
    r4 = stage_tts_generation(content_id, r3['transcript_text'], voice=tts_voice)
    results['tts_generation'] = r4

    # Stage 4.5: Fetch background visual from Pexels / AI
    try:
        from content_employee.video_engine import fetch_background
        audio_duration = 30.0
        try:
            import subprocess as _sp
            probe = _sp.run(['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                             '-of', 'csv=p=0', str(CONTENT_OUTPUT_DIR / content_id / 'narration.mp3')],
                            capture_output=True, text=True)
            audio_duration = float(probe.stdout.strip())
        except Exception:
            pass
        r_bg = fetch_background(topic, niche, content_id, duration=audio_duration)
        results['background_fetch'] = r_bg
    except Exception as e:
        results['background_fetch'] = {'ok': False, 'error': str(e)}

    # Stage 5
    r5 = stage_asset_generation(content_id, content_type)
    results['asset_generation'] = r5

    # Stage 6
    r6 = stage_assembly(content_id)
    results['assembly'] = r6

    # Stage 7 — always goes to review, never auto-publishes
    r7 = stage_set_review(content_id)
    results['review'] = r7

    results['content_id'] = content_id
    results['status'] = 'needs_review'
    results['audio_ready'] = r4.get('ok', False)
    results['assembly_ready'] = r6.get('ok', False)
    results['manual_assembly_required'] = r6.get('status') == 'manual_required'

    return results
