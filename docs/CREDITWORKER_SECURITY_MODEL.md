# CreditWorker Security Model

## Data Classification

All credit-related data is classified into three classes. Class determines what AI systems may access.

### Class A — Sensitive (AI NEVER sees this)

| Data Type | Examples | Storage Rule |
|-----------|---------|-------------|
| Social Security Number | `123-45-6789` | Supabase Storage (encrypted), RLS required |
| Date of Birth | `01/15/1985` | Supabase Storage (encrypted), RLS required |
| Account Numbers | `4111 1111 1111 1111` | Encrypted storage, last-4 only in any logs |
| Full legal name | Client's real name | Supabase clients table (Oracle side), RLS |
| Home addresses | `123 Main St, City, ST` | Supabase clients table, RLS |
| Phone numbers | `(555) 123-4567` | Supabase clients table, RLS |
| Email addresses | `client@email.com` | Supabase clients table, RLS |
| Raw credit reports | Full bureau report text | Supabase Storage, isolated bucket, no AI access |

**Rule:** Class A data is stored in encrypted Supabase tables or Storage buckets. No AI worker, queue, or log ever receives Class A data.

### Class B — Restricted (AI may process with constraints)

| Data Type | Examples | AI Access Rule |
|-----------|---------|----------------|
| Redacted tradeline summaries | "AMEX charge-off, $2,400, 2021" | CreditWorker dispute_draft only |
| Account type + last 4 digits | "Chase Visa ...1234" | Dispute draft only |
| Derogatory item categories | "3 late payments, 2 collections" | Dispute draft only |
| Dispute-ready extracted facts | "Balance $0 but showing $1,200" | Dispute draft only |

**Rule:** Class B data is processed only by `dispute_draft_workflow.js` after explicit advisor action. Never stored in queues or logs. Discarded after draft generation.

### Class C — General (Freely usable)

| Data Type | Examples | AI Access |
|-----------|---------|-----------|
| Educational research | "FCRA § 611 gives 30 days to investigate" | All workers |
| Template scaffolds | Generic dispute letter templates | All workers |
| Strategy summaries | "Medical debt under $500 can't be reported" | All workers |
| CFPB policy updates | "New rule effective March 2025..." | All workers |

**Rule:** Class C data is what CreditWorker primarily operates on. This is ingested via the research pipeline (YouTube transcripts, manual sources) — no client PII involved.

---

## What CreditWorker.js Analyzes

The `credit_worker.js` module **only processes Class C data** — research artifacts from the `credit_repair` topic in Supabase. It analyzes:

- Educational credit repair content from YouTube channels
- FCRA / CFPB strategy summaries
- Dispute strategy patterns
- Policy update detection

It does **not** touch any client files, credit reports, or personal information.

---

## Dispute Workflow Separation

The dispute letter workflow is a separate, human-gated process:

```
Step 1: Advisor receives client credit report (Class A)
        ↓ Outside AI scope — advisor only

Step 2: Advisor extracts dispute facts manually
        ↓ Creates Class B summary (redacted)

Step 3: dispute_draft_workflow.js
        Input: Class B redacted facts (no PII)
        Output: Draft letter with [PLACEHOLDER] fields

Step 4: Human advisor reviews draft
        ↓ Updates status to "approved_for_reinsertion"

Step 5: dispute_template_reinsertion.js
        Input: Approved draft + Class A personal info (advisor provides at call time)
        Output: Final letter text (PII NOT persisted in result object)

Step 6: Advisor produces final document (PDF/print)
        ↓ PII discarded from memory after document production
```

---

## PII Redaction Engine

`credit_redaction_policy.js` provides automatic PII detection and redaction:

| Pattern | Replacement |
|---------|------------|
| SSN (e.g., 123-45-6789) | [SSN REDACTED] |
| DOB patterns | [DOB REDACTED] |
| Account numbers (13-19 digits) | [ACCOUNT# REDACTED] |
| Street addresses | [ADDRESS REDACTED] |
| Phone numbers | [PHONE REDACTED] |
| Email addresses | [EMAIL REDACTED] |
| Known sensitive field names | [FIELD REDACTED — SENSITIVE] |

The redaction engine also classifies text as Class A, B, or C automatically.

---

## Blocked Actions (Hard-Coded)

These actions are permanently blocked regardless of any configuration:

| Action | Blocked By |
|--------|-----------|
| Send raw credit report to AI model | No code path exists |
| Read client account records | Not in approved table list |
| Process client SSN/DOB | PII redaction blocks; no DB access path |
| Auto-generate final dispute letters | Template reinsertion requires human approval gate |
| Store PII in Supabase via CreditWorker | No write path to client tables |
| Auto-mail dispute letters | No email integration in worker |

---

## Supabase Table Boundaries

| Table | CreditWorker Access | Notes |
|-------|---------------------|-------|
| `research_artifacts` (credit_repair) | READ | Class C only — educational research |
| `research_claims` | READ | For FCRA claim extraction |
| `research_briefs` | DRAFT | Can write credit research briefs |
| `dispute_drafts` (future) | DRAFT | Class B content only, human-reviewed |
| Client tables (`clients`, `credit_reports`, etc.) | NONE | Not in Mac Mini scope |

---

## Audit Trail Requirements

For any dispute workflow activity:
- Log advisor ID who approved reinsertion
- Log timestamp of approval
- Log draft ID
- Log dispute type
- Do NOT log any Class A personal information

`dispute_template_reinsertion.js` returns `approved_by` and `approval_id` fields for caller to log.
