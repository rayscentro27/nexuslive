# Render Remotion v3 via GitHub Actions (artifact only)

## Why
The local Mac is **macOS 12 (Darwin 21.6)** — too old for Remotion 4.x's headless browser
(render times out at browser connect). A Linux runner (ubuntu-latest) renders it cleanly.
This workflow produces an **MP4 artifact only** — no YouTube, no posting, no secrets.

## Trigger (manual only)
- **GitHub UI:** repo → Actions → "Render Remotion Short (artifact only)" → Run workflow →
  (optionally change inputs) → Run.
- **gh CLI:**
  `gh workflow run render-remotion-short.yml -f content_id=fcf087ea -f output_name=fcf087ea_business_credit_myths_v3_remotion.mp4`
- Watch: `gh run watch` (or Actions tab).

## Inputs (defaults shown)
- content_id: `fcf087ea`
- remotion_data_file: `tool-lab/remotion-shorts/src/data/fcf087ea.json`
- output_name: `fcf087ea_business_credit_myths_v3_remotion.mp4`

## Expected artifact
- Artifact name: **nexus-remotion-short-fcf087ea**
- Contains: `fcf087ea_business_credit_myths_v3_remotion.mp4`

## Download + place locally
- **GitHub UI:** open the finished run → Artifacts → download the zip → unzip.
- **gh CLI:** `gh run download <run-id> -n nexus-remotion-short-fcf087ea -D reports/tool_lab/creative_renders/`
- Then validate: `python3 scripts/validate_remotion_ci_artifact.py reports/tool_lab/creative_renders/fcf087ea_business_credit_myths_v3_remotion.mp4`

## Safety notes
- Artifact render only. **No upload, no post, no schedule.**
- **No repo secrets**, no YouTube credentials, no paid APIs.
- `social_publish_executor.py` (the only upload path) is untouched; executor stays disabled.
- To later publish the v3 MP4: review it, then use the scoped, gated `social_publish_executor.py`
  with a per-item approval (separate, deliberate) — same as v2.
