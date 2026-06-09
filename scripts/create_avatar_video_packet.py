#!/usr/bin/env python3
"""
create_avatar_video_packet.py — build an Avatar / Host Video production packet from a script.

Deterministic, free, no network, no paid API, no upload. Produces a complete production packet
(host script + shot list + captions + lower-thirds + HyperFrames overlay plan) and — because this
host has no avatar GPU — a **manual hosted-tool packet** (CapCut free; HeyGen/Symphony/Flow only if
Ray approves a paid tool). It never renders a fake avatar and never claims a blocked tool works.

Capability probe: if there is no NVIDIA GPU / no torch, local talking-avatar generation is reported
BLOCKED and the packet routes to the free faceless-host (HyperFrames + Piper) draft + manual hero route.

Usage:
  python scripts/create_avatar_video_packet.py --content-id fcf087ea-... \
      --script-path reports/publish_packages/fcf087ea_business_credit_myths.md \
      --voiceover-path reports/tool_lab/creative_renders/fcf087ea_business_credit_myths_v4_piper_voiceover.wav \
      --style "clean business host / virtual advisor / no hype" --duration 45
"""
from __future__ import annotations
import argparse, re, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DEFAULT = ROOT / "reports" / "content_engine" / "generated" / "avatar_video_packets"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def avatar_capability() -> dict:
    """Honest local talking-avatar capability probe. No install, no network."""
    has_nvidia = shutil.which("nvidia-smi") is not None
    try:
        import torch  # noqa: F401
        has_torch = True
        try:
            cuda = bool(torch.cuda.is_available())
        except Exception:
            cuda = False
    except Exception:
        has_torch, cuda = False, False
    blocked = not (has_nvidia and has_torch and cuda)
    reason = ("local talking-avatar BLOCKED: " +
              ", ".join(filter(None, [
                  None if has_nvidia else "no NVIDIA GPU",
                  None if has_torch else "no torch",
                  None if cuda else "no CUDA",
              ])) ) if blocked else "local avatar capable"
    return {"blocked": blocked, "reason": reason,
            "nvidia": has_nvidia, "torch": has_torch, "cuda": cuda}


def parse_script(path: Path | None) -> dict:
    """Pull a usable script body + title from a publish package (or return empty)."""
    if not path or not path.exists():
        return {"title": "", "body": "", "hashtags": ""}
    t = path.read_text(encoding="utf-8", errors="ignore")
    title = re.search(r"Title:\s*(.+)", t)
    m = re.search(r"##[^\n]*script[^\n]*\n(.+?)(?:\n##\s|\Z)", t, re.I | re.S)
    tags = re.search(r"##\s*Hashtags\s*\n(.+)", t)
    return {
        "title": re.sub(r"\s*\(.*?script.*?\)\s*$", "", (title.group(1).strip() if title else ""), flags=re.I),
        "body": (m.group(1).strip() if m else ""),
        "hashtags": (tags.group(1).strip() if tags else ""),
    }


def host_script_45(title: str, body: str) -> str:
    """Build a 45s host-delivered version from the source script body (myth/truth aware)."""
    lines = [ln.strip() for ln in re.split(r"\n+", body) if ln.strip() and not ln.lower().startswith("(")]
    intro = "Quick one for founders — let's clear up three things about business credit that cost people time."
    keep = [ln for ln in lines if any(k in ln.lower() for k in ("myth", "truth", "hook")) or ":" in ln][:6]
    if not keep:
        keep = lines[:5]
    cta = "Save this, and build it the boring, correct way. Educational only — not financial advice."
    return intro + "\n" + "\n".join(f"- {re.sub(r'^(HOOK|MYTH ?[0-9]?|TRUTH ?[0-9]?|CTA):?', '', k).strip()}"
                                    for k in keep) + "\n" + cta


