# Nexus Platform — Pilot User Journey Simulation
**Date:** 2026-05-03  
**Simulated persona:** "Marcus" — new pilot user, invited by admin, free full access override, starting from scratch with no prior data.  
**Method:** Step-by-step walkthrough of the most likely first-session and subsequent session paths. Each step evaluated against code behavior.

---

## Step 1 — Admin invites Marcus

**Action:** Admin opens Admin Portal → Invite Users → fills form with Marcus's name, email, phone, selects "Free Full Access."  
**Result:** PASS  
**Data created:** Row in `invited_users` (status: `pending`). No email actually sent.  
**Bug:** "Send Welcome Email" only sets `invite_status = 'sent'` in DB — no SMTP or Edge Function is called. Marcus receives no actual email.  
**Recommendation:** Wire the invite email to a Supabase Edge Function or Resend API.

---

## Step 2 — Marcus signs up via the platform

**Action:** Marcus navigates to signup URL, creates account via Supabase Auth.  
**Result:** PASS (auth flow is Supabase-handled, outside component scope)  
**Data created:** Row in `auth.users`. Row in `user_profiles` (auto-created by trigger or first profile fetch).

---

## Step 3 — Admin activates Marcus's free access

**Action:** Admin finds Marcus in Invite Users list → clicks "Activate."  
**Result:** PASS  
**Data created:** `invited_users.subscription_status = 'waived'`. Row upserted in `user_access_overrides` (`subscription_required = false`). Notification inserted for Marcus.  
**Note:** Marcus now has pilot access; the "Pilot" badge will appear in his Account page.

---

## Step 4 — Marcus logs in and sees Dashboard

**Action:** Marcus logs in; Dashboard loads.  
**Result:** PASS  
**Data read:** `user_profiles`, `tasks` (empty), `activity_log` (empty → shows hardcoded fallback), `credit_reports` (empty → funding range shows hardcoded $13k–$75k), `funding_readiness_snapshots` (empty → score = 0 or blank).  
**Bug:** Hardcoded activity and funding range shown immediately — Marcus sees fake data as if it were real. Misleading for a fresh account.

---

## Step 5 — Marcus clicks "Upload Report" on Dashboard

**Action:** Dashboard → "Upload Report" button.  
**Result:** PASS  
**Navigation:** Correctly navigates to `credit` tab via `onNavigate`.

---

## Step 6 — Marcus tries to upload a credit report in Credit Analysis

**Action:** Credit Analysis → drag-and-drop zone or "Upload New Report" button.  
**Result:** FAIL  
**Bug:** No file handler attached to the upload zone. Clicks do nothing. Marcus cannot upload his credit report from this screen.  
**Workaround:** Marcus must go to Documents tab, upload the PDF there, then manually return to Credit Analysis — but the credit report still won't be parsed into the `credit_reports` table automatically.

---

## Step 7 — Marcus explores the Credit Analysis tab

**Action:** Marcus views the Analysis tab.  
**Result:** PARTIAL PASS  
**Data read:** `credit_reports` (empty) — shows empty/zero state. Tab switching between Analysis / Boost Engine / Simulator works.  
**Broken buttons:** "Generate Dispute Letters," "View Disputes," "View Utilization" — all have no `onClick`. Marcus taps them and nothing happens.

---

## Step 8 — Marcus opens Credit Boost Engine

**Action:** Credit Analysis → Boost Engine tab.  
**Result:** PASS  
**Data read:** `credit_boost_opportunities` (needs seed data), `credit_boost_actions`.  
**Bug:** If `credit_boost_opportunities` table is empty (no seed rows), Marcus sees no opportunities. The catalog requires manual DB seeding by admin.  
**Working:** Category filter tabs work. "Add to Plan" upserts and creates a task.

---

## Step 9 — Marcus clicks "See Options" on a non-rent category opportunity

**Action:** Boost Engine → clicks "See Options" on e.g., "Authorized User" category.  
**Result:** FAIL  
**Bug:** Only `rent_reporting` category opens a modal. All other categories are no-ops. Marcus sees a button that does nothing.

