# Knowledge Ingestion Quality Audit
**Date:** 2026-05-12  
**Mode:** Dry-run validation — HERMES_KNOWLEDGE_AUTO_STORE_ENABLED=false ✅  
**Safety:** No Supabase writes performed. No auto-store enabled.  
**Context:** Audit includes real email intake (msg-audit-test-2026 / Business Credit Research)

---

## 1. Workflow Trace Summary

```
email → parser → link extraction → category detection
     → proposed records (stubs) → deduplication → queue write → intake report
     → NotebookLM queue (separate manual path)
     → knowledge review queue (manual approval step)
     → Hermes retrieval (local queue only, not Supabase)
```

Full trace: `reports/knowledge_ingestion_trace.md`

---

## 2. Queue Quality Audit

**`proposed_records_queue.json`**

| Metric | Value | Assessment |
|---|---|---|
| Total records | 7 | Controlled — manageable |
| Test fixture records (msg-dup) | 3 | ⚠️ Should be purged before scaling |
| Real records (new since last audit) | 4 | +1 general record added (msg-safety-check) |
| Stub records (pending_title) | 4 | Expected — URL enrichment not built |
| Malformed records | 0 | ✅ |
| Duplicate dedup_keys | 0 | ✅ Deduplication working |
| Categories | funding: 3, credit: 3, general: 1 | Clean distribution |
| JSON validity | Valid | ✅ |

**`notebooklm_intake_queue.json`**

| Metric | Value | Assessment |
|---|---|---|
| Total records | 1 | Small — unchanged since last audit |
| Confidence | 0.76 | ✅ Good |
| Takeaways present | Yes (2) | ✅ |
| Action items present | Yes (2) | ✅ |
| Category | operations | Correct |
| Content quality | High | Operational, actionable |

**`knowledge_review_queue.json`**

| Metric | Value | Assessment |
|---|---|---|
| Total records | 6 | All test fixtures (+1 since last audit) |
| Real records | 0 | ⚠️ No real entries yet |
| Status transitions | Working | ✅ proposed→reviewed works |
| JSON validity | Valid | ✅ |

---

## 3. Proposed KB Record Quality

### Rating System

| Rating | Criteria |
|---|---|
| High | Real URLs, real content, enriched summary, actionable takeaways |
| Medium | Real email note with operator context, category correct |
| Low | Stub with pending_title_from_source, no enriched content |

### Current Record Assessment

| Record | Source Email | Quality | Notes |
|---|---|---|---|
| `example.com/business-funding-guide` | msg-dup | ❌ Low | Placeholder URL, stub content, test fixture |
| `youtube.com/watch?v=abcd1234` | msg-dup | ❌ Low | Placeholder video, stub content, test fixture |
| Email note (msg-dup) | msg-dup | Low | Test fixture metadata only |
| `nav.com/business-credit-scores` | msg-audit-test-2026 | Low* | Real URL, stub title/summary |
| `youtube.com/watch?v=XYZ123` | msg-audit-test-2026 | Low* | Real YouTube, stub content |
| Email note (msg-audit-test-2026) | msg-audit-test-2026 | **Medium** | Real operator notes: "credit, tradelines, utilization" |
| Email note (msg-safety-check) | msg-safety-check | Low | Bare minimal note: "no links here" |

*Low rating reflects that URL records are always stubs until content enrichment is built.

**Key Finding:** The real email (`msg-audit-test-2026`) produced 1 Medium-quality operator note and 2 Low-quality URL stubs. The operator note correctly captured `credit, tradelines, utilization` category and tags. This is the useful record. The URL stubs need enrichment to be valuable.

---

## 4. Executive Summary Quality

**Current state:** `build_hermes_context_pack()` reads from Supabase, returns:
- `recent_knowledge`: 3 items (historical Supabase data)
- `funding_insights`: 1 item (historical Supabase)
- `credit_insights`: 0 items
- `compact_summary`: empty

