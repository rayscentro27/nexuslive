# NotebookLM Digest Testing + Validation
**Date:** 2026-05-12  
**Mode:** Dry-run — no auto-store

---

## 1. How the NotebookLM Workflow Currently Works

NotebookLM integration in Nexus is a **manual curation pipeline** — not automated.

```
Operator reads source material (article, email, research)
    ↓
Manually curates key insights into notebooklm_intake_queue.json
    ↓
Hermes reads queue via try_internal_first() → notebooklm topic
    ↓
Conversational retrieval: "What NotebookLM research is ready?"
```

There is NO automatic digest generation. NotebookLM-style digests are written manually by the operator into the queue file. Hermes can retrieve and summarize what's in the queue.

---

## 2. Current Queue State

**File:** `reports/knowledge_intake/notebooklm_intake_queue.json`  
**Records:** 1

```
Title:    "Funding + Ops Research"
Topic:    "travel-ready operations"
Category: operations
Confidence: 0.76
Takeaways: 2 (present)
Action items: 2 (present)
```

This is high-quality — structured takeaways and action items present, confidence above 0.7, category correct.

---

## 3. Hermes Retrieval: Verified Working

| Query | Result |
|---|---|
| "What NotebookLM research is ready?" | Lists 1 item with notebook + topic ✅ |
| "Summarize NotebookLM intake queue" | Returns digest summary ✅ |
| "NotebookLM queue status" | Routes correctly ✅ |
| "What is in notebooklm?" | Routes correctly ✅ (fixed 2026-05-12) |
| "notebook research" | Routes correctly ✅ |
| "knowledge queue" | Routes correctly ✅ |

**All 6 notebooklm query patterns route correctly.**

---

## 4. How to Add a New NotebookLM Digest Entry

Edit `reports/knowledge_intake/notebooklm_intake_queue.json` and add a record:

```json
{
  "id": "nlm-YYYYMMDD-001",
  "title": "Title of research or source",
  "topic": "core topic or concept",
  "category": "funding | credit | operations | marketing | general",
  "confidence": 0.80,
  "source_url": "https://optional-source-url",
  "summary": "2-3 sentence summary of the key finding.",
  "takeaways": [
    "Key takeaway 1",
    "Key takeaway 2"
  ],
  "action_items": [
    "Specific action for Nexus based on this research",
    "Second action item"
  ],
  "inserted_at": "2026-05-12T00:00:00+00:00"
}
```

**After adding:** Test retrieval by asking Hermes "What NotebookLM research is ready?"

---

## 5. How to Test Digest Quality

### Recommended test prompts
1. "What NotebookLM research is ready?" → Should list all items with topic
2. "Summarize the latest NotebookLM intake" → Should give concise digest
3. "What knowledge queue items are pending?" → Should route to notebooklm topic
4. "What is the funding research in notebooklm?" → Tests category-specific recall (currently: returns all items, no category filter)

### Quality criteria
| Criterion | Pass |
|---|---|
| Routes to notebooklm topic | ✅ |
| Returns correct record count | ✅ |
| Shows topic/notebook name | ✅ |
| Summarizes key takeaways | ⚠️ Partial — depends on LLM fallback |
| Category-specific filtering | ❌ Not implemented — returns all |

---

## 6. Gaps

| Gap | Severity | Description |
|---|---|---|
| No automatic digest generation | LOW | By design — manual curation is the posture |
| Category-specific NotebookLM queries | LOW | "What funding research is in NotebookLM?" treats as general |
| No expiry on old entries | LOW | Old research accumulates; no age-out logic |
| Confidence threshold not enforced | LOW | Low-confidence entries (< 0.5) are not filtered out |

---

## 7. Recommended Next Steps

1. Add 2-3 real research entries to the queue (funding/credit sources)
2. Test retrieval quality for each after adding
3. Consider adding category-filter to the notebooklm topic handler
4. Set a quarterly review cadence to prune stale entries