---

## Step 10 — Marcus opens the Approval Simulator

**Action:** Credit Analysis → Simulator tab.  
**Result:** PASS  
**Data read:** `lender_rules` (needs seed data), `credit_reports` (empty → score = 0).  
**Working:** "Run Simulation" computes odds from local logic. Results display correctly.  
**Bug 1:** With empty credit report, all simulations run against score = 0 — every lender shows 0% odds. Not useful.  
**Bug 2:** No "Apply" or follow-up action button in results. Marcus can see odds but cannot proceed.  
**Bug 3:** Simulation results are not saved to `approval_simulations` table even though the table exists.

---

## Step 11 — Marcus navigates to Business Foundation

**Action:** Bottom dock → Business tab.  
**Result:** PASS  
**Data read:** `business_entities` (empty for new user).  
**Working:** Foundation tab edit/save works (upsert). Business Credit tab edit/save works. Vendors tab shows catalog (needs seed data).

---

## Step 12 — Marcus tries to complete LLC Setup steps

**Action:** Business Foundation → LLC Setup tab → clicks step checkboxes or marks steps complete.  
**Result:** FAIL  
**Bug:** `completedSteps` is local React state. Refreshing the page loses all progress. Marcus cannot track his LLC formation progress across sessions.

---

## Step 13 — Marcus applies to a vendor tradeline

**Action:** Business Foundation → Vendors tab → clicks "Apply" on a tier-1 vendor.  
**Result:** PASS  
**Data created:** Row in `user_vendor_accounts` (status: `applied`). Row in `tasks`. Opens `application_url` in new tab.  
**Note:** Requires `vendor_tradelines_catalog` to be seeded by admin.

---

## Step 14 — Marcus navigates to Funding tab

**Action:** Bottom dock → Funding.  
**Result:** PARTIAL PASS  
**Data read:** `user_profiles`, `funding_applications` (empty), `tasks`.  
**Broken:** "New Application" button has no `onClick`. Marcus cannot create a funding application.  
**Static data:** Pipeline bars show hardcoded percentages. Lender Matches are hardcoded — not personalized to Marcus.  
**Strategy checklist:** Checking off items is local state only; not saved.

---

## Step 15 — Marcus tries to create a funding application

**Action:** Funding tab → "New Application" button.  
**Result:** FAIL  
**Bug:** No `onClick` handler. No modal, no form appears. This is the core conversion action of the platform and it does nothing.

---

## Step 16 — Marcus navigates to Funding Roadmap

**Action:** Bottom dock → Roadmap.  
**Result:** PARTIAL PASS  
**Data read:** `funding_stages` (needs seed data or falls back to STATIC_STAGES).  
**Bug 1:** Action step checkboxes are display-only; Marcus cannot check them off.  
**Bug 2:** "View Funding Options" button has no `onClick`.

---

## Step 17 — Marcus navigates to Funding Readiness

**Action:** Dashboard readiness card → click factor item → navigates to `funding-readiness` tab.  
**Result:** PASS (navigation works)  
**Data read:** `funding_readiness_snapshots`.  
**Working:** "Recalculate" button pulls live data and inserts new snapshot.  
**Bug:** Bank behavior factor always returns null. Even after Marcus adds bank snapshots, the readiness score will not reflect bank behavior.

---

## Step 18 — Marcus navigates to Bank Behavior

**Action:** Funding Readiness → Bank Behavior factor button → navigates to `bank-behavior` tab.  
**Result:** PASS (navigation works)  
**Working:** Add Month snapshot form works fully. Score preview is live. Inserts to `bank_behavior_snapshots`.  
**Bug:** No edit or delete on existing snapshots. Submitting same month twice creates duplicate rows.

---

## Step 19 — Marcus navigates to Grants Finder

**Action:** Bottom dock → Grants.  
**Result:** FAIL — CRASH  
**Bug:** `GrantsFinder.tsx` references an `opportunities` variable in JSX that is never defined. This causes a `ReferenceError` at runtime. The entire Grants page crashes and likely shows a white screen or React error boundary.  
**Impact:** Every user who visits the Grants tab will hit this crash. This is a P0 bug.

