# Prompt — TikTok / Instagram Reels
_Inherits `_universal_content_rules.md`. Internal draft only; **no auto-posting**._

**Purpose:** Create TikTok / Instagram Reels-style short videos from a topic, source, or board card.

## Inputs
`content_id`, `topic`, `source_paths`, `audience`, `niche`, `voice_style`, `visual_style`,
`broll_keywords`, `affiliate_disclosure_required`, `target_platform` (tiktok|reels), `board_id`.

## Instruction to the model
> Write a 15–30s TikTok/Reels script optimized for native, fast, casual pacing. Strong first-second hook,
> visible pattern interrupts, kinetic captions. Educational; no guarantees; no luxury/wealth bait.

## Required output structure
1. **First-second hook** — on-screen text + spoken line that lands within 1.0s (curiosity, bold claim
   reversal, or "stop doing X"). Avoid slow intros.
2. **Pattern interrupts** — note 2–3 beat changes (zoom, cut, color flip, text slam) to hold retention.
3. **Fast caption style** — word-by-word / 1–3 word chunks, high-contrast, centered-lower.
4. **Visual / b-roll plan** — per beat; native-feeling, vertical 9:16; clean/illustrative; no misleading imagery.
5. **Voice tone** — casual, confident, friendly (Piper or native VO); spoken lines ≤ 12 words.
6. **Platform-specific caption** — TikTok: punchy + 1 question; Reels: slightly cleaner + 1 CTA.
7. **Hashtags** — 4–6, niche + 1 broad; no banned/spammy tags.
8. **Compliance checks** — educational-only line; affiliate disclosure if links; no guarantees; checklist below.

## Compliance checklist (must all pass)
- [ ] No guarantee / "get approved" / income claims
- [ ] Educational disclaimer present where relevant
- [ ] Affiliate disclosure if any link/program
- [ ] No misleading wealth/luxury imagery
- [ ] Claims traceable to sources

## Output paths
- Packet: `reports/creative_short_packets/<short>_tiktok_reels.md`
- Draft render: `reports/tool_lab/hyperframes_renders/<short>_tiktok_v1.mp4` (or b-roll lane)

## Board + approval
`content_board_add.py … --content-type "TikTok/Reels" --platform "TikTok,Instagram Reels"`.
Score → route (<7 Improve/Retry · 7–8 Needs Ray Review · 9+ candidate). **No auto-posting** — Ray approval
required for any publish; the executor stays disabled.
