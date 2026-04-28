// ── Credit Redaction Policy ────────────────────────────────────────────────────
// Defines PII classification rules and redaction patterns for credit documents.
//
// Classification:
//   Class A (Sensitive) — SSN, DOB, account numbers, full name, addresses
//   Class B (Restricted) — Redacted tradeline summaries, extracted dispute facts
//   Class C (General) — Educational content, research notes, templates
//
// Class A data NEVER reaches any AI model, queue, or logging system.
// Class B data may be used for dispute draft generation (no raw PII).
// Class C data is freely usable by workers and copilots.
// ─────────────────────────────────────────────────────────────────────────────

// ── PII Patterns (Class A — must be redacted) ─────────────────────────────────

export const PII_PATTERNS = Object.freeze([
  // Social Security Number
  {
    name:        "SSN",
    class:       "A",
    pattern:     /\b(?:\d{3}[-\s]?\d{2}[-\s]?\d{4})\b/g,
    replacement: "[SSN REDACTED]",
  },
  // Date of Birth (multiple formats)
  {
    name:        "DOB",
    class:       "A",
    pattern:     /\b(?:dob|date\s+of\s+birth)[:\s]+\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}\b/gi,
    replacement: "[DOB REDACTED]",
  },
  // Standalone date that looks like a DOB in context (e.g. 01/15/1985)
  {
    name:        "DOB_DATE",
    class:       "A",
    pattern:     /\b\d{1,2}[\/\-]\d{1,2}[\/\-](?:19|20)\d{2}\b/g,
    replacement: "[DATE REDACTED]",
  },
  // Credit card / account numbers (13-19 digit sequences)
  {
    name:        "ACCOUNT_NUMBER",
    class:       "A",
    pattern:     /\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{1,4}[\s\-]?\d{0,3}\b/g,
    replacement: "[ACCOUNT# REDACTED]",
  },
  // Short account numbers (e.g., "Acct #12345678")
  {
    name:        "SHORT_ACCOUNT",
    class:       "A",
    pattern:     /(?:acct?\.?\s*#?|account\s*(?:number|#)?)[:\s]*\d{4,12}\b/gi,
    replacement: "[ACCOUNT# REDACTED]",
  },
  // Street addresses
  {
    name:        "ADDRESS",
    class:       "A",
    pattern:     /\b\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+){0,3}\s+(?:st|ave|blvd|dr|rd|ln|ct|way|pl|terr?|cir)\b\.?/gi,
    replacement: "[ADDRESS REDACTED]",
  },
  // Phone numbers
  {
    name:        "PHONE",
    class:       "A",
    pattern:     /\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b/g,
    replacement: "[PHONE REDACTED]",
  },
  // Email addresses
  {
    name:        "EMAIL",
    class:       "A",
    pattern:     /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g,
    replacement: "[EMAIL REDACTED]",
  },
]);

// ── Sensitive field names (Class A) ───────────────────────────────────────────
// Supabase column names that should never be read by AI workers

export const SENSITIVE_FIELD_NAMES = Object.freeze([
  "ssn", "social_security", "social_security_number",
  "dob", "date_of_birth", "birthdate",
  "account_number", "card_number", "account_no",
  "full_name", "legal_name",
  "street_address", "address_line_1", "address_line_2",
  "phone", "phone_number", "mobile",
  "email", "email_address",
  "drivers_license", "passport_number",
  "bank_routing", "routing_number",
  "raw_credit_report", "credit_report_text", "bureau_report",
]);

// ── Redaction engine ──────────────────────────────────────────────────────────

/**
 * Redact Class A PII from a text string.
 * Returns the redacted text and a count of replacements made.
 *
 * @param {string} text - Input text (may contain PII)
 * @returns {{ redacted: string, replacements: number, pii_types_found: string[] }}
 */
export function redactPII(text) {
  if (!text || typeof text !== "string") return { redacted: "", replacements: 0, pii_types_found: [] };

  let result = text;
  let total = 0;
  const found = [];

  for (const rule of PII_PATTERNS) {
    const before = result;
    result = result.replace(rule.pattern, rule.replacement);
    const count = (before.match(rule.pattern) ?? []).length;
    if (count > 0) {
      total += count;
      found.push(rule.name);
    }
  }

  return {
    redacted: result,
    replacements: total,
    pii_types_found: found,
  };
}

/**
 * Redact PII from all string fields in an object.
 * Skips non-string fields. Returns a new object (does not mutate).
 *
 * @param {Object} obj - Input object (e.g., a Supabase row)
 * @param {string[]} [skipFields=[]] - Fields to skip (e.g., IDs, metadata)
 * @returns {{ redacted: Object, replacements: number }}
 */
export function redactObjectPII(obj, skipFields = []) {
  const redacted = {};
  let totalReplacements = 0;

  for (const [key, value] of Object.entries(obj)) {
    // Always block known sensitive field names
    if (SENSITIVE_FIELD_NAMES.includes(key.toLowerCase())) {
      redacted[key] = "[FIELD REDACTED — SENSITIVE]";
      totalReplacements++;
      continue;
    }

    if (skipFields.includes(key)) {
      redacted[key] = value;
      continue;
    }

    if (typeof value === "string") {
      const { redacted: r, replacements } = redactPII(value);
      redacted[key] = r;
      totalReplacements += replacements;
    } else {
      redacted[key] = value;
    }
  }

  return { redacted, replacements: totalReplacements };
}

/**
 * Check if an object contains any known sensitive field names.
 * Used as a pre-flight check before processing.
 *
 * @param {Object} obj
 * @returns {{ hasSensitiveFields: boolean, fields: string[] }}
 */
export function detectSensitiveFields(obj) {
  const fields = Object.keys(obj).filter((k) => SENSITIVE_FIELD_NAMES.includes(k.toLowerCase()));
  return { hasSensitiveFields: fields.length > 0, fields };
}

/**
 * Classify a piece of text as A / B / C based on PII presence.
 *
 * @param {string} text
 * @returns {"A"|"B"|"C"}
 */
export function classifyText(text) {
  if (!text) return "C";
  const { replacements } = redactPII(text);
  if (replacements > 0) return "A";
  // Class B signals: mentions real tradeline data but no PII
  if (/(?:tradeline|charge.off|collection|late\s+payment|derogatory)/i.test(text)) return "B";
  return "C";
}