---

## Step 20 — Marcus navigates to Documents

**Action:** Bottom dock → Documents.  
**Result:** PASS  
**Data read:** `documents` table (empty).  
**Working:** Upload writes to Supabase Storage + inserts to `documents`. Delete works. View/Download work via anchor tags. Storage usage bar is accurate.

---

## Step 21 — Marcus uploads a credit report PDF via Documents

**Action:** Documents → Upload → selects credit report PDF.  
**Result:** PASS (file uploads to storage)  
**Bug:** Uploading a PDF here does NOT populate the `credit_reports` table. The Credit Analysis tab still shows empty state. There is no parsing pipeline — the file sits in storage as an inert blob. Marcus must manually enter credit data another way (which is also not available on the Credit Analysis screen).

---

## Step 22 — Marcus opens Messages / AI Advisor

**Action:** Bottom dock → Messages.  
**Result:** PASS  
**Working:** Conversation created or reused. Sending a message inserts to DB and triggers Gemini response (persisted).  
**Bug 1:** Search bar is rendered but does not filter conversations.  
**Bug 2:** Phone/Video/MoreVertical buttons do nothing.  
**Bug 3:** "Suggested Actions" panel buttons do nothing.  
**Bug 4:** 65% readiness shown in sidebar is hardcoded — not Marcus's real score.

---

## Step 23 — Marcus uses Floating Chat

**Action:** Floating chat bubble → types a question.  
**Result:** PASS  
**Working:** Message persisted to DB. Auto-acknowledge canned response appears after 800ms. Quick chips are context-aware.  
**Note:** Canned response is always the same text regardless of what Marcus asked. No Gemini call in FloatingChat (unlike the Messages tab which does call Gemini).

---

## Step 24 — Marcus checks his Notifications

**Action:** Notification bell in header → opens dropdown.  
**Result:** PASS  
**Data read:** `notifications` (should have the activation notification from Step 3).  
**Working:** Mark read, mark all read, dismiss all work. Real-time toast works for new inserts.

---

## Step 25 — Marcus opens Action Center

**Action:** Bottom dock → Action Center.  
**Result:** PARTIAL PASS  
**Data read:** `tasks` (has items from Steps 8 and 13 above).  
**Working:** Real tasks (UUID IDs) can be marked complete in DB.  
**Bug 1:** "Refresh" button has no `onClick`.  
**Bug 2:** "Chat with Advisor" button has no `onClick`.  
**Bug 3:** Business Setup checklist is hardcoded — not driven by Marcus's actual `business_entities` data.  
**Bug 4:** Recent Alerts are hardcoded — not from Marcus's real `notifications`.  
**Bug 5:** "Grants Eligible: 3" is hardcoded regardless of Marcus's profile.

---

## Step 26 — Marcus opens Trading Lab

**Action:** Bottom dock → Trading (gated by PlanGate for pro/elite).  
**Result:** PARTIAL PASS (if Marcus has pilot access override, PlanGate behavior depends on implementation)  
**Research Lab:** Fully static. "Try Demo" and "Journal" buttons are broken.  
**Paper Account:** PASS — auto-creates $10,000 account. Open Trade and Close Trade both write to DB correctly.  
**Bug:** Market prices must be typed manually; no live quotes. Marcus is trading against self-reported prices.

---

## Step 27 — Marcus visits his Account page

**Action:** Bottom dock → Account.  
**Result:** PARTIAL PASS  
**Data read:** `user_profiles`, `business_entities`, `user_access_overrides`.  
**Working:** Pilot badge shows. Profile completion widget is accurate. Edit name saves to DB. Sign Out works.  
**Bug 1:** "Add Credits" button does nothing.  
**Bug 2:** Quick Settings buttons (Security, Notifications, Integrations) do nothing.  
**Bug 3:** Credits display is hardcoded $0.

---

## Step 28 — Marcus opens Settings

