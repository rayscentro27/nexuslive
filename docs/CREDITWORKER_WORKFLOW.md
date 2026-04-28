# CreditWorker Workflow

## Overview

CreditWorker has two distinct workflows that must never be confused:

| Workflow | Input | PII Involved | AI Role |
|----------|-------|-------------|---------|
| Research Analysis | `research_artifacts` (Class C) | None | Analyzes educational content |
| Dispute Draft | Redacted tradeline facts (Class B) | Reinserted by human AFTER approval | Generates template scaffolds |

---

## Workflow 1 — Research Analysis (Automated)

Runs on a schedule. No human input required. No PII involved.

```
research_artifacts (topic = credit_repair)
        │
        ▼
credit_worker.js
        │
        ├── Classify text (Class A/B/C via credit_redaction_policy.js)
        ├── Flag if any PII detected in source content (advisory only)
        ├── Detect FCRA/CFPB references
        ├── Detect dispute strategies mentioned
        ├── Score urgency (high/low)
        │
        ▼
Research brief + Telegram alert
        │
        ▼
Human reviews — no action required unless PII flag raised
```

**Direct run:**
```bash
node workflows/ai_workforce/credit_worker/credit_worker.js --dry-run
node workflows/ai_workforce/credit_worker/credit_worker.js --since 30
```

---

## Workflow 2 — Dispute Draft (Human-Supervised)

Triggered manually by an advisor. PII is handled by advisor only.

```
Step 1 — ADVISOR ONLY (outside AI scope)
─────────────────────────────────────────────────────────────
Advisor receives client credit report (Class A)
Advisor reads report manually
Advisor extracts relevant tradeline facts into plain text
        Example: "Chase Visa ending 1234, shows charge-off
                  $2,400 from March 2021. Account was paid
                  off in October 2021 per client records."
─────────────────────────────────────────────────────────────

Step 2 — PII Redaction Check
─────────────────────────────────────────────────────────────
import { redactPII } from "./credit_redaction_policy.js";
const { redacted, replacements } = redactPII(advisorText);
// Verify replacements = 0 before proceeding
─────────────────────────────────────────────────────────────

Step 3 — Dispute Draft Generation
─────────────────────────────────────────────────────────────
import { generateDisputeDraft } from "./dispute_draft_workflow.js";

const draft = generateDisputeDraft({
  redacted_facts: redacted,    // Class B only
  creditor_name:  "Chase",     // Company name — not PII
  account_suffix: "1234",      // Last 4 only — not full account number
});
// draft.status = "draft"
// draft.letter_text contains [PLACEHOLDER] fields — no PII
─────────────────────────────────────────────────────────────

Step 4 — Human Review
─────────────────────────────────────────────────────────────
Advisor reads draft.letter_text
Advisor verifies:
  - Correct dispute type detected
  - FCRA reference is appropriate
  - Letter body accurately describes the dispute
  - All facts are accurate

If approved:
  draft.status = "approved_for_reinsertion"
  (Advisor updates status — either directly or via staff tool)
─────────────────────────────────────────────────────────────

Step 5 — Personal Info Reinsertion
─────────────────────────────────────────────────────────────
import { reinsertPersonalInfo } from "./dispute_template_reinsertion.js";

const final = reinsertPersonalInfo({
  draft,
  personal_info: {
    full_name:        "John Smith",       // ← Provided by advisor at call time
    current_address:  "456 Oak Street",   // ← Provided by advisor at call time
    city_state_zip:   "Atlanta, GA 30301",
    bureau_name:      "Equifax",
    bureau_address:   "P.O. Box 740256, Atlanta, GA 30374",
  },
  approved_by: "Ray Davis",
  approval_id: draft.id ?? "draft-001",
});
// final.pii_persisted = false
// PII is discarded after this function call
─────────────────────────────────────────────────────────────

Step 6 — Document Production
─────────────────────────────────────────────────────────────
Advisor uses final.letter_text to produce PDF or printed letter
PII is discarded from memory — NOT stored in Supabase by this workflow
Final document delivered to client via secure channel (advisor-managed)
─────────────────────────────────────────────────────────────
```

---

## Direct Run Commands

```bash
cd ~/nexus-ai/workflows/ai_workforce

# Research analysis — dry run
node credit_worker/credit_worker.js --dry-run

# Research analysis — last 30 days
node credit_worker/credit_worker.js --since 30

# Research analysis — all time
node credit_worker/credit_worker.js --since all

# Quiet mode
node credit_worker/credit_worker.js --quiet

# Via dispatcher
node workforce_dispatcher.js --role credit_worker --job credit_artifact_scan --dry-run
```

---

## Dispute Draft Commands (Programmatic Only)

```js
import { generateDisputeDraft, detectDisputeType } from "./dispute_draft_workflow.js";
import { reinsertPersonalInfo, checkUnfilledPlaceholders } from "./dispute_template_reinsertion.js";
import { redactPII } from "./credit_redaction_policy.js";

// Step 1: Redact facts
const { redacted, replacements } = redactPII(advisorExtractedFacts);
if (replacements > 0) throw new Error("PII still present — review redaction");

// Step 2: Generate draft
const draft = generateDisputeDraft({
  redacted_facts: redacted,
  creditor_name: "Equifax",
  account_suffix: "5678",
});

// Step 3: Advisor approves (set status)
draft.status = "approved_for_reinsertion";

// Step 4: Reinsert personal info (advisor provides at call time)
const final = reinsertPersonalInfo({
  draft,
  personal_info: { full_name: "...", current_address: "...", city_state_zip: "..." },
  approved_by: "advisor_name",
});

// Step 5: Verify no placeholders remain
const { unfilled } = checkUnfilledPlaceholders(final.letter_text);
if (unfilled.length) console.warn("Unfilled placeholders:", unfilled);

// Step 6: Produce document from final.letter_text
```

---

## Supported Dispute Types

| Type | Description |
|------|-------------|
| `not_mine` | Account doesn't belong to consumer |
| `identity_theft` | Fraudulent account opened without authorization |
| `inaccurate_balance` | Wrong balance reported |
| `inaccurate_status` | Wrong payment status (showing late when paid on time) |
| `paid_in_full` | Account is paid but shows balance |
| `duplicate_account` | Same account reported twice |
| `statute_of_limitations` | Account older than 7-year reporting limit |
| `medical_debt` | Medical debt subject to CFPB exemption rules |
| `outdated_info` | Information past reporting period |

---

## Prerequisites

- `research_artifacts` rows with `topic = 'credit_repair'` (run research pipeline)
- `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` (optional, for research alerts)
- For dispute workflow: advisor must have client credit report access (outside Mac Mini scope)
