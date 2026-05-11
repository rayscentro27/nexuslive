// ── Dispute Draft Workflow ─────────────────────────────────────────────────────
// Generates PII-safe dispute letter drafts from REDACTED credit facts only.
//
// Workflow stages:
//   1. Receive redacted tradeline facts (Class B — no PII)
//   2. Match dispute type to template
//   3. Generate draft letter with [PLACEHOLDER] fields
//   4. Return draft for human review
//   5. Human fills in placeholders and approves
//   6. Template reinsertion adds approved personal info (see dispute_template_reinsertion.js)
//
// CRITICAL: This module never receives or processes Class A (PII) data.
// All raw client data must be redacted via credit_redaction_policy.js FIRST.
// ─────────────────────────────────────────────────────────────────────────────

// ── Dispute types ─────────────────────────────────────────────────────────────

export const DISPUTE_TYPE = Object.freeze({
  NOT_MINE:           "not_mine",
  INACCURATE_BALANCE: "inaccurate_balance",
  INACCURATE_STATUS:  "inaccurate_status",
  DUPLICATE_ACCOUNT:  "duplicate_account",
  PAID_IN_FULL:       "paid_in_full",
  STATUTE_OF_LIMITATIONS: "statute_of_limitations",
  MEDICAL_DEBT:       "medical_debt",
  IDENTITY_THEFT:     "identity_theft",
  OUTDATED_INFO:      "outdated_info",
});

// ── Dispute type detection from redacted facts ────────────────────────────────

const DISPUTE_DETECTION_PATTERNS = [
  { type: DISPUTE_TYPE.NOT_MINE,            patterns: [/not\s+mine/i, /unknown\s+account/i, /never\s+opened/i, /authorized\s+user\s+removed/i] },
  { type: DISPUTE_TYPE.IDENTITY_THEFT,      patterns: [/identity\s+theft/i, /fraud/i, /stolen/i, /fraudulent\s+account/i] },
  { type: DISPUTE_TYPE.INACCURATE_BALANCE,  patterns: [/incorrect\s+balance/i, /wrong\s+balance/i, /balance\s+is\s+higher/i] },
  { type: DISPUTE_TYPE.INACCURATE_STATUS,   patterns: [/wrong\s+status/i, /incorrect\s+status/i, /showing\s+late/i, /should\s+show\s+paid/i] },
  { type: DISPUTE_TYPE.PAID_IN_FULL,        patterns: [/paid\s+in\s+full/i, /paid\s+off/i, /settled\s+in\s+full/i] },
  { type: DISPUTE_TYPE.DUPLICATE_ACCOUNT,   patterns: [/duplicate/i, /same\s+account\s+twice/i, /reported\s+twice/i] },
  { type: DISPUTE_TYPE.STATUTE_OF_LIMITATIONS, patterns: [/statute\s+of\s+limitations/i, /too\s+old/i, /7[\s-]?year/i, /past\s+reporting\s+period/i] },
  { type: DISPUTE_TYPE.MEDICAL_DEBT,        patterns: [/medical\s+(?:debt|bill|collection)/i, /hospital/i, /healthcare/i] },
  { type: DISPUTE_TYPE.OUTDATED_INFO,       patterns: [/outdated/i, /should\s+have\s+fallen\s+off/i, /expired/i] },
];

export function detectDisputeType(redactedFacts) {
  const text = redactedFacts.toLowerCase();
  for (const { type, patterns } of DISPUTE_DETECTION_PATTERNS) {
    if (patterns.some((p) => p.test(text))) return type;
  }
  return DISPUTE_TYPE.INACCURATE_STATUS; // default fallback
}

// ── Legal references per dispute type ────────────────────────────────────────

const FCRA_REFERENCES = Object.freeze({
  [DISPUTE_TYPE.NOT_MINE]:              "FCRA § 611 (15 U.S.C. § 1681i) — Right to Dispute Inaccurate Information",
  [DISPUTE_TYPE.IDENTITY_THEFT]:        "FCRA § 605B (15 U.S.C. § 1681c-2) — Block of Information Resulting from Identity Theft",
  [DISPUTE_TYPE.INACCURATE_BALANCE]:    "FCRA § 611 (15 U.S.C. § 1681i) — Procedure for Investigating Disputed Information",
  [DISPUTE_TYPE.INACCURATE_STATUS]:     "FCRA § 623 (15 U.S.C. § 1681s-2) — Responsibilities of Furnishers of Information",
  [DISPUTE_TYPE.PAID_IN_FULL]:          "FCRA § 623(a)(2) — Duty to Correct and Update Information",
  [DISPUTE_TYPE.DUPLICATE_ACCOUNT]:     "FCRA § 611 (15 U.S.C. § 1681i) — Dispute of Duplicate Tradelines",
  [DISPUTE_TYPE.STATUTE_OF_LIMITATIONS]:"FCRA § 605(a) (15 U.S.C. § 1681c) — Requirements Relating to Information Contained in Consumer Reports",
  [DISPUTE_TYPE.MEDICAL_DEBT]:          "FCRA § 605(a)(6) — Medical Information Reporting Rules",
  [DISPUTE_TYPE.OUTDATED_INFO]:         "FCRA § 605(a)(4) — Obsolete Information",
});

// ── Dispute letter template engine ────────────────────────────────────────────
// All personal details are [PLACEHOLDER] — filled in at the reinsertion stage.

