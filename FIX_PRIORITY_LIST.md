# Nexus Platform — Fix Priority List
**Date:** 2026-05-03  
**Source:** FUNCTIONALITY_AUDIT.md + USER_SIMULATION_REPORT.md  

Priority Definitions:
- **P0 — Crash / Total Blocker:** Breaks a page or flow for every user. Must fix before any public demo.
- **P1 — Core Feature Broken:** Named feature exists in UI but does nothing when clicked. Breaks expected user journey.
- **P2 — Polish / Missing UX:** Buttons stub out, data is hardcoded, minor consistency gaps. Fix before launch.

---

## P0 — Crash Bugs and Total Blockers (Fix Immediately)

### P0-1: GrantsFinder.tsx — `opportunities` ReferenceError Crashes Grants Page
**File:** `src/components/GrantsFinder.tsx`  
**Issue:** JSX references an `opportunities` variable that is never declared or imported. Every user who navigates to the Grants tab gets a `ReferenceError`. The entire component unmounts. If no error boundary is in place, it may crash the parent layout.  
**Fix:** Audit every use of `opportunities` in the JSX. Either replace with `grants` (the defined filtered array variable) or declare and populate `opportunities` from the DB. This is a one-line rename in most cases.  
**Impact:** 100% of users cannot access the Grants page.

### P0-2: Credit Report Upload — No Handler on Drop Zone
**File:** `src/components/CreditAnalysis.tsx`  
**Issue:** The "Upload New Report" zone has no `onChange` or `onDrop` handler. Users cannot upload a credit report from the primary credit entry point. Without a credit report, Approval Simulator, Funding Readiness, and Dashboard funding range all show empty or hardcoded data.  
**Fix:** Attach a file input handler that uploads to Supabase Storage and either (a) parses basic fields (score, date) into `credit_reports`, or (b) navigates user to Documents tab to complete. At minimum, wire the existing Documents upload flow to also insert a `credit_reports` row for PDFs tagged as credit reports.  
**Impact:** Entire credit and funding intelligence layer is non-functional for fresh users.

### P0-3: Funding — "New Application" Button Has No onClick
**File:** `src/components/Funding.tsx`  
**Issue:** "New Application" is the primary call-to-action in the Funding tab. It has no `onClick` handler. Users cannot create any funding application record.  
**Fix:** Add a modal or inline form that inserts a row into `funding_applications` (lender name, product type, requested amount, status). Minimum viable: simple modal with three fields + save button.  
**Impact:** The entire funding pipeline is empty for all users. Admin Funding view shows zero applications.

---

## P1 — Core Features Broken (Fix Before Soft Launch)

### P1-1: LLC Setup Steps — Not Persisted
**File:** `src/components/BusinessFoundation.tsx`  
**Issue:** `completedSteps` is local React state. Refreshing the page resets all LLC progress. Users lose track of which formation steps they have completed.  
**Fix:** Store `completedSteps` in `business_entities` as a JSONB column (or a new `llc_setup_progress` table), upserted when a step is toggled.  
**Implementation order:** Add column to migration → read on mount → upsert on toggle.

### P1-2: Funding Roadmap Action Checkboxes — Display Only
**File:** `src/components/FundingRoadmap.tsx`  
**Issue:** Action step checkboxes render but have no `onClick`. Users cannot mark roadmap actions as complete.  
**Fix:** Add `onClick` to each checkbox that updates the corresponding `funding_actions` row status in DB (toggle `completed`/`pending`). If using static fallback stages, write progress to `funding_roadmap_stages` on the user.

### P1-3: Credit Boost "See Options" — Only Works for rent_reporting
**File:** `src/components/CreditBoostEngine.tsx`  
**Issue:** The `handleSeeOptions` function only opens `RentKharmaModal` for the `rent_reporting` category. All other categories (authorized_user, credit_builder, utilization, tradeline) silently do nothing.  
**Fix:** For each category, either (a) open a generic `ProviderOptionsModal` that reads `providers` from the opportunity's JSONB field, or (b) navigate to an appropriate external resource. At minimum, show a toast or modal explaining the category.

### P1-4: Messages — Search Bar Not Connected
**File:** `src/components/Messages.tsx`  
**Issue:** The conversation search input has no onChange handler connected to the conversation list filter.  
**Fix:** Add a `searchQuery` state, filter conversations array by query, wire the input to `setSearchQuery`.

