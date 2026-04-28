#!/usr/bin/env python3
"""
Nexus Research — YouTube Channel Manager
Add, remove, and list channels for the research pipeline.

Usage:
  python3 channels.py list
  python3 channels.py add <youtube_url> [--name "Channel Name"] [--category forex_strategy] [--videos 3]
  python3 channels.py remove <name_or_url>
  python3 channels.py run [--videos N]        # collect + summarize + store immediately
"""
import os, sys, json, subprocess, argparse

CHANNELS_FILE = os.path.join(os.path.dirname(__file__), "channels", "trading_channels.json")

CATEGORIES = [
    "forex_strategy",
    "trading_education",
    "crypto_strategy",
    "stock_trading",
    "options_trading",
    "macro_analysis",
    "trading_psychology",
    "technical_analysis",
    "other",
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def load():
    if not os.path.exists(CHANNELS_FILE):
        return {"channels": []}
    with open(CHANNELS_FILE) as f:
        return json.load(f)

def save(data):
    with open(CHANNELS_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"✅ Saved to {CHANNELS_FILE}")

def resolve_name(url: str) -> str:
    """Derive a display name from a YouTube URL (best-effort)."""
    handle = url.rstrip("/").split("/")[-1].lstrip("@")
    # Convert CamelCase / no-separator handles → spaced name
    import re
    spaced = re.sub(r'([A-Z])', r' \1', handle).strip()
    return spaced if spaced != handle else handle

# ── Commands ─────────────────────────────────────────────────────────────────

def cmd_list(args):
    data = load()
    channels = data.get("channels", [])
    if not channels:
        print("No channels configured yet. Use: python3 channels.py add <url>")
        return

    print(f"\n{'#':<4} {'Name':<35} {'Category':<22} {'Videos':<8} URL")
    print("─" * 95)
    for i, c in enumerate(channels, 1):
        print(f"{i:<4} {c.get('name','?'):<35} {c.get('category','?'):<22} {c.get('max_videos',1):<8} {c.get('url','?')}")
    print(f"\nTotal: {len(channels)} channels")


def cmd_add(args):
    data = load()
    channels = data.setdefault("channels", [])

    url = args.url.strip().rstrip("/")

    # Check duplicate
    for c in channels:
        if c["url"].rstrip("/") == url or (args.name and c["name"].lower() == args.name.lower()):
            print(f"⚠️  Channel already exists: {c['name']} ({c['url']})")
            return

    name     = args.name or resolve_name(url)
    category = args.category or "trading_education"
    videos   = args.videos or 3

    if category not in CATEGORIES:
        print(f"⚠️  Unknown category '{category}'. Valid options:")
        for cat in CATEGORIES:
            print(f"   {cat}")
        return

    entry = {"name": name, "url": url, "category": category, "max_videos": videos}
    channels.append(entry)
    save(data)

    print(f"\n  Added: {name}")
    print(f"  URL:      {url}")
    print(f"  Category: {category}")
    print(f"  Videos:   {videos} per run")
    print(f"\nRun 'python3 channels.py run' to scrape it now.")


def cmd_remove(args):
    data  = load()
    query = args.query.lower().strip()
    before = len(data.get("channels", []))

    data["channels"] = [
        c for c in data.get("channels", [])
        if query not in c.get("name", "").lower() and query not in c.get("url", "").lower()
    ]

    removed = before - len(data["channels"])
    if removed == 0:
        print(f"No channel matched '{args.query}'. Run 'python3 channels.py list' to see names.")
        return

    save(data)
    print(f"Removed {removed} channel(s) matching '{args.query}'.")


def cmd_run(args):
    """Collect → Summarize → Store for all configured channels."""
    root = os.path.dirname(__file__)
    env  = os.environ.copy()

    # Load .env if present
    env_path = os.path.join(root, "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env.setdefault(k.strip(), v.strip())

    max_videos = str(args.videos) if args.videos else None
    if max_videos:
        env["COLLECTOR_MAX_VIDEOS"] = max_videos

    steps = [
        ("📥 Collecting transcripts...", ["python3", "collector.py"]),
        ("🧠 Summarizing...",            ["python3", "summarize.py"]),
        ("🎯 Extracting strategies...",  ["python3", "strategy_extractor.py"]),
        ("☁️  Storing to Supabase...",   ["python3", "supabase_store.py"]),
    ]

    for label, cmd in steps:
        print(f"\n{label}")
        result = subprocess.run(cmd, cwd=root, env=env)
        if result.returncode != 0:
            print(f"❌ Step failed: {' '.join(cmd)}")
            sys.exit(1)

    print("\n✅ Research cycle complete!")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Nexus YouTube Channel Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 channels.py list
  python3 channels.py add https://www.youtube.com/@TraderNick
  python3 channels.py add https://www.youtube.com/@SMBcapital --name "SMB Capital" --category trading_education --videos 5
  python3 channels.py remove "SMB Capital"
  python3 channels.py remove tradernick
  python3 channels.py run
  python3 channels.py run --videos 2

Categories:
  forex_strategy, trading_education, crypto_strategy, stock_trading,
  options_trading, macro_analysis, trading_psychology, technical_analysis, other
        """
    )
    sub = parser.add_subparsers(dest="command")

    # list
    sub.add_parser("list", help="Show all configured channels")

    # add
    p_add = sub.add_parser("add", help="Add a YouTube channel")
    p_add.add_argument("url",                              help="YouTube channel URL (e.g. https://www.youtube.com/@Handle)")
    p_add.add_argument("--name",     "-n", default=None,  help="Display name (auto-detected if omitted)")
    p_add.add_argument("--category", "-c", default=None,  help="Category (default: trading_education)")
    p_add.add_argument("--videos",   "-v", type=int, default=3, help="Max videos to collect per run (default: 3)")

    # remove
    p_rm = sub.add_parser("remove", help="Remove a channel by name or URL fragment")
    p_rm.add_argument("query", help="Name or URL fragment to match")

    # run
    p_run = sub.add_parser("run", help="Run full pipeline: collect → summarize → store")
    p_run.add_argument("--videos", "-v", type=int, default=None, help="Override max videos per channel")

    args = parser.parse_args()

    if   args.command == "list":   cmd_list(args)
    elif args.command == "add":    cmd_add(args)
    elif args.command == "remove": cmd_remove(args)
    elif args.command == "run":    cmd_run(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