function generateDisputeLetter({ disputeType, redactedFacts, creditorName, accountSuffix }) {
  const fcra = FCRA_REFERENCES[disputeType] ?? FCRA_REFERENCES[DISPUTE_TYPE.INACCURATE_STATUS];
  const disputeDescription = getDisputeDescription(disputeType, redactedFacts);

  return `[CONSUMER FULL NAME]
[CONSUMER CURRENT ADDRESS]
[CITY, STATE, ZIP]

[DATE]

[CREDIT BUREAU NAME]
[CREDIT BUREAU ADDRESS]

Re: Formal Dispute — Account: ${creditorName ?? "[CREDITOR NAME]"} (Last 4: ${accountSuffix ?? "XXXX"})

To Whom It May Concern,

I am writing to formally dispute the following information appearing on my credit report pursuant to the Fair Credit Reporting Act (FCRA).

Account Information (as reported):
  Creditor: ${creditorName ?? "[CREDITOR NAME]"}
  Account: ending in ${accountSuffix ?? "XXXX"}
  Issue: ${disputeDescription}

${getDisputeBody(disputeType, redactedFacts)}

Legal Basis:
${fcra}

I request that this item be investigated and corrected or removed within the 30-day investigation window required by the FCRA. Please send written confirmation of the results of your investigation to my address above.

Enclosed (for reinsertion after approval):
  ☐ [CONSUMER IDENTITY DOCUMENT]
  ☐ [PROOF OF ADDRESS]
  ☐ [SUPPORTING EVIDENCE — IF APPLICABLE]

Sincerely,

[CONSUMER FULL NAME]
[CONSUMER SIGNATURE]

---
[DRAFT — NOT FOR DISTRIBUTION — REQUIRES HUMAN REVIEW AND PERSONAL INFO REINSERTION]
[Generated by Nexus AI CreditWorker — ${new Date().toISOString()}]
`;
}

function getDisputeDescription(type, facts) {
  const descriptions = {
    [DISPUTE_TYPE.NOT_MINE]:              "This account does not belong to me and should not appear on my credit report.",
    [DISPUTE_TYPE.IDENTITY_THEFT]:        "This account was opened fraudulently without my authorization.",
    [DISPUTE_TYPE.INACCURATE_BALANCE]:    "The reported balance is inaccurate.",
    [DISPUTE_TYPE.INACCURATE_STATUS]:     "The reported payment status is inaccurate.",
    [DISPUTE_TYPE.PAID_IN_FULL]:          "This account has been paid in full and should reflect a $0 balance.",
    [DISPUTE_TYPE.DUPLICATE_ACCOUNT]:     "This account is reported as a duplicate entry.",
    [DISPUTE_TYPE.STATUTE_OF_LIMITATIONS]:"This account has exceeded the 7-year reporting period.",
    [DISPUTE_TYPE.MEDICAL_DEBT]:          "This medical debt is subject to updated FCRA medical debt reporting rules.",
    [DISPUTE_TYPE.OUTDATED_INFO]:         "The information is outdated and should have been removed from my report.",
  };
  return descriptions[type] ?? "The reported information is inaccurate.";
}

function getDisputeBody(type, facts) {
  const factSummary = facts ? `\nFacts supporting this dispute:\n${facts.slice(0, 300)}\n` : "";

  if (type === DISPUTE_TYPE.IDENTITY_THEFT) {
    return `${factSummary}
I have filed a report with the Federal Trade Commission and/or local law enforcement regarding this identity theft. I request that this item be blocked from my credit report per FCRA § 605B.`;
  }

  if (type === DISPUTE_TYPE.STATUTE_OF_LIMITATIONS) {
    return `${factSummary}
The delinquency on this account originated more than 7 years ago. Under FCRA § 605(a), this information must be removed from consumer credit reports.`;
  }

  if (type === DISPUTE_TYPE.MEDICAL_DEBT) {
    return `${factSummary}
Per updated CFPB rules and FCRA § 605(a)(6), medical debts under $500 must not appear on consumer credit reports. If this debt is over $500, it must be verified as accurate per § 611.`;
  }

  return `${factSummary}
I request that the credit bureau investigate this item and correct the information to accurately reflect my credit history.`;
}

// ── Public draft generator ────────────────────────────────────────────────────

/**
 * Generate a PII-safe dispute letter draft from redacted facts.
 *
 * @param {Object} opts
 * @param {string} opts.redacted_facts  - Class B redacted tradeline summary
 * @param {string} [opts.creditor_name] - Creditor name (not PII — company name)
 * @param {string} [opts.account_suffix]- Last 4 digits only (not full account number)
 * @param {string} [opts.dispute_type]  - Override auto-detection (DISPUTE_TYPE constant)
 * @returns {Object} Draft dispute letter payload
 */
export function generateDisputeDraft({
  redacted_facts,
  creditor_name,
  account_suffix,
  dispute_type,
} = {}) {
  if (!redacted_facts) throw new Error("[dispute-draft] redacted_facts is required.");

  // Detect dispute type from facts if not overridden
  const detectedType = dispute_type ?? detectDisputeType(redacted_facts);

  const letterText = generateDisputeLetter({
    disputeType:   detectedType,
    redactedFacts: redacted_facts,
    creditorName:  creditor_name,
    accountSuffix: account_suffix,
  });

  return {
    status:            "draft",
    dispute_type:      detectedType,
    creditor_name:     creditor_name ?? null,
    account_suffix:    account_suffix ?? null,
    letter_text:       letterText,
    fcra_reference:    FCRA_REFERENCES[detectedType],
    pii_present:       false,    // guaranteed — facts were pre-redacted
    requires_reinsertion: true,  // personal info must be added by human
    requires_human_review: true,
    generated_at:      new Date().toISOString(),
  };
}
