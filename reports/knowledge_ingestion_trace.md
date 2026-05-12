# Knowledge Ingestion Workflow Trace
**Date:** 2026-05-12  
**Mode:** Dry-run (no Supabase storage)  
**Context:** Updated trace — includes real email intake from msg-audit-test-2026

---

## Stage-by-Stage Trace

### Stage 1 — Email Received
**Entry point:** `ingest_knowledge_email_dry_run()` or `ingest_gmail_hydrated_email_dry_run()`  
**Status:** ✅ Complete  
- Accepts `sender`, `subject`, `body`, `message_id`
- Gmail format supported via `parse_gmail_hydrated_message()` (multipart MIME handling)
- Real email ingested: `msg-audit-test-2026` (Business Credit Research)

### Stage 2 — Parser
**Function:** `parse_knowledge_email()`  
**Status:** ✅ Complete (7/7 parser tests pass)  
- Extracts: sender email, subject, timestamp, message_id
- Strips HTML: `_strip_html()` handles `<script>`, `<style>`, `<br>`, `<p>` tags
- Deduplication key generated: `SHA256(url|category|email_id)[:24]`

### Stage 3 — Link Extraction
**Functions:** `_urls()`, `_urls_from_html()`  
**Status:** ✅ Complete  
- Regex extraction from plaintext: `https?://[^\s<>()...]+`
- HTML `href` attribute extraction
- YouTube detection: `_youtube()` flags `youtube.com/` and `youtu.be/` links
- URL deduplication: insertion-order preserved, no duplicates

### Stage 4 — Category Detection
**Function:** `_detect_category()`  
**Status:** ✅ Complete  
- Explicit `Category: X` in body takes priority over keyword matching
- Keyword rules for 11 categories
- `msg-audit-test-2026` → `credit` (correctly detected from body keywords)
- `msg-safety-check` → `general` (no category signal — correct fallback)

### Stage 5 — Proposed Record Construction
**Function:** `build_proposed_records()`  
**Status:** ⚠️ Partial — structure correct but URL content is stub  
- Creates one record per URL + one `email_note` record
- URL records: `title="pending_title_from_source"`, `summary="pending_summary_from_source"`, `confidence="low"`
- Note record: contains raw email body (up to 500 chars), `confidence="medium"`
- **Gap:** No content enrichment step — URL records remain stubs permanently

### Stage 6 — Deduplication + Queue Write
**Functions:** `_dedup_key()`, `_load_queue()`, `_save_queue()`  
**Status:** ✅ Complete  
- SHA256 key prevents exact duplicates from same email+URL+category combination
- Queue capped at 1200 records (rolling truncation)
- Deduplication verified: re-running `msg-dup` email produced 3 duplicates detected, 0 new records
- JSON written to `reports/knowledge_intake/proposed_records_queue.json`

### Stage 7 — Intake Report
**Status:** ✅ Complete  
- Markdown report written to `reports/knowledge_intake/YYYYMMDD_HHMMSS_email_knowledge_intake.md`
- Includes: sender, subject, links found, duplicate count, proposed record count, next steps
- 10 report files on disk (7 from 2026-05-10, 3 from 2026-05-12)

### Stage 8 — NotebookLM Queue (Separate Path)
**Status:** ✅ Complete (1 real record present)  
- Manually curated via `reports/knowledge_intake/notebooklm_intake_queue.json`
- Adapter: `lib/notebooklm_ingest_adapter.py`
- Current record: "Funding + Ops Research" → "travel-ready operations" (conf=0.76)
- Takeaways and action items present and meaningful

### Stage 9 — Knowledge Review Queue
**File:** `reports/knowledge_intake/knowledge_review_queue.json`  
**Status:** ⚠️ Test-only — 6 records, all `topic="test"`, `summary="queue test"`  
- Status transitions work: proposed → reviewed → approved
- **Gap:** No real records; no automatic flow from proposed_records → review queue

### Stage 10 — Executive Summary / Context Pack
**Functions:** `build_hermes_context_pack()`, `build_telegram_knowledge_report_context()`  
**Status:** ⚠️ Reads from Supabase only — no local queue integration  
- Returns: 3 recent_knowledge items, 1 funding_insight, 0 credit_insights, 0 compact_summary
- Supabase data is from prior workflow runs (pre-intake pipeline)
- **Gap:** Proposed records in local queue are NOT in executive summary or context pack

### Stage 11 — Hermes Conversational Retrieval
**Function:** `try_internal_first()` → `knowledge_email` or `notebooklm` topics  
**Status:** ✅ Working — 8/8 test queries now routing correctly  
- Routing fixed: "what is in notebooklm" keyword added (was missing, fixed this session)
- "What knowledge emails received" → reads `proposed_records_queue.json`
- "NotebookLM queue" → reads `notebooklm_intake_queue.json`
- "What funding research arrived?" → reads Supabase (known mismatch — architectural gap)

---

## Hidden Failure Points Identified

| Issue | Severity | Location |
|---|---|---|
| No content enrichment step | Medium | `build_proposed_records()` — URL title/summary = stub |
| No proposed→review queue flow | Medium | Manual step; not automated |
| Executive summary reads Supabase only | Medium | `build_hermes_context_pack()` doesn't read local queue |
| knowledge_email reply says "runs" not "records" | Low | Confusing UX — 5 proposed records ≠ 5 ingestion runs |
| knowledge_email limit=5 hardcoded in internal-first | Low | `try_internal_first()` line 131 — should reflect actual count |
| 3 test fixture records in queue (msg-dup) | Low | Should be purged before production use |
| knowledge_review_queue has 0 real records | Low | Only test fixtures present |
| "what funding research arrived?" → Supabase gap | Medium | New credit research not reflected in funding reply |

---

## Timestamp Consistency Check

Real email intakes (2026-05-12):
- `msg-audit-test-2026` — timestamp 01:07:00 → 3 proposed records (2 URL + 1 note)
- `msg-safety-check` — timestamp 01:07:23 → 1 proposed record (1 note, no URLs)
- `msg-dup` re-run — timestamp 13:39:28 → 3 duplicates detected, 0 new records

All timestamps in UTC, consistent, correctly formatted ISO-8601.

---

## Change from Prior Trace (2026-05-11)

| Item | Then | Now |
|---|---|---|
| Real records in proposed queue | 3 (credit) | 4 (credit + general) |
| Intake report files | 9 | 10 (+1 msg-dup re-run today) |
| Retrieval queries matched | 7/8 | 8/8 (fixed "what is in notebooklm") |
| Test fixture records | 3 | 3 (unchanged — still need purge) |
