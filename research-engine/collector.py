#!/usr/bin/env python3
"""
Research Collector
Downloads transcripts from YouTube trading channels via yt-dlp.
Reads channel list from channels/trading_channels.json.
"""
import os
import sys
import json
import subprocess
import shutil

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CHANNELS_FILE = "./channels/trading_channels.json"
OUTPUT = "./transcripts"
MAX_VIDEOS = int(os.getenv("COLLECTOR_MAX_VIDEOS", "3"))

os.makedirs(OUTPUT, exist_ok=True)


def load_channels():
    """Load channels from JSON config, fall back to hardcoded list."""
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r") as f:
            data = json.load(f)
        return [(c["url"], c.get("max_videos", MAX_VIDEOS), c.get("name", c["url"]))
                for c in data.get("channels", [])]
    # fallback
    return [
        ("https://www.youtube.com/@NoNonsenseForex", MAX_VIDEOS, "No Nonsense Forex"),
        ("https://www.youtube.com/@SMBcapital",       MAX_VIDEOS, "SMB Capital"),
        ("https://www.youtube.com/@TraderNick",       MAX_VIDEOS, "TraderNick"),
    ]


def check_ytdlp():
    if not shutil.which("yt-dlp"):
        print("ERROR: yt-dlp not found. Install with: pip3 install yt-dlp")
        sys.exit(1)


def collect_channel(channel_url: str, max_videos: int, name: str):
    print(f"\n📥 Collecting from: {name} (last {max_videos} videos)")
    # Append /videos to ensure we only get regular uploads (not Shorts/livestreams)
    url = channel_url.rstrip("/") + "/videos" if "/videos" not in channel_url else channel_url
    cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--skip-download",
        "--playlist-end", str(max_videos * 3),  # fetch extra to account for filtered items
        "--js-runtimes", "node",
        "--match-filter", "duration > 120 & !is_live",
        "-o", f"{OUTPUT}/%(uploader)s - %(title)s.%(ext)s",
        url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"  ⚠️  yt-dlp error for {name}:")
        print(f"  {result.stderr.strip()[:300]}")
        return 0

    # Count how many subtitle files were written this run
    downloaded = len([f for f in os.listdir(OUTPUT) if f.endswith(('.vtt', '.srt'))])
    print(f"  ✅ Done: {name}")
    return downloaded


def main():
    check_ytdlp()
    channels = load_channels()
    print(f"📋 Loaded {len(channels)} channels from config")

    success = 0
    for url, max_vids, name in channels:
        if collect_channel(url, max_vids, name):
            success += 1

    transcript_count = len([f for f in os.listdir(OUTPUT) if f.endswith(('.vtt', '.srt'))])
    print(f"\n✅ Collected from {success}/{len(channels)} channels")
    print(f"📄 Total transcripts in {OUTPUT}/: {transcript_count}")


if __name__ == "__main__":
    main()
