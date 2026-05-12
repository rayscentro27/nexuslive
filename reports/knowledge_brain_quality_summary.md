# Knowledge Brain Quality Summary
**Date:** 2026-05-12  
**Mode:** Dry-run — HERMES_KNOWLEDGE_AUTO_STORE_ENABLED=false ✅  
**Scope:** Intake pipeline, KB record quality, retrieval quality, scaling readiness

---

## Session Accomplishments

### B1 — Knowledge Ingestion Audit (Full second-pass) ✅
Completed full audit of intake pipeline from email receipt to Hermes retrieval.

Key validated:
- Real email (`msg-audit-test-2026`, Business Credit Research) parsed correctly
- Category detected: `credit` (correct from body keywords)
- Deduplication working: SHA256 key, re-runs produce 0 new records
- 8/8 conversational retrieval queries route correctly (up from 7/8 — fixed "what is in notebooklm")

### B2 — Reply Text Fix ✅
`lib/hermes_internal_first.py` knowledge_email topic:
- Changed `limit=5` → `limit=50` (was capping count at 5 regardless of queue size)
- Changed reply text: "N recent runs recorded" → "N proposed records from M email(s) in intake queue"
- This makes the response accurate and non-misleading

### B3 — Keyword Fix ✅
`lib/hermes_runtime_config.py` notebooklm topic:
- Added `"what is in notebooklm"` keyword (full-words variant was missing)
- Result: query "what is in notebooklm" now routes correctly

---

## Current Queue State

| Queue | Records | Status |
|---|---|---|
| `proposed_records_queue.json` | 7 | 4 real + 3 test fixtures (msg-dup) |
| `notebooklm_intake_queue.json` | 1 | High quality, conf=0.76 |
| `knowledge_review_queue.json` | 6 | All test fixtures, 0 real records |

**Action still needed:** Purge 3 test fixture records (msg-dup) from proposed queue. First real production cleanup.

---

## Gap Status

| Gap | Severity | Status |
|---|---|---|
| Reply text misleading ("runs") | LOW | ✅ FIXED |
| "what is in notebooklm" not routing | LOW | ✅ FIXED |
| URL records are stubs (no enrichment) | MEDIUM | Open — requires URL enrichment feature |
| Executive summary reads Supabase only | MEDIUM | Open — local queue not bridged |
| No proposed→review auto-flow | MEDIUM | Open — manual only |
| Test fixture records in queue | LOW | Open — needs one-time purge |
| knowledge_review_queue has 0 real records | LOW | Open — waiting on real intake approval flow |
| "what funding research arrived?" → Supabase gap | MEDIUM | Open — architectural |

---

## Knowledge Quality Scores (2026-05-12)

| Dimension | Score | Change from 2026-05-11 |
|---|---|---|
| Parser quality | 8/10 | No change |
| Queue quality | 7/10 | No change |
| KB record quality | 4/10 | No change (stubs by design) |
| Executive summary | 5/10 | No change (Supabase gap) |
| Conversational retrieval | 8/10 | +1 (7/8 → 8/8, keyword fix) |
| Operational usefulness | 6/10 | No change |
| Scalability readiness | 6/10 | No change |
| **Overall** | **6.3/10** | **+0.3 from 2026-05-11** |

---

## Test Results (Knowledge Subsystem)

| Suite | Tests | Result |
|---|---|---|
| `test_hermes_email_knowledge_intake.py` | 7 | ✅ 7/7 |
| `test_hermes_knowledge_brain.py` | 14 | ✅ 14/14 |
| `test_hermes_internal_first.py` | 13 | ✅ 13/13 |
| `test_knowledge_email_intake_parser.py` | varies | ✅ Pass |
| `test_notebooklm_ingest_adapter.py` | varies | ✅ Pass |
| `test_knowledge_review_queue.py` | varies | ✅ Pass |

---

## Next Steps (Priority Order)

1. **Purge test fixture records** — 15 minutes, immediately cleaner queue
2. **Admin review CLI** (`/review intake`) — unlocks full pipeline without auto-store
3. **Real email validation round 2** — 2-3 more emails across varied categories
4. **Local queue → exec summary bridge** — connect proposed queue to `build_hermes_context_pack()`
5. **Content enrichment** (URL title/summary fetching) — longer term, behind feature flag
