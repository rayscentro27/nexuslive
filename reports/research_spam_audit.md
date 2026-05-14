# Research Spam Audit
Date: 2026-05-13

## Summary
Full audit of knowledge_items, research_requests, and transcript_queue to identify spam, test artifacts, and recursive escalation noise.

## knowledge_items Audit Results

| ID | Status (before) | Quality | Title | Finding |
|----|----------------|---------|-------|---------|
| 01653c10 | approved | 72 | ICT Silver Bullet Trading — NitroTrades | ✅ LEGITIMATE — keep |
| 0c214071 | approved | 75 | hello alice small business grant | ✅ LEGITIMATE — keep |
| e63caf61 | approved → archived | 75 | grants for AI education businesses | ❌ SPAM — "No vetted Nexus knowledge found" content |
| 448a0c16 | approved → archived | 75 | lenders for startups with low revenue | ❌ SPAM — empty content |
| f9a13fa7 | approved → archived | 75 | AI affiliate automation model | ❌ SPAM — empty content |
| 8924346e | approved → archived | 75 | ICT silver bullet strategy | ❌ SPAM — empty content |
| a898a9fe | approved → archived | 85 | Can Nexus research the ICT silver bullet strategy? | ❌ SPAM — empty content |
| 00f59b29 | approved → archived | 85 | What does Nexus know about the ICT silver bullet? | ❌ SPAM — empty content |
| ef7bb351 | approved → archived | 85 | Can Nexus review AI automation affiliate opportunities? | ❌ SPAM — empty content |
| 221658ae | approved → archived | 85 | What funding paths has Nexus researched for startups? | ❌ SPAM — empty content |
| bf433142 | approved → archived | 85 | Can Nexus find grants for AI education businesses? | ❌ SPAM — empty content |
| a0a19677 | approved → archived | 80 | YouTube video research: def12345678 | ❌ PLACEHOLDER — fake URL + fabricated content |

### Root Cause
`research_processing_worker.py` auto-generates knowledge_items from research tickets. When no model synthesis is available, it falls back to `"No vetted Nexus knowledge found for: {topic}"`. These fallback strings exceeded the 50-char minimum and were stored as `proposed` — then were incorrectly approved (quality score elevated to 75-85) during a prior mass-approval pass.

## research_requests Audit Results

| ID | Status (before) | Topic | Finding |
|----|----------------|-------|---------|
| 166ced54 | needs_review → cancelled | What grant opportunities has Nexus researched? | ❌ RECURSIVE — Hermes self-query |
| 8b1b5fb3 | needs_review → cancelled | What trading research is available internally? | ❌ RECURSIVE — Hermes self-query |
| 32e7e595 | needs_review → cancelled | What opportunities are Nexus validated? | ❌ RECURSIVE — Hermes self-query |
| 96de6be6 | needs_review → cancelled | What new knowledge was recently approved? | ❌ RECURSIVE — Hermes self-query |

12 remaining tickets (10 needs_review, 2 submitted) are legitimate research backlog — kept.

## transcript_queue Audit Results

| Count | Status | Domain | Notes |
|-------|--------|--------|-------|
| 10 | needs_transcript | trading | Real YouTube URLs — legitimate queue |
| 2 | ready | trading | def12345678 placeholder URL — test artifact |
| 1 | ready | trading | @nitrotrades channel — legitimate |

No deletions from transcript_queue — placeholder rows are inert and don't affect Hermes retrieval.

## Post-Cleanup State

- **Approved knowledge_items:** 2 (from 12) — clean, legitimate only
- **Cancelled research_tickets:** 4 (recursive) — removed from needs_review backlog
- **Total knowledge_items archived:** 10