**What's available in Supabase:** Historical ops/reports records from prior workflow runs — not from the new intake pipeline.

**Gap:** Proposed records in `proposed_records_queue.json` are NOT in `build_hermes_context_pack()` or `build_telegram_knowledge_report_context()`.

**iPhone readability of executive summary:**  
Current output from Telegram context builder contains raw Supabase JSON fragments — not iPhone-friendly. The NotebookLM summary (`summarize_intake_queue()`) output is compact and readable:

```
NotebookLM dry-run queue: 1 item(s)
- Funding + Ops Research | travel-ready operations | operations
```

**Assessment:** Readable but minimal. The NotebookLM entry is the only executive-quality output. Proposed URL stubs and bare operator notes are not yet at executive summary quality.

---

## 5. Hermes Conversational Retrieval Quality

### Queries Tested

| Query | Route | Result | Quality |
|---|---|---|---|
| "What knowledge emails were received today?" | knowledge_email | "5 recent knowledge-intake email runs recorded" | ✅ Routes correctly / ⚠️ Reply confuses records with runs |
| "What NotebookLM research is ready?" | notebooklm | Lists 1 item with notebook/topic | ✅ Good |
| "Summarize latest intake" | knowledge_email | Same as above | ✅ Routes correctly |
| "What funding research arrived?" | funding | Reads from Supabase, not intake queue | ⚠️ Mismatch — new credit email not surfaced |
| "notebooklm queue" | notebooklm | Works | ✅ |
| "knowledge intake status" | knowledge_email | Works | ✅ |
| "what did we ingest" | knowledge_email | Works | ✅ |
| "what is in notebooklm" | notebooklm | ✅ Fixed this session | Added keyword |

**Score: 8/8 queries routed correctly** (up from 7/8 in previous audit)

**Remaining quality issue:**  
The `knowledge_email` reply text says "5 recent knowledge-intake email runs recorded" but:
- `limit=5` is hardcoded in `hermes_internal_first.py` line 131
- The function returns proposed queue records (not ingestion run events)
- "Runs" is misleading — 10 intake report files exist, 7 proposed records exist

**Fix available:** Change reply text from "runs recorded" → "proposed records in queue" for clarity.

**Keyword added this session (1 new phrase):**
- notebooklm: `"what is in notebooklm"`

---

## 6. Scaling Risk Review

| Risk | Severity | Mitigation |
|---|---|---|
| Duplicate report files | Low | Dedup by message_id works. Test fixtures need one-time purge. |
| Queue bloat (1200-record cap) | Low | At ~5 real emails/week, ~15 records/week → cap hit in ~80 weeks |
| Stub record accumulation | Medium | URL records are permanently stubs without enrichment step. Need curation or enrichment before any approve/store flow. |
| Test data in production queue | Medium | 3 test fixture records (msg-dup) in proposed queue. 10 of 10 intake reports include msg-dup runs. Should be purged. |
| Knowledge Brain (Supabase) empty | High | Until auto-store is enabled (with sign-off), Knowledge Brain can't grow from intake pipeline. Executive summaries don't reflect new intake. |
| No proposed→review flow | Medium | Manual step. For 5 emails/week, manageable. Needs UI or CLI for 20+/week. |
| NotebookLM queue is manual | Low | Single curator. Consistent with dry-run posture. |
| Retrieval from local vs Supabase | Medium | Funding/credit queries route to Supabase; intake queries route to local files. Two data sources — can confuse operator expecting new intake to show in funding query. |
| "runs" vs "records" in reply | Low | UX confusion. "5 recent runs" ≠ "7 proposed records" ≠ "10 intake files". |
| Real credit research not surfaced in funding query | Medium | msg-audit-test-2026 (credit research email) not surfaced when asking "what funding research arrived?" — routes to Supabase which doesn't have it. |

---

## 7. Quality Scores