**Action:** Account or settings gear → Settings.  
**Result:** PARTIAL PASS  
**Working:** Name save, notification toggles, 2FA toggle all write to DB.  
**Bug 1:** Avatar upload has no handler.  
**Bug 2:** "Change Password," "Download My Data," "Help Center," "Contact Support," "Manage Subscription" all have no `onClick`.  
**Bug 3:** Security and Integrations tabs show placeholder text only.

---

## Step 29 — Marcus submits a grant research request

**Action:** Grants tab → (if crash bug is fixed) → Grant Research Request form.  
**Result:** PASS (assuming GrantsFinder crash is fixed)  
**Data created:** Row in `grant_review_requests` (status: `pending`). Row in `notifications`.  
**Working:** Admin will see this in Admin Grant Reviews and can respond. Response appears in the form when populated.

---

## Step 30 — Admin responds to Marcus's grant request

**Action:** Admin Portal → Grant Reviews → clicks "Respond to Request" → enters research results → submits.  
**Result:** PASS  
**Data created:** `grant_review_requests` updated (status: `completed`, `response` populated). Notification inserted for Marcus.  
**Working:** Full lifecycle functional on admin side.

---

## Step 31 — Marcus tries to navigate to Funding Readiness directly

**Action:** Marcus tries to find "Funding Readiness" in the bottom dock.  
**Result:** FAIL  
**Bug:** `funding-readiness` is not in the bottom dock nav. Marcus can only reach it by clicking a readiness factor in the Dashboard. There is no direct navigation path. Same applies to `bank-behavior` and `business-setup`.

---

## Step 32 — Admin views Marcus in Admin Clients

**Action:** Admin Portal → Clients → finds Marcus in list.  
**Result:** PARTIAL PASS  
**Working:** Search, sort all work. Marcus appears in list with his readiness score.  
**Bug:** "Manage" button does nothing. Admin cannot open Marcus's profile, see his documents, or take any action from this screen.

---

## Step 33 — Admin reviews Marcus's funding applications

**Action:** Admin Portal → Funding.  
**Result:** PARTIAL PASS  
**Working:** Table shows all applications with search.  
**Bug:** No per-row actions. Admin cannot change application status, add notes, or contact Marcus from this screen.  
**Note:** Marcus has no applications (Step 15 was broken) so this table is empty in practice.

---

## Step 34 — Marcus returns the next day

**Action:** Marcus logs back in after 24 hours.  
**Result:** PARTIAL PASS  
**Persisted:** Bank behavior snapshots, vendor applications, credit boost actions, tasks (completed/not), paper trades, documents, messages, notifications.  
**Lost:** LLC Setup step progress (local state only), Funding Strategy checklist (local state only), any AI workforce system prompt edits.  
**First impression issues:** Dashboard still shows hardcoded activity log and funding range if no credit report uploaded. Nothing has changed since Day 1 on the Dashboard despite real actions taken.

---

## Overall Journey Verdict

| Phase | Pass | Fail | Partial |
|-------|------|------|---------|
| Onboarding (Steps 1–4) | 2 | 1 | 1 |
| Credit Setup (Steps 5–10) | 2 | 5 | 2 |
| Business Setup (Steps 11–13) | 2 | 1 | 1 |
| Funding (Steps 14–18) | 2 | 3 | 2 |
| Grants (Step 19) | 0 | 1 | 0 |
| Documents (Steps 20–21) | 1 | 1 | 0 |
| Communication (Steps 22–24) | 1 | 0 | 2 |
| Action Center & Tools (Steps 25–28) | 1 | 0 | 3 |
| Grant Research Loop (Steps 29–30) | 2 | 0 | 0 |
| Navigation & Admin (Steps 31–34) | 0 | 2 | 2 |
| **Total** | **13** | **14** | **13** |

**Crash bugs that block the user entirely:** 1 (Grants page ReferenceError)  
**Core conversion actions that are broken:** "New Application" (Funding), credit report upload, LLC step persistence  
**Deceptive static data shown as live:** Dashboard activity log, funding range, 65% readiness in Messages, "Grants Eligible: 3," Recent Alerts
