# Content Employee — Windows / Oracle Contract

Mac Mini side: Nova Media worker produces scripts, audio, asset manifests.
Windows side: must create these tables + Oracle API endpoints for approval flow.

---

## Tables to Create (run on Supabase from Windows)

```sql
-- Content request lifecycle tracker
CREATE TABLE IF NOT EXISTS content_requests (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id       text        UNIQUE NOT NULL,
  topic            text        NOT NULL,
  content_type     text        NOT NULL,  -- instagram_reel | tiktok_short | youtube_short | youtube_training
  niche            text        NOT NULL,
  target_platforms text[]      DEFAULT '{}',
  requested_by     text        DEFAULT 'nova_media',
  status           text        NOT NULL DEFAULT 'topic_received',
  -- status values: topic_received | script_generated | transcript_ready | audio_ready
  --                assets_manifest_ready | needs_review | approved | publish_ready | rejected
  approved_by      text,
  approved_at      timestamptz,
  metadata         jsonb       DEFAULT '{}',
  created_at       timestamptz DEFAULT now(),
  updated_at       timestamptz DEFAULT now()
);

-- Scripts produced by Nova Media
CREATE TABLE IF NOT EXISTS content_scripts (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  script_id    text        UNIQUE NOT NULL,
  content_id   text        REFERENCES content_requests(content_id),
  content_type text        NOT NULL,
  script_text  text        NOT NULL,
  provider     text        DEFAULT 'openclaw',  -- openclaw | fallback_template
  word_count   integer     DEFAULT 0,
  status       text        DEFAULT 'draft',     -- draft | approved | rejected
  created_at   timestamptz DEFAULT now()
);

-- Media assets (audio, thumbnails, b-roll manifests)
CREATE TABLE IF NOT EXISTS content_assets (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id   text        REFERENCES content_requests(content_id),
  asset_type   text        NOT NULL,  -- audio_narration | thumbnail | b_roll | caption_srt
  local_path   text,                  -- Mac Mini local path (for reference only)
  remote_url   text,                  -- future: CDN/storage URL after upload
  provider     text,                  -- macos_say | gtts | manual | ffmpeg
  status       text        DEFAULT 'ready',  -- ready | failed | pending_upload
  error        text,
  created_at   timestamptz DEFAULT now()
);

-- Publish targets and outcomes (never auto-filled by Mac Mini)
CREATE TABLE IF NOT EXISTS content_publish_log (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content_id   text        REFERENCES content_requests(content_id),
  platform     text        NOT NULL,  -- instagram | tiktok | youtube
  published_at timestamptz,
  post_url     text,
  published_by text,                  -- who triggered publish
  notes        text,
  created_at   timestamptz DEFAULT now()
);
```

---

## Indexes

```sql
CREATE INDEX IF NOT EXISTS content_requests_status ON content_requests(status);
CREATE INDEX IF NOT EXISTS content_requests_content_type ON content_requests(content_type);
CREATE INDEX IF NOT EXISTS content_scripts_content_id ON content_scripts(content_id);
CREATE INDEX IF NOT EXISTS content_assets_content_id ON content_assets(content_id);
```

---

## Oracle API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/content` | List content requests (filter by status, content_type) |
| GET | `/api/content/:content_id` | Get one content request + scripts + assets |
| GET | `/api/content/needs-review` | All items with `status = needs_review` |
| PATCH | `/api/content/:content_id/approve` | Set `status = publish_ready`, set `approved_by` |
| PATCH | `/api/content/:content_id/reject` | Set `status = rejected` |
| POST | `/api/content/request` | (Optional) Create content request from UI rather than Mac Mini |
| POST | `/api/content/:content_id/publish` | Record publish event to content_publish_log |

---

## Approval Contract (Human-in-the-Loop)

Nova Media NEVER auto-publishes.
The approval flow is:
1. Mac Mini produces → status = `needs_review` + Telegram alert sent
2. Founder reviews script + audio in dashboard/portal
3. Founder approves → Oracle API PATCH `/api/content/:id/approve`
4. Oracle sets status = `publish_ready`, records approved_by
5. Founder manually publishes or schedules in social tool

Mac Mini `stage_approve()` can be called via CLI:
```bash
python3 -m content_employee.nova_media --approve <content_id>
```
But this is for local dev only. Production approvals should come through Oracle API.

---

## Dashboard Surface (Founder Panel)

Content review panel should show:
- `status = needs_review` list
- Script text preview
- Audio player (if local path accessible or uploaded to storage)
- Asset manifest checklist
- Approve / Reject buttons → calls Oracle API

---

## Mac Mini Local Output Structure

```
~/nexus-ai/content_employee/output/
└── <content_id>/
    ├── narration.aiff          # macOS say output
    ├── narration.mp3           # gTTS output (if say unavailable)
    └── asset_manifest.json     # required assets for manual production
```

---

## Free/Low-Cost Architecture Notes

| Component | Current Provider | Cost | Install |
|---|---|---|---|
| Script generation | OpenClaw (local Codex OAuth) | Free | Already running |
| TTS / narration | macOS `say` | Free, built-in | Already available |
| TTS fallback | gTTS | Free (needs network) | `pip install gtts` |
| Transcript extraction | yt-dlp | Free | Already installed |
| Video assembly | Manual (CapCut/DaVinci) | Free | Human step |
| Video assembly (future) | ffmpeg | Free | `brew install ffmpeg` |
| Image/thumbnail | Manual | Free | Human step |
| Image (future) | Pillow | Free | `pip install Pillow` |

**Never hardcoded to a paid video AI vendor.** All providers in `tooling_adapter.py` are pluggable.