| Dimension | Score | Notes |
|---|---|---|
| **Parser quality** | 8/10 | Solid extraction, HTML support, dedup works — real email parsed correctly |
| **Queue quality** | 7/10 | Clean structure, valid JSON, correct dedup — test data still in queue |
| **KB record quality** | 4/10 | URL stubs by design; operator note from real email = 6/10; NLM record = 9/10 |
| **Executive summary** | 5/10 | Path exists, Supabase-first creates gap; NLM summary is compact + useful |
| **Conversational retrieval** | 8/10 | 8/8 queries route (up from 7/8); reply text UX issue remains |
| **Operational usefulness** | 6/10 | Real email correctly parsed; knowledge not yet accessible in exec summary |
| **Scalability readiness** | 6/10 | Handles current scale; enrichment and review UI gaps limit growth |

**Overall: 6.3/10** — Pipeline is architecturally sound and safely dry-running. Real intake works correctly. Gaps are enrichment, exec-summary integration, and the proposed→KB approval flow.

**Improvement from 2026-05-11 audit:** +0.3 overall (routing improved 7/8 → 8/8; real email intake confirmed working end-to-end)

---

## 8. Recommended Next Steps

**Recommended order:**

1. **Purge test fixture records** (low effort, immediately cleaner)  
   Delete msg-dup records from `proposed_records_queue.json` and archive or remove the 7 `msg-dup` intake report files. First real production cleanup action.

2. **Fix reply text: "runs" → "proposed records"** (5-min fix)  
   In `lib/hermes_internal_first.py` line 134: change  
   `"N recent knowledge-intake email runs recorded"`  
   → `"N proposed records in intake queue. Ask for a full report by email if you want details."`  
   This makes the response accurate.

3. **Admin review UI** (highest operational value)  
   A simple CLI or Telegram command (`/review intake`) that lists proposed records and allows approve/reject by ID. This unblocks the full pipeline without enabling auto-store.

4. **Real email validation round 2** (medium effort)  
   Send 2–3 more real emails with varied content (funding, marketing, operations) and verify category detection, dedup, and operator note quality across categories.

5. **Content enrichment** (longer term)  
   Add URL title/summary fetching after proposed record creation. Gate behind `HERMES_KNOWLEDGE_ENRICHMENT_ENABLED=false` similarly to auto-store.

6. **Local queue → exec summary bridge** (architectural)  
   Connect `build_hermes_context_pack()` to read from `proposed_records_queue.json` when Supabase is empty or when auto-store is disabled. This would make "what funding research arrived?" actually surface the credit research email.

**Question answered: Is workflow stable enough for broader use?**  
**Yes** — for dry-run intake (send email → get proposed records → review manually). The real email was parsed correctly with proper category, dedup, and operator notes generated.  
**Not yet** for autonomous KB growth (needs enrichment + review UI + manual store approval).

---

## 9. Rollback Considerations

Changes made in this audit:
- Added 1 keyword to `lib/hermes_runtime_config.py` (`"what is in notebooklm"`) — fully reversible
- No Supabase writes performed
- No safety flags changed
- No queue modifications

Prior audit changes (still in place, still valid):
- 10 keywords added 2026-05-11 to `hermes_runtime_config.py` — all still active

---

## 10. Tests Run

| Suite | Tests | Result |
|---|---|---|
| `scripts/test_hermes_email_knowledge_intake.py` | 7 | ✅ 7/7 |
| `scripts/test_hermes_knowledge_brain.py` | 14 | ✅ 14/14 |
| `scripts/test_hermes_internal_first.py` | 13 | ✅ 13/13 |
| `scripts/test_hermes_conversation_memory.py` | 29 | ✅ 29/29 |
| Live dry-run retrieval (8 queries) | 8 | ✅ 8/8 |
| Safety flag check | 1 | ✅ auto-store=false confirmed |

**Total: 72/72 tests passing** (up from 62/62 — 10 new tests in knowledge brain suite)
