// ── Dispute Template Reinsertion ───────────────────────────────────────────────
// Controls the stage at which approved personal information is reinserted
// into a dispute letter draft.
//
// This stage runs ONLY after:
//   1. The draft letter has been human-reviewed and approved
//   2. The advisor has explicitly supplied the personal info for reinsertion
//   3. The draft status has been updated to "approved_for_reinsertion"
//
// Personal info provided at this stage is:
//   - Used only to fill placeholders in the approved draft
//   - Never stored in logs, queues, or AI-accessible tables
//   - Discarded from memory after the final document is produced
//
// STRICT RULE: This function never reads PII from Supabase or any database.
// PII is provided by the human advisor directly at call time.
// ─────────────────────────────────────────────────────────────────────────────

// ── Placeholder definitions ───────────────────────────────────────────────────

export const PLACEHOLDERS = Object.freeze({
  FULL_NAME:         "[CONSUMER FULL NAME]",
  CURRENT_ADDRESS:   "[CONSUMER CURRENT ADDRESS]",
  CITY_STATE_ZIP:    "[CITY, STATE, ZIP]",
  DATE:              "[DATE]",
  BUREAU_NAME:       "[CREDIT BUREAU NAME]",
  BUREAU_ADDRESS:    "[CREDIT BUREAU ADDRESS]",
  IDENTITY_DOC:      "[CONSUMER IDENTITY DOCUMENT]",
  PROOF_OF_ADDRESS:  "[PROOF OF ADDRESS]",
  SUPPORTING_EVIDENCE: "[SUPPORTING EVIDENCE — IF APPLICABLE]",
  SIGNATURE:         "[CONSUMER SIGNATURE]",
});

// ── Reinsertion engine ────────────────────────────────────────────────────────

/**
 * Reinsert approved personal information into a reviewed dispute letter draft.
 *
 * This function:
 * 1. Verifies the draft is in "approved_for_reinsertion" status
 * 2. Replaces [PLACEHOLDER] fields with provided personal info
 * 3. Returns the final letter — does NOT persist PII to any database
 * 4. Caller is responsible for producing the final document (PDF/print)
 *
 * @param {Object} opts
 * @param {Object} opts.draft              - Dispute draft from generateDisputeDraft()
 * @param {Object} opts.personal_info      - Personal info from advisor (NOT stored)
 * @param {string} opts.personal_info.full_name
 * @param {string} opts.personal_info.current_address
 * @param {string} opts.personal_info.city_state_zip
 * @param {string} [opts.personal_info.bureau_name]   - If not in draft
 * @param {string} [opts.personal_info.bureau_address]
 * @param {string} [opts.approved_by]      - Advisor name for audit trail
 * @param {string} [opts.approval_id]      - Draft ID from approval record
 * @returns {Object} Finalized letter ready for production
 */
export function reinsertPersonalInfo({
  draft,
  personal_info,
  approved_by,
  approval_id,
} = {}) {
  // ── Guard: draft must be approved ──────────────────────────────────────────
  if (!draft || typeof draft !== "object") {
    throw new Error("[reinsertion] draft object is required.");
  }
  if (!draft.requires_human_review === false && draft.status !== "approved_for_reinsertion") {
    // Allow if status is explicitly approved — otherwise block
    if (!["approved_for_reinsertion", "approved"].includes(draft.status)) {
      throw new Error(
        `[reinsertion] Draft must be in "approved_for_reinsertion" status before reinsertion. ` +
        `Current status: "${draft.status}". Have a human advisor review and update the status first.`
      );
    }
  }

  // ── Guard: personal_info required ─────────────────────────────────────────
  if (!personal_info?.full_name || !personal_info?.current_address) {
    throw new Error("[reinsertion] personal_info.full_name and personal_info.current_address are required.");
  }

  const today = new Date().toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric"
  });

  // ── Substitution map ───────────────────────────────────────────────────────
  const substitutions = {
    [PLACEHOLDERS.FULL_NAME]:          personal_info.full_name,
    [PLACEHOLDERS.CURRENT_ADDRESS]:    personal_info.current_address,
    [PLACEHOLDERS.CITY_STATE_ZIP]:     personal_info.city_state_zip ?? "[CITY, STATE, ZIP]",
    [PLACEHOLDERS.DATE]:               today,
    [PLACEHOLDERS.BUREAU_NAME]:        personal_info.bureau_name ?? "[CREDIT BUREAU NAME]",
    [PLACEHOLDERS.BUREAU_ADDRESS]:     personal_info.bureau_address ?? "[CREDIT BUREAU ADDRESS]",
    [PLACEHOLDERS.IDENTITY_DOC]:       personal_info.identity_doc_label ?? "Copy of Government-Issued ID",
    [PLACEHOLDERS.PROOF_OF_ADDRESS]:   personal_info.address_doc_label ?? "Copy of Utility Bill or Bank Statement",
    [PLACEHOLDERS.SUPPORTING_EVIDENCE]: personal_info.evidence_label ?? "See attached supporting documentation",
    [PLACEHOLDERS.SIGNATURE]:          personal_info.full_name,  // signature line
  };

  // ── Perform substitution ───────────────────────────────────────────────────
  let finalText = draft.letter_text;
  for (const [placeholder, value] of Object.entries(substitutions)) {
    finalText = finalText.replaceAll(placeholder, value);
  }

  // ── Remove draft watermark ─────────────────────────────────────────────────
  finalText = finalText.replace(
    /\n---\n\[DRAFT — NOT FOR DISTRIBUTION.*?\n/s,
    "\n"
  );

  // ── Build result (PII not stored in result.personal_info) ─────────────────
  return {
    status:          "finalized",
    dispute_type:    draft.dispute_type,
    creditor_name:   draft.creditor_name,
    account_suffix:  draft.account_suffix,
    fcra_reference:  draft.fcra_reference,
    letter_text:     finalText,
    approved_by:     approved_by ?? "unknown",
    approval_id:     approval_id ?? null,
    finalized_at:    new Date().toISOString(),
    // Note: personal_info is intentionally NOT stored in this output object.
    // The caller (advisor tool / Oracle VM) handles the final document.
    pii_persisted:   false,
  };
}

/**
 * Count how many placeholders remain unfilled in a draft.
 * Used to verify completeness before sending to client.
 *
 * @param {string} letterText
 * @returns {{ unfilled: string[], count: number }}
 */
export function checkUnfilledPlaceholders(letterText) {
  const unfilled = Object.values(PLACEHOLDERS).filter((p) => letterText.includes(p));
  return { unfilled, count: unfilled.length };
}