def main() -> int:
    ap = argparse.ArgumentParser(description="Create an avatar/host video production packet")
    ap.add_argument("--content-id", required=True)
    ap.add_argument("--script-path", default=None)
    ap.add_argument("--voiceover-path", default=None)
    ap.add_argument("--style", default="clean business host / virtual advisor / no hype")
    ap.add_argument("--duration", type=int, default=45)
    ap.add_argument("--output-dir", default=str(OUT_DEFAULT))
    args = ap.parse_args()

    short = args.content_id.split("-")[0]
    cap = avatar_capability()
    sc = parse_script(Path(args.script_path) if args.script_path else None)
    title = sc["title"] or args.content_id
    vo = args.voiceover_path or "(synthesize Piper voiceover — generate_short_voiceover.py)"
    h45 = host_script_45(title, sc["body"]) if sc["body"] else "(provide --script-path to auto-build the host script)"

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f"{short}_avatar_host_packet.md"

    packet = f"""# Avatar / Host Video Packet — {title}
# DRAFT / PACKET ONLY — no upload, no post, no schedule. content_id: {args.content_id}
# prompt: skills/content_prompts/avatar_host_video.md · style: {args.style} · target ~{args.duration}s

## Avatar capability on this host
- **{cap['reason']}** (nvidia={cap['nvidia']}, torch={cap['torch']}, cuda={cap['cuda']}).
- → Autonomous draft route: **faceless host (HyperFrames + Piper)**. Hero route: **manual hosted packet** (below).
- No local avatar render is faked. If/when a Linux+NVIDIA host exists, re-run to enable a real talking head.

## Host / character concept
- Role: business host / virtual advisor — calm, credible, no hype.
- Persona: faceless or stylized Nexus host (navy/blue), NO real-person likeness, NO creator impersonation.
- Voice: Piper `en_US-amy-medium` (local/free) → `{vo}`.

## {args.duration}-second host script
{h45}

## 90-second extended version (outline)
- Cold open (0-8s): the hook above, host on camera / faceless card.
- Body (8-75s): expand each point with one concrete example + an on-screen card per point.
- Close (75-90s): recap the correct order + CTA + disclosure.

## Scene / shot list
| # | Shot | On-screen | B-roll insert | Lower-third |
|---|---|---|---|---|
| 1 | host talking-head / title card | hook line | person at laptop | Nexus · Business Credit |
| 2 | host + key-point card | point 1 | document/checklist | "Myth 1" |
| 3 | overlay card (motion graphic) | truth 1 | bank/entity icons | "Truth" |
| 4 | host + key-point card | point 2 | cards → rising bar | "Myth 2" |
| 5 | overlay card | truth 2 | pattern/graph | "Truth" |
| 6 | host close | CTA | calendar/cycles | "Save this" |

## B-roll inserts (free sources only; NO misleading luxury/wealth imagery)
person at laptop · business documents/checklist · bank & entity icons · simple rising bar chart · calendar pages.

## Lower-thirds
- Persistent: "Nexus · GoClearOnline". Section labels: "Myth 1/2/3", "Truth", "Save this".

## Caption style
Kinetic, 1–4 words/beat, bold sans, high-contrast pill, safe margins. (HyperFrames `.clip` or Whisper `init --audio`.)

## HyperFrames overlay concept
Compose host/faceless base + motion-graphics overlays via `skills/content_prompts/hyperframes_video.md`:
key-point cards, myth(red ✕)/truth(green ✓) flips, lower-thirds, kinetic captions, Nexus brand + disclosure.
Render: `scripts/render_creative_short_hyperframes.py` → `reports/tool_lab/hyperframes_renders/{short}_avatar_host_v1.mp4`.

## Manual hosted-avatar route (hero quality; Ray-gated)
1. **CapCut (free):** assemble host base + b-roll + captions + lower-thirds; export 1080×1920 / 1920×1080.
2. **HeyGen / Symphony / Google Flow (ONLY if Ray approves a paid/manual tool):** paste the host script,
   pick a clean business avatar, use the Piper wav or the tool's TTS, export MP4. **No account connected here; no posting.**
3. Bring the exported MP4 back as a draft; attach to the board card; generate an approval card.

## YouTube metadata
- Title: {sc['title'] or '3 Business Credit Myths That Cost You Time'} #Shorts
- Description: educational summary + "Educational only — not financial advice. No guarantees." +
  "This content may include affiliate links. If you use a link, Nexus/GoClearOnline may earn a commission at no extra cost to you."
- Hashtags: {sc['hashtags'] or '#Shorts #businesscredit #businessfunding #smallbusiness #entrepreneur'}

## Compliance / disclosure
Educational only; no guarantees; no "get approved"; affiliate disclosure if links; claims traced to sources;
no real-person likeness; no copyrighted footage.

## Board update metadata
- content_type: "Avatar/Host Video" · prompt_used: avatar_host_video.md
- generated_artifacts: ["{out.relative_to(ROOT)}"]
- recommended status: Drafted (packet ready) → score → Needs Ray Review (≥7) / Improve / Retry (<7)
- next_action: build faceless-host HyperFrames draft OR run the manual hero route (Ray-gated)

_Generated by create_avatar_video_packet.py · {_now()} · free/local · no paid API · no upload._
"""
    out.write_text(packet, encoding="utf-8")
    print(f"wrote packet: {out.relative_to(ROOT)}")
    print(f"avatar capability: {cap['reason']}")
    print("board: content_type='Avatar/Host Video' prompt_used=avatar_host_video.md status=Drafted (score before review)")
    print("NO render run (local avatar blocked); NO upload/post/schedule.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
