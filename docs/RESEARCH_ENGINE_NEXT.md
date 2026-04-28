# Research Engine Next

Target flow:

1. Ingest source material
   - YouTube transcript
   - article / website
   - manual operator notes

2. Digest and classify
   - trading
   - business opportunity
   - grant / funding
   - credit / operations

3. Score and normalize
   - deterministic score for quality
   - domain-specific viability score
   - confidence score

4. Hermes recommendation packet
   - approve / review / reject
   - thesis
   - execution plan
   - profitability path
   - backend handoff tasks

5. Operator approval
   - pending
   - approved
   - rejected

6. Backend employee handoff
   - website structure
   - CRM / analytics
   - offer pages
   - launch checklist

Repo foundation added:

- `research_intelligence/recommendation_packet_engine.py`
  - turns `business_opportunities` and `reviewed_signal_proposals` into structured recommendation packets
- `supabase/migrations/20260425123000_research_recommendations.sql`
  - unified `research_recommendations` table for pending and approved packets

Intended use:

```bash
python3 -m research_intelligence.recommendation_packet_engine --domain business --limit 5
python3 -m research_intelligence.recommendation_packet_engine --domain trading --limit 5
```

What this unlocks:

- Business ideas can now carry a launch plan and profitability path, not just a score.
- Trading ideas can now carry a single operator-facing packet with risk/replay context.
- Once a row is marked `approval_status='approved'`, backend workers can consume `backend_handoff`.

Recommended next build steps:

1. Add a worker that watches `research_recommendations` for `approval_status='approved'`.
2. Route approved `business` rows into a website/ops implementation queue.
3. Route approved `trading` rows into the paper-trader promotion path.
4. Extend ingestion to non-YouTube sources so the same packet flow works for websites and manual notes.
