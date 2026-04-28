# YouTube Email Experiments

Turns YouTube-backed `research_artifacts` into draft email experiments so we can
test which subjects, hooks, and framings actually create replies and revenue.

Worker:

- `research_intelligence/email_experiment_engine.py`

Migration:

- `supabase/migrations/20260425150000_youtube_email_experiments.sql`

Usage:

```bash
python3 -m research_intelligence.email_experiment_engine --limit 5
```

What it does:

1. Reads recent `research_artifacts` rows where `source_type = youtube_channel`
2. Creates one `video_email_experiments` row per chosen video
3. Creates one draft `email_campaigns` row per experiment
4. Creates three draft `email_variants` rows per campaign:
   - `CURIOSITY`
   - `CONTRARIAN`
   - `PLAYBOOK`
5. Leaves everything in draft/manual-review status

Tables:

- `video_email_experiments`
  - one experiment brief per video/topic
- `email_campaigns`
  - base campaign shell for the experiment
- `email_variants`
  - actual draft subject lines and bodies
- `email_send_events`
  - future provider/webhook or manual event logging
- `email_experiment_results`
  - rollup metrics for comparing winners

Important boundary:

- This worker does **not** send email.
- It only stages drafts so we can inspect them, send intentionally, and then
  measure outcomes.

Current intent:

- use YouTube videos across different subjects as the raw idea source
- convert each video into 3 email angles
- compare which topics and hooks earn replies, clicks, and conversions
