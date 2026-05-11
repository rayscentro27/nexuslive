# Opportunity Scoring

## Objective
Provide a practical, low-cost ranking model for opportunities detected from Nexus Brain research outputs.

No heavy ML is required for this phase. The model is heuristic, transparent, and easy to tune.

## Score Range
- `0` to `100`
- Default inclusion threshold: `45`

Priority bands:
- `critical`: `>= 78`
- `high`: `62 - 77`
- `medium`: `45 - 61`
- `low`: `< 45`

## Scoring Components
Total score is the sum of these weighted components:

1. `repetition_score` (max 25)
- Higher when the same type/niche appears repeatedly across artifacts/claims/clusters.

2. `source_authority_score` (max 15)
- Higher with stronger source mix and recognized authoritative signals.
- Mixed evidence types (artifact + claim + hypothesis) are rewarded.

3. `novelty_score` (max 15)
- Higher for emerging/underserved/whitespace/policy-shift language.

4. `actionability_score` (max 20)
- Higher when wording implies immediate execution steps (pilot, submit, automate, launch).

5. `monetization_score` (max 15)
- Higher for recurring revenue/retainer/grant funding quality.

6. `urgency_score` (max 10)
- High urgency receives maximum weight.

7. `confidence_adjustment` (max 10)
- Derived from normalized confidence (0..1) across aggregated signals.

## Why this Model Fits Nexus
- Transparent scoring supports human review and trust.
- Low compute cost for Mac Mini workflows.
- Strong alignment with owner routing (GrantWorker, OpportunityWorker, CRM/Product, Ops/Automation).
- Easy to tune without schema changes.

## Tuning Guidance
Tune these first before introducing complexity:
- `--min-score` threshold
- repetition bucket cutoffs
- urgency keyword list
- monetization keyword list

## Example
A repeated grant signal with deadline urgency and clear eligibility usually scores high due to:
- high repetition
- high urgency
- strong actionability
- grant monetization hint

A weak single-source niche mention with low confidence will rank lower and remain informational.

## Safety Notes
- This score does not auto-execute actions.
- Outputs remain recommendations until reviewed by the responsible owner/worker.
- No trading execution or client PII handling is introduced by this model.
