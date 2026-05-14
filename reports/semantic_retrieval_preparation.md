# Nexus Semantic Retrieval Preparation
Date: 2026-05-13

## Overview
Adds concept-map-based semantic expansion and hype detection as a preparation layer for all AI employee knowledge queries. Replaces naive keyword search with domain-aware synonym expansion.

## nexus_semantic_concepts.py

### Domain Concept Maps
| Domain | Key Clusters | Synonym Count |
|--------|-------------|---------------|
| ICT/Trading | silver bullet, liquidity sweep, session timing, NY reversal, market structure, FVG, order block, entry model | 40+ |
| Grants | Hello Alice, SBA, CDFI, AI education, minority-owned, startup | 25+ |
| Funding | LOC, invoice financing, equipment financing, revenue-based | 20+ |
| Business | AI affiliate, digital product, agency model | 15+ |
| Credit | credit building, utilization, personal credit, tradeline | 20+ |

### Functions
- `expand_query(query, domain)` — returns list of synonym terms for supabase ilike expansion
- `detect_hype(text)` → bool — checks 20+ hype signals + 10 scam signals
- `source_trust_score(url)` → 0-100 — returns trust for known domains (sba.gov=95, youtube=60, etc.)
- `get_related_concepts(topic, domain)` → list[str] — returns up to 5 concept labels related to the topic

### Hype Detection Signals (sample)
- "guaranteed returns", "100% success", "zero risk", "make $10000 overnight"
- "secret formula", "banks don't want you to know", "exploit the system"
- Scam: "wire transfer upfront", "advance fee", "pay to receive grant"

## hermes_supabase_first.py Integration
```python
# Hype gate (before routing)
if detect_hype(text):
    return "Nexus flags this as potentially hype-driven content..."

# Semantic expansion
domain_map = {"trading_analyst": "trading", "grant_researcher": "grants", ...}
expanded_terms = expand_query(core_query, domain=domain_map.get(role, ""))
related_concepts = get_related_concepts(core_query, domain=...)
context = {"expanded_terms": expanded_terms[:6], "related_concepts": related_concepts}
```

## Next Step: Vector Search
Current implementation uses ilike with expanded terms. Next evolution:
- Replace `transcript_queue` ilike with pgvector similarity search
- Run `notebooklm_ingest_adapter` on 5 domain notebooks to seed embeddings
- Target: `cosine_similarity > 0.75` threshold

## Commit
- nexus-ai agent-coord-clean → `772b9a2`
- nexus_semantic_concepts.py: NEW (200+ lines)
- hermes_supabase_first.py + research_processing_worker.py: MODIFIED
