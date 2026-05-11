# Faceless Content Engine

Date: 2026-05-11
Mode: planning architecture, safe/no auto-publish changes.

## Pipeline Architecture
1. Ingestion
- Inputs: YouTube transcripts, trend notes, internal knowledge emails, operator prompts.
- Queue: `topic_backlog -> research_ready -> script_ready -> production_ready -> published -> analyzed`.

2. Research Workflow
- Pull internal-first context from Nexus reports and knowledge queue.
- Attach source metadata: channel, URL, date, topic family, confidence.
- Produce short research brief (problem, promise, proof, CTA).

3. Topic Generation
- Buckets: funding, AI automation, credit, grants, side hustles, online business intelligence, educational trading.
- Scoring model: demand signal, monetization fit, compliance risk, production effort.

4. Script Workflow
- Hook bank + format templates:
  - 30-60s shorts script
  - 3-8 min explainer script
  - carousel/thread copy variant
- Require compliance footer for financial/legal claims.

5. Voiceover Workflow
- Persona matrix: calm educator, tactical operator, urgency alert.
- TTS script linting: sentence length, pacing markers, pronunciation map.

6. Editing Workflow
- Shot list JSON spec: scene id, b-roll intent, caption line, SFX cue.
- Thumbnail concept card: title line, visual metaphor, contrast target.

7. Publishing Workflow
- Manual approval gates only:
  - compliance pass
  - brand pass
  - CTA pass
- Distribution checklist per platform (YouTube, Shorts, Reels, TikTok).

8. Analytics Workflow
- Track: retention, CTR, watch completion, saves/shares, click-outs.
- Weekly loop: top winners -> hook library update -> next sprint priorities.

## Data Objects
- `content_topic`: id, category, demand_score, monetization_tags, risk_level
- `content_script`: topic_id, format, hook_id, body, disclaimer_variant
- `content_asset_manifest`: script_id, voice_profile, broll_plan, thumbnail_plan
- `content_publish_record`: channel, post_url, publish_time, cta_type
- `content_metric_snapshot`: views, retention, ctr, saves, revenue_proxy

## Safety Controls
- No auto-posting, no auto-client messaging.
- Compliance-required disclaimer blocks for monetization/funding advice content.
- Human review required before publish state transition.
