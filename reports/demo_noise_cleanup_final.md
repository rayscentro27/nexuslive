# Demo Noise Cleanup — Final
Date: 2026-05-13

## Status: COMPLETE ✅ (completed in prior pass)

## What Was Cleaned

### knowledge_items (10 archived)

All 10 had content "No vetted Nexus knowledge found for: [query]" — auto-generated empty fallback from research_processing_worker.py when no model synthesis was available. These were incorrectly approved at q=75-85 during a mass-approval pass.

| ID | Title | Previous Status |
|----|-------|----------------|
| e63caf61 | grants for AI education businesses | approved q=75 → archived |
| 448a0c16 | lenders for startups with low revenue | approved q=75 → archived |
| f9a13fa7 | AI affiliate automation model | approved q=75 → archived |
| 8924346e | ICT silver bullet strategy | approved q=75 → archived |
| a898a9fe | Can Nexus research the ICT silver bullet strategy? | approved q=85 → archived |
| 00f59b29 | What does Nexus know about the ICT silver bullet? | approved q=85 → archived |
| ef7bb351 | Can Nexus review AI automation affiliate opportunities? | approved q=85 → archived |
| 221658ae | What funding paths has Nexus researched for startups? | approved q=85 → archived |
| bf433142 | Can Nexus find grants for AI education businesses? | approved q=85 → archived |
| a0a19677 | YouTube video research: def12345678 | approved q=80 → archived (placeholder URL) |

### research_requests (4 cancelled)

Recursive operational Hermes queries that should never become research tickets:

| Topic | Action |
|-------|--------|
| What grant opportunities has Nexus researched? | cancelled |
| What trading research is available internally? | cancelled |
| What opportunities are Nexus validated? | cancelled |
| What new knowledge was recently approved? | cancelled |

## Systemic Fixes Applied

1. `research_processing_worker.py`: Never propose knowledge when content is the empty-result fallback
2. `hermes_supabase_first.py`: Operational query guard — 10 patterns blocked from ticket creation
3. `hermes_supabase_first.py`: Empty content suppression — "No vetted" text filtered from retrieval
4. `scripts/cleanup_spam.py`: Safe archive tool (dry-run default, explicit UUIDs)

## Post-Cleanup State

| Table | Before | After |
|-------|--------|-------|
| knowledge_items (approved) | 12 | 2 |
| knowledge_items (archived) | 1 | 11 |
| research_requests (cancelled) | 0 | 4 |

## Safety

- Dry-run executed before apply ✅
- Explicit UUIDs only (no wildcards) ✅
- 2 legitimate approved records preserved: NitroTrades ICT + Hello Alice Grant ✅
- transcript_queue untouched ✅
- NEXUS_DRY_RUN=true unchanged ✅