### P1-5: Action Center — "Refresh" and "Chat with Advisor" Broken
**File:** `src/components/ActionCenter.tsx`  
**Issue:** "Refresh" has no `onClick`. "Chat with Advisor" has no `onClick` or navigation.  
**Fix:** "Refresh" → call `load()` to re-fetch tasks. "Chat with Advisor" → call `onNavigate('messages')`.

### P1-6: Action Center — Static Business Checklist and Alerts
**File:** `src/components/ActionCenter.tsx`  
**Issue:** Business Setup checklist is hardcoded, Recent Alerts are hardcoded, "Grants Eligible: 3" is hardcoded. These ignore all real user data.  
**Fix:**
- Business checklist → derive from `business_entities` fields (same logic as Account's profile completion widget).
- Recent Alerts → read last 3 from `notifications` table filtered by `user_id`.
- Grants count → query `grants_catalog` count (or use static 0 if uncountable) until a proper eligibility model exists.

### P1-7: Approval Simulator — No Save and No "Apply" Action
**File:** `src/components/ApprovalSimulator.tsx`  
**Issue:** Simulation results are computed but never written to `approval_simulations` table. No "Apply Now" action button exists in results.  
**Fix:** After "Run Simulation," insert each lender result to `approval_simulations`. Add an "Apply" button per result row that either opens the lender's external URL or navigates to Funding to pre-populate a new application form (requires P0-3 fix first).

### P1-8: Bank Behavior Factor Not Connected to Funding Readiness Score
**File:** `src/components/FundingReadiness.tsx`  
**Issue:** The bank behavior factor calculation always returns null in `Recalculate`. Bank snapshots exist in the DB but are never read during score recalculation.  
**Fix:** In `FundingReadiness.tsx`, fetch the most recent `bank_behavior_snapshots` row for the user. Extract `bank_readiness_score` and include it in the `overall_score` formula.

### P1-9: Funding Strategy Checklist — Not Persisted
**File:** `src/components/Funding.tsx`  
**Issue:** Strategy tab checklist is local state only. Refresh resets all checked items.  
**Fix:** Store checklist state in `funding_strategies` table (upsert per `strategy_name` + `user_id`). Read on mount. Write on each toggle.

### P1-10: Admin AI Workforce — System Prompt Save Not Wired
**File:** `src/components/admin/AdminAIWorkforce.tsx`  
**Issue:** System prompt textarea is editable but the Save button has no `onClick`. Prompt changes are lost on navigation.  
**Fix:** Add `onClick` to Save button that calls `supabase.from('bot_profiles').update({ system_prompt: promptValue }).eq('agent_key', selectedId)`.

### P1-11: Admin AI Workforce — Pause / Restart / Deploy New AI Buttons Broken
**File:** `src/components/admin/AdminAIWorkforce.tsx`  
**Issue:** Pause, Restart, and "Deploy New AI" buttons have no `onClick` handlers.  
**Fix (minimal):** Pause/Restart → update `bot_profiles.status` to `idle`/`active` respectively. "Deploy New AI" → open a modal to create a new `bot_profiles` row.

### P1-12: Admin Clients — "Manage" Button Broken
**File:** `src/components/admin/AdminClients.tsx`  
**Issue:** "Manage" button per client row has no `onClick`. Admin cannot view or edit any individual client's data.  
**Fix:** Open a side-panel or modal with the client's `user_profiles`, `business_entities`, `credit_reports`, and `tasks`. Allow admin to update `user_profiles.role` or `subscription_plan`. This is the most important admin workflow gap.

### P1-13: Admin Funding — No Per-Row Actions
**File:** `src/components/admin/AdminFunding.tsx`  
**Issue:** Admin can see all applications but cannot change status, add notes, or contact the applicant.  
**Fix:** Add a "Review" button per row that opens a modal allowing admin to update `funding_applications.status` and add admin notes.

### P1-14: Hidden Tabs Not in Bottom Dock
**File:** `src/App.tsx`  
**Issue:** `funding-readiness`, `bank-behavior`, and `business-setup` exist as valid routes but are not in the bottom dock. Users can only reach them via indirect `onNavigate` calls from specific Dashboard elements.  
**Fix:** Either (a) add these to the dock (requires dock redesign), (b) add them as sub-tabs within their parent sections (e.g., Funding Readiness inside Funding tab), or (c) ensure every entry point in Dashboard is visually prominent enough that users discover the path.

---

## P2 — Polish and UX Gaps (Fix Before Full Launch)

### P2-1: Dashboard — Hardcoded Fallback Data Displayed as Real
**File:** `src/components/Dashboard.tsx`  
**Issue:** Hardcoded activity log and $13k–$75k funding range shown immediately on new accounts. Misleading.  
**Fix:** Show empty state components ("No activity yet" / "Upload a credit report to see your funding range") instead of hardcoded values when DB returns empty.

### P2-2: CreditAnalysis — "Generate Dispute Letters," "View Disputes," "View Utilization" No Handlers
**File:** `src/components/CreditAnalysis.tsx`  
**Issue:** Three action buttons have no `onClick`.  
**Fix:** "Generate Dispute Letters" → navigate to a dispute letter generation flow or show a modal. "View Disputes" → navigate to a disputes list tab or modal. "View Utilization" → scroll to/expand the utilization section or open a modal.

### P2-3: Funding — Pipeline Bars and Lender Matches Are Static
**File:** `src/components/Funding.tsx`  
**Issue:** Pipeline bars show hardcoded percentages. Lender Matches list is hardcoded.  
**Fix:** Pipeline bars → derive from real `funding_applications` status counts. Lender Matches → read from `funding_recommendations` table (already in schema), or use the `lender_rules` table filtered to user's score band.

### P2-4: Funding Roadmap — "View Funding Options" Button Broken
**File:** `src/components/FundingRoadmap.tsx`  
**Issue:** "View Funding Options" has no `onClick`.  
**Fix:** Navigate to `funding` tab via `onNavigate('funding')`.

### P2-5: Messages — Static 65% Readiness in Sidebar
**File:** `src/components/Messages.tsx`  
**Issue:** 65% readiness is hardcoded.  
**Fix:** Pass the user's latest `funding_readiness_snapshots.overall_score` as a prop or read it directly in the component.

### P2-6: Messages — Phone, Video, MoreVertical Buttons Broken
**File:** `src/components/Messages.tsx`  
**Issue:** Three header icon buttons have no `onClick`.  
**Fix (minimal):** Remove buttons if the features don't exist. Or wire to a "feature not available" toast. Do not show actionable buttons that do nothing.

### P2-7: Messages — Context Panel "Suggested Actions" Broken
**File:** `src/components/Messages.tsx`  
**Issue:** Suggested action buttons in the context panel have no `onClick`.  
**Fix:** Wire each to the appropriate `onNavigate` call based on the action label.

### P2-8: Account — "Add Credits," Quick Settings Buttons Broken
**File:** `src/components/Account.tsx`  
**Issue:** "Add Credits," Security, Notifications, and Integrations buttons have no handlers.  
**Fix:** "Add Credits" → open Stripe checkout or a coming-soon modal. Quick Settings → navigate to Settings tab sub-sections. Nexus Credits balance → read from a `user_credits` table (add to schema) or hide the card entirely until credits are implemented.

### P2-9: Settings — Multiple Broken Buttons
**File:** `src/components/Settings.tsx`  
**Issue:** Avatar upload, "Change Password," "Download My Data," "Help Center," "Contact Support," "Manage Subscription" all have no handlers. Security/Integrations tabs show placeholder text.  
**Fix (prioritized):**
- Avatar upload → wire to Supabase Storage bucket, update `user_profiles.avatar_url`.
- "Change Password" → call Supabase `auth.updateUser({ password: newPw })` with a confirmation modal.
- "Manage Subscription" → navigate to Stripe customer portal or `admin/subscriptions`.
- "Help Center" / "Contact Support" → `window.open` to support URL or navigate to Messages.
- "Download My Data" → export user's `user_profiles` + `tasks` + `documents` as JSON.

### P2-10: Admin Dashboard — "View" Button and "System Report" Broken
**File:** `src/components/admin/AdminDashboard.tsx`  
**Issue:** "View" button on client rows has no `onClick`. "System Report" has no `onClick`.  
**Fix:** "View" → navigate admin to AdminClients and auto-select/scroll to that client. "System Report" → generate and display or download platform-wide metrics as JSON/CSV.

### P2-11: Admin Credit Ops — "New Case" and No Per-Row Actions
**File:** `src/components/admin/AdminCreditOps.tsx`  
**Issue:** "New Case" button has no `onClick`. Admin cannot update dispute status per row.  
**Fix:** "New Case" → open modal to create a `credit_disputes` row for a selected user. Per-row → add "Resolve," "Reject," "Update Status" actions that write to `credit_disputes.status`.

### P2-12: Admin Settings — Settings Items Are All Placeholder
**File:** `src/components/admin/AdminSettings.tsx`  
**Issue:** All settings items except Subscriptions are hover decorations. No functionality behind any item.  
**Fix (minimum):** For each item, either build a minimal implementation panel, or remove the item and add a "Coming Soon" label. "View System Logs" → link to Supabase logs or a `audit_log` table query.

### P2-13: Admin AI Workforce — Agent Search Not Wired
**File:** `src/components/admin/AdminAIWorkforce.tsx`  
**Issue:** Agent search input has no onChange connected to the bot list filter.  
**Fix:** Add `searchQuery` state, filter `bots` array by `name` or `role`, wire input to state.

### P2-14: Grants Finder — "Save Search" and "Talk to Your AI" Broken
**File:** `src/components/GrantsFinder.tsx`  
**Issue:** Both buttons have no `onClick`.  
**Fix:** "Save Search" → insert a row to a `saved_searches` table (add to schema) or store in `user_settings.saved_grant_searches`. "Talk to Your AI" → call `onNavigate('messages')` or open FloatingChat.

### P2-15: BankBehavior — Duplicate Month Inserts Possible
**File:** `src/components/BankBehavior.tsx`  
**Issue:** `handleSave` uses `insert` not `upsert`. Users who submit the same month twice create duplicate snapshot rows.  
**Fix:** Change to `upsert` with `onConflict: ['user_id', 'snapshot_month']`. Add `UNIQUE(user_id, snapshot_month)` constraint to migration.

### P2-16: Trading Lab Research Section — Static and Broken Buttons
**File:** `src/components/TradingLab.tsx`  
**Issue:** Performance data and backtest results are hardcoded. "Try Demo" and "Journal" have no `onClick`.  
**Fix:** "Try Demo" → pre-populate the Paper Account open trade form with a sample trade. "Journal" → open a notes modal that writes to a `trade_journal` table (or re-use `tasks`). Static data can remain for now with a clear "example data" label.

### P2-17: Admin Welcome Email Not Actually Sent
**File:** `src/components/admin/AdminInviteUsers.tsx`  
**Issue:** "Send Welcome Email" only updates `invite_status` in DB. No email is delivered.  
**Fix:** Call a Supabase Edge Function (e.g., `send-invite-email`) that uses Resend or SendGrid to deliver the email. Pass the invite record ID. The Edge Function reads name, email, and signup_link from DB.

### P2-18: FloatingChat — React Hook Order Violation
**File:** `src/components/FloatingChat.tsx`  
**Issue:** `isFeatureEnabled('floating_chat')` is called and a conditional `return null` may occur before all hooks run. This violates React's rules of hooks and can cause errors under Strict Mode or future refactors.  
**Fix:** Move the feature flag check below all hook declarations, or lift the flag into the parent component (App.tsx) and conditionally render `<FloatingChat />` there.

---

## Recommended Implementation Order

1. **P0-1** — Fix GrantsFinder crash (1 line rename, 15 minutes)
2. **P0-3** — Wire "New Application" button with a save modal (2 hours)
3. **P0-2** — Wire credit report upload with at least manual entry form (4 hours)
4. **P1-1** — Persist LLC Setup steps to DB (2 hours)
5. **P1-5** — Fix Action Center Refresh + Chat with Advisor (30 minutes)
6. **P1-6** — Replace static Action Center data with live DB reads (3 hours)
7. **P1-8** — Connect bank behavior score to Funding Readiness calculation (1 hour)
8. **P1-2** — Wire Roadmap action checkboxes to DB (2 hours)
9. **P1-12** — Admin Clients "Manage" side-panel (4 hours)
10. **P1-3** — Credit Boost "See Options" generic modal for other categories (2 hours)
11. **P2-1** — Replace Dashboard hardcoded fallback data with empty states (1 hour)
12. **P2-3** — Funding pipeline bars and lender matches from DB (2 hours)
13. **P2-9** — Settings: avatar upload + change password (3 hours)
14. **P2-17** — Admin invite email via Edge Function (3 hours)
15. **P2-18** — FloatingChat hook order fix (30 minutes)
16. Remaining P1 and P2 items in priority order above

**Estimated minimum viable hours to resolve all P0 + P1 items:** ~30 hours of focused development  
**Estimated full P2 cleanup:** additional ~25 hours
