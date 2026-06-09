# Nexus Source Intake

Use the unified router to send sources into the existing Nexus review path without creating a second ingestion system.

Canonical path:
- `transcript_queue`
- `knowledge_items`
- review / approval
- `scripts/bridge_approved_knowledge_to_nexus_os.py`

Default behavior:
- dry-run by default
- no writes unless `--apply`
- no publishing
- no email sending
- no social posting
- no bridge apply until knowledge is approved

## Add A YouTube Video Link

Dry-run:

```bash
cd ~/nexus-ai
python3 scripts/nexus_source_intake_router.py --input "https://www.youtube.com/watch?v=VIDEO_ID" --type youtube_video --dry-run
```

Apply:

```bash
cd ~/nexus-ai
python3 scripts/nexus_source_intake_router.py --input "https://www.youtube.com/watch?v=VIDEO_ID" --type youtube_video --apply
```

What it does:
- routes through the existing email-style intake logic
- creates `transcript_queue` review records
- creates proposed `knowledge_items`
- does not publish or bridge automatically

## Add A YouTube Channel

Dry-run:

```bash
cd ~/nexus-ai
python3 scripts/nexus_source_intake_router.py --input "https://www.youtube.com/@channel" --type youtube_channel --dry-run
```

Apply:

```bash
cd ~/nexus-ai
python3 scripts/nexus_source_intake_router.py --input "https://www.youtube.com/@channel" --type youtube_channel --apply
```

What it does:
- registers the channel in `docs/reports/youtube/source_registry.json`
- keeps it in a review/intelligence lane
- does not ingest the full channel automatically

Next safe follow-up:

```bash
cd ~/nexus-ai
python3 scripts/run_youtube_intelligence_cycle.py --url "https://www.youtube.com/@channel" --dry-run
```

## Add A YouTube Playlist

Dry-run:

```bash
cd ~/nexus-ai
python3 scripts/nexus_source_intake_router.py --input "https://www.youtube.com/playlist?list=PLAYLIST_ID" --type youtube_playlist --dry-run --limit 3
```

Apply:

```bash
cd ~/nexus-ai
python3 scripts/nexus_source_intake_router.py --input "https://www.youtube.com/playlist?list=PLAYLIST_ID" --type youtube_playlist --apply --limit 3
```

What it does:
- registers the playlist for review
- does not mass-ingest the playlist automatically
- keeps the next step explicit and limited

## Send By Email

Current manual processing command:

```bash
cd ~/nexus-ai
python3 scripts/process_knowledge_emails_once.py --dry-run
```

Apply:

```bash
cd ~/nexus-ai
python3 scripts/process_knowledge_emails_once.py --apply
```

Email can contain:
- a YouTube video link
- a YouTube channel link
- transcript text
- NotebookLM note text

What it does:
- parses links and notes
- creates `transcript_queue` review records
- creates proposed `knowledge_items`
- does not bridge automatically

## Use NotebookLM Export

Dry-run:

```bash
cd ~/nexus-ai
python3 scripts/nexus_source_intake_router.py --file "/path/to/notebooklm_export.md" --type notebooklm_export --dry-run
```

Apply:

```bash
cd ~/nexus-ai
python3 scripts/nexus_source_intake_router.py --file "/path/to/notebooklm_export.md" --type notebooklm_export --apply
```

Status / pending review:

```bash
cd ~/nexus-ai
python3 scripts/nexus_notebooklm_ops.py status --pending-review
```

What it does:
- routes through NotebookLM ingest adapter logic
- creates proposed `knowledge_items`
- creates `transcript_queue` placeholders for linked YouTube sources
- does not bridge automatically

## Drop Transcript Files

Canonical inbox:
- `~/nexus-ai/inbox/youtube_transcripts/`

Dry-run inbox scan:

```bash
cd ~/nexus-ai
python3 scripts/ingest_local_youtube_transcripts_once.py --dry-run --limit 3
```

Single file through the unified router:

```bash
cd ~/nexus-ai
python3 scripts/nexus_source_intake_router.py --file "/path/to/transcript.md" --type transcript_file --dry-run
```

Apply:

```bash
cd ~/nexus-ai
python3 scripts/nexus_source_intake_router.py --file "/path/to/transcript.md" --type transcript_file --apply
```

What it does:
- creates `transcript_queue` rows
- creates proposed `knowledge_items`
- keeps everything review-first

## Review Knowledge Items

Review target:
- `knowledge_items` where `status='proposed'`
- `knowledge_items` where `metadata.review_required=true`

Review before bridge:
- confirm the summary is accurate
- confirm the source is relevant
- confirm the campaign match is correct
- confirm compliance language is safe
- approve only the rows that should affect Nexus OS

## Bridge Approved Knowledge Into Nexus OS

Dry-run:

```bash
cd ~/nexus-ai
python3 scripts/bridge_approved_knowledge_to_nexus_os.py --dry-run --source knowledge_items --limit 10
```

Apply a very small approved batch:

```bash
cd ~/nexus-ai
python3 scripts/bridge_approved_knowledge_to_nexus_os.py --apply --source knowledge_items --limit 3
```

Optional content drafts require explicit choice:
- do not add `--create-content` unless Ray wants draft-only content suggestions

## Hermes Command Aliases

No new Telegram routing was added in this pass.

Use these shell commands as the safe operator aliases:
- `python3 scripts/nexus_source_intake_router.py --input "<url>" --dry-run`
- `python3 scripts/nexus_source_intake_router.py --file "/path/to/file.md" --dry-run`

Suggested natural-language aliases to document for Hermes later:
- `ingest source <url>`
- `review source <url>`
- `add YouTube source <url>`
- `add channel <url>`
- `process NotebookLM export <file>`

## What Not To Do

- do not build a new transcript importer
- do not write directly to Nexus OS tables from raw links
- do not auto-approve `knowledge_items`
- do not bridge raw or unreviewed transcript material
- do not mass-ingest YouTube channels or playlists without explicit apply and limit
- do not publish, email, post, or enable ad spend from intake tools
