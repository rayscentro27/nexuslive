# PII Redaction Boundary

## The Core Rule

> **No Class A (PII) data ever passes through an AI model, queue, log, or automated workflow.**

This is the absolute boundary. Everything in the CreditWorker system is designed around protecting this rule.

---

## Class Hierarchy

```
Class A — Sensitive
  SSN, DOB, account numbers, full name, addresses, phone, email
  Raw credit reports, bureau report text
  Storage: Encrypted Supabase tables + Storage buckets (RLS required)
  AI Access: NEVER
  Log Access: NEVER (use [REDACTED] markers in logs)

Class B — Restricted
  Redacted tradeline summaries, account type + last-4, dispute facts
  (All Class A elements removed by redactPII() before Class B exists)
  Storage: In-memory only during dispute draft generation
  AI Access: Dispute draft generation only (dispute_draft_workflow.js)
  Log Access: Never logged in full — only metadata (type, creditor name)

Class C — General
  Educational research, templates, FCRA references, strategy notes
  Storage: research_artifacts in Supabase
  AI Access: All workers, no restrictions
  Log Access: Full access
```

---

## Where the Boundary is Enforced

### 1. `credit_redaction_policy.js`

- `redactPII(text)` — scans and replaces all Class A patterns
- `redactObjectPII(obj)` — redacts all string fields in an object
- `detectSensitiveFields(obj)` — warns if known PII column names are present
- `classifyText(text)` — returns "A", "B", or "C"

Used before any text is passed to AI workers or dispute draft generators.

### 2. `dispute_draft_workflow.js`

- Accepts only `redacted_facts` (string assumed Class B)
- Never accesses Supabase client tables
- Never receives `personal_info` — that's a reinsertion-stage concern
- Draft output contains `[PLACEHOLDER]` fields — no real PII

### 3. `dispute_template_reinsertion.js`

- Only runs after draft status = "approved_for_reinsertion"
- `personal_info` is accepted at call time (from advisor, not DB)
- `pii_persisted: false` in return value — PII is discarded after call
- `reinsertPersonalInfo()` does not write to any database
- Caller produces the final document and manages PII disposal

### 4. `copilot_permissions.js`

- `COPILOT_BLOCKED_ACTIONS` includes `"access_client_credit_reports"`
- Portal assistant has no path to client data
- Staff copilot has no path to client credit files

### 5. `workforce_memory_map.js`

- Client-side tables (future: `credit_report_uploads`, `dispute_drafts`) will have `NONE` access for all automated workers
- Only the dispute draft workflow (human-triggered) touches these tables

---

## Storage Architecture for Credit Documents

Recommended Supabase structure (not yet created — pending future implementation):

```
Supabase Storage — bucket: credit-documents (private, RLS enforced)
  /reports/{tenant_id}/{client_id}/raw/        ← Class A, advisor-only access
  /reports/{tenant_id}/{client_id}/working/    ← Class B, advisor-only access
  /reports/{tenant_id}/{client_id}/final/      ← Final letters, advisor-only

Supabase Tables (Oracle VM scope, RLS required):
  credit_report_uploads  — metadata only (no raw report text), Class A fields encrypted
  dispute_drafts         — Class B content, linked to upload_id, status field
  dispute_approvals      — audit log: approved_by, approval_id, timestamp, draft_id
```

Mac Mini CreditWorker has **zero access** to any of these tables.

---

## Template Reinsertion Protocol

**Personal info is provided at call time — not retrieved from database.**

```
Sequence:
  1. Draft approved by advisor (status = "approved_for_reinsertion")
  2. Advisor opens advisor tool (Oracle VM scope)
  3. Advisor inputs client personal info in the tool UI
  4. Tool calls reinsertPersonalInfo({ draft, personal_info }) [Mac Mini function]
  5. Function returns final.letter_text
  6. Advisor tool generates PDF
  7. Tool discards personal_info from memory
  8. Audit log records: advisor_id, draft_id, timestamp (NO PII in log)
```

**What is logged:**
- Advisor ID
- Draft ID
- Timestamp
- Dispute type
- Creditor name (company — not PII)

**What is never logged:**
- SSN, DOB, account numbers
- Full name, address
- Any Class A fields

---

## Testing Redaction

```bash
# Quick smoke test via Node REPL
node -e "
import('./workflows/ai_workforce/credit_worker/credit_redaction_policy.js')
  .then(({ redactPII, classifyText }) => {
    const text = 'SSN: 123-45-6789, DOB: 01/15/1985, phone: 555-123-4567';
    const { redacted, replacements, pii_types_found } = redactPII(text);
    console.log('Redacted:', redacted);
    console.log('Replacements:', replacements);
    console.log('PII types:', pii_types_found);
    console.log('Classification:', classifyText(text));
  });
"
```

Expected output:
```
Redacted: SSN: [SSN REDACTED], DOB: [DOB REDACTED], phone: [PHONE REDACTED]
Replacements: 3
PII types: [ 'SSN', 'DOB', 'PHONE' ]
Classification: A
```

---

## Compliance Notes

- **FCRA § 611** — Consumers have the right to dispute inaccurate information. Dispute letters generated here cite this authority.
- **FCRA § 605B** — Identity theft blocks. Template type `identity_theft` references this.
- **CFPB Medical Debt Rules** — Medical debts under $500 removed from reports per 2025 rule. Template type `medical_debt` references this.
- **GDPR / CCPA** — Client PII stored in Supabase must comply with applicable privacy regulations. This is enforced at the Oracle VM layer (RLS + tenant isolation). Mac Mini workers never access this data.
