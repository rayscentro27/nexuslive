# Nexus Platform — Functionality Audit
**Date:** 2026-05-03  
**Auditor:** Claude Code (read-only pass)  
**Scope:** All client and admin components + migration SQL  

**Status Codes**
| Code | Meaning |
|------|---------|
| ✅ WORKS | Has click handler / DB operation / navigation confirmed functional |
| ⚠️ PARTIAL | Partially functional — some sub-features broken or DB write missing |
| ❌ BROKEN | Missing onClick, navigation dead-end, or runtime error |
| 🔲 STATIC | Hardcoded data with no DB read or write |

---

## 1. App.tsx — Core Routing & Navigation

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| URL-based routing (`/app/*` React Router) | ✅ WORKS | Routes map correctly to components |
| State-based tab routing (SPA dock) | ✅ WORKS | `activeTab` state drives render |
| Bottom dock — 11 client nav items | ✅ WORKS | `dashboard`, `credit`, `funding`, `roadmap`, `business`, `action-center`, `documents`, `messages`, `trading`, `grants`, `account` |
| `business-setup` tab | ⚠️ PARTIAL | Exists in state router; NOT in dock — only reachable via `onNavigate` calls from Dashboard / FundingReadiness |
| `funding-readiness` tab | ⚠️ PARTIAL | Exists in state router; NOT in dock — reachable only via FundingReadiness button callbacks |
| `bank-behavior` tab | ⚠️ PARTIAL | Exists in state router; NOT in dock — reachable only via FundingReadiness |
| Admin portal switcher | ✅ WORKS | Visible only to `admin`/`super_admin` roles; toggles `portal` state |
| FloatingChat global render | ⚠️ PARTIAL | Renders globally; see FloatingChat hook-order bug below |
| NotificationBell | ✅ WORKS | Subscribes via NotificationContext |
| PlanGate (pro/elite gating) | ✅ WORKS | Wraps Trading Lab, some credit features |

---

## 2. Dashboard

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `user_profiles`, `tasks`, `activity_log`, `credit_reports` | ✅ WORKS | Live data |
| Funding range display | ⚠️ PARTIAL | Falls back to hardcoded $13k–$75k if no credit report on file |
| Activity log fallback | ⚠️ PARTIAL | Shows hardcoded activity if DB table empty |
| Readiness breakdown item clicks → navigate to tabs | ✅ WORKS | `onNavigate` calls go to valid tabs |
| "Upload Report" button | ✅ WORKS | Navigates to `credit` tab via `onNavigate` |
| Quick action buttons | ✅ WORKS | Navigate to correct tabs |
| Funding readiness score card | ✅ WORKS | Reads from `funding_readiness_snapshots` |

---

## 3. Credit Analysis

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `credit_reports` | ✅ WORKS | Displays score, band, utilization |
| Three tabs (Analysis / Boost Engine / Simulator) | ✅ WORKS | Tab switching works |
| "Generate Dispute Letters" button | ❌ BROKEN | No `onClick` handler |
| "View Disputes" button | ❌ BROKEN | No `onClick` handler |
| "View Utilization" button | ❌ BROKEN | No `onClick` handler |
| "Upload New Report" file drop zone | ❌ BROKEN | No file handler attached |
| Credit Boost Engine sub-tab | ✅ WORKS | Renders `CreditBoostEngine` |
| Approval Simulator sub-tab | ✅ WORKS | Renders `ApprovalSimulator` |

---

## 4. Credit Boost Engine

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `credit_boost_opportunities`, `credit_boost_actions` | ✅ WORKS | Live catalog + user actions |
| Category filter tabs | ✅ WORKS | Filters opportunities list |
| "Add to Plan" button | ✅ WORKS | Upserts to `credit_boost_actions` AND inserts to `tasks` |
| "See Options" button — `rent_reporting` category | ✅ WORKS | Opens `RentKharmaModal` |
| "See Options" button — all other categories | ❌ BROKEN | No-op; only rent_reporting handled |
| RentKharmaModal: reads `rent_reporting_providers` | ✅ WORKS | Live DB read |
| RentKharmaModal: "Add to Action Center" | ✅ WORKS | Calls `onAddToPlan` which upserts |

---

## 5. Approval Simulator

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `lender_rules`, `credit_reports` | ✅ WORKS | Live data |
| "Run Simulation" button | ✅ WORKS | Computes approval odds locally; sorted by odds |
| Simulation result display | ✅ WORKS | Shows lender, odds, estimated limit, risk factors |
| No DB write on simulation | ⚠️ PARTIAL | `approval_simulations` table exists in schema but component never writes to it |
| "Apply" / lender action button | ❌ BROKEN | No button present in results; user cannot proceed to apply |
| Re-run simulation | ✅ WORKS | Resets and allows re-run |

---

## 6. Business Foundation

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| Foundation tab: reads/writes `business_entities` | ✅ WORKS | Edit/Save via `upsertBusinessEntity` |
| LLC Setup tab: provider links | ✅ WORKS | `window.open` via anchor tags |
| LLC Setup tab: step completion | ❌ BROKEN | `completedSteps` is local state only — not persisted to DB |
| Business Credit tab: reads/writes `business_credit_profiles` | ✅ WORKS | Upsert on `user_id` |
| Vendors tab: reads `vendor_tradelines_catalog` | ✅ WORKS | Live catalog |
| Vendors tab: "Apply" button | ✅ WORKS | Upserts to `user_vendor_accounts`, inserts `tasks`, opens `application_url` |
| Vendors tab: applied status badge | ✅ WORKS | Reads `user_vendor_accounts` |

---

## 7. Funding

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `user_profiles`, `funding_applications`, `tasks` | ✅ WORKS | Live data |
| Five tabs (Overview / Applications / Pipeline / Strategy / History) | ✅ WORKS | Tab switching works |
| "New Application" button | ❌ BROKEN | No `onClick` handler |
| Pipeline bars | 🔲 STATIC | Hardcoded percentages; no DB source |
| Lender Matches section | 🔲 STATIC | Hardcoded lender list |
| Strategy tab checklist | ❌ BROKEN | Local state only; not persisted |
| "Apply at Issuer" card links | ✅ WORKS | Anchor tags with `target="_blank"` |
| Applications list (if any records exist) | ✅ WORKS | DB-driven display |

---

## 8. Funding Readiness

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `funding_readiness_snapshots` | ✅ WORKS | Shows latest snapshot |
| "Recalculate" button | ✅ WORKS | Pulls live credit/entity/business_credit data; inserts new snapshot row |
| Factor navigation buttons | ✅ WORKS | Call `onNavigate` to correct tabs |
| Bank behavior factor | ❌ BROKEN | Always returns null (explicitly noted in code) |
| Snapshot history | ✅ WORKS | Multiple rows shown in order |

---

## 9. Funding Roadmap

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `funding_stages` with joined `funding_actions` | ✅ WORKS | Falls back to `STATIC_STAGES` if DB empty |
| Stage cards display | ✅ WORKS | Status, requirements shown |
| Action step checkboxes | ❌ BROKEN | Display only; no toggle/DB write |
| "View Funding Options" button | ❌ BROKEN | No `onClick` handler |
| Static fallback stages | 🔲 STATIC | 4 hardcoded stages if DB empty |

---

## 10. Grants Finder

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `grants_catalog` | ✅ WORKS | Falls back to 4 `STATIC_GRANTS` if DB empty |
| Search input | ✅ WORKS | Filters by title/description/category |
| Category filter tabs | ✅ WORKS | Filters grant list |
| "Apply" button (with `official_url`) | ✅ WORKS | Anchor tag opens external URL |
| "Apply" button (without `official_url`) | ❌ BROKEN | Renders as dead button with no action |
| "Save Search" button | ❌ BROKEN | No `onClick` handler |
| `opportunities` variable reference | ❌ BROKEN | **Runtime ReferenceError crash** — variable used in JSX but never defined in the component |
| "Talk to Your AI" button | ❌ BROKEN | No `onClick` handler |
| Grant Research Request section | ✅ WORKS | Renders `GrantResearchRequest` component |

---

## 11. Grant Research Request

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `grant_review_requests` | ✅ WORKS | Shows existing request if any |
| Form submit | ✅ WORKS | Inserts to `grant_review_requests` with status `pending` |
| Notification on submit | ✅ WORKS | Also inserts to `notifications` table |
| Response display (when admin responds) | ✅ WORKS | Shows `response` field when populated |

---

## 12. Trading Lab

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| Research Lab — performance data | 🔲 STATIC | Hardcoded `performanceData` arrays |
| Research Lab — backtest results | 🔲 STATIC | Hardcoded `backtestResults` |
| Research Lab — "Try Demo" button | ❌ BROKEN | No `onClick` handler |
| Research Lab — "Journal" button | ❌ BROKEN | No `onClick` handler |
| Paper Account — DB reads: `paper_trading_accounts`, `paper_trades` | ✅ WORKS | Live data |
| Paper Account — auto-create account | ✅ WORKS | Creates account with $10,000 balance if none exists |
| Paper Account — Open Trade | ✅ WORKS | Writes to `paper_trades`, updates balance |
| Paper Account — Close Trade | ✅ WORKS | Writes to DB, updates P&L and balance |
| Market prices for trade entry | ❌ BROKEN | Manually entered; no live market data feed |

---

## 13. Documents

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `documents` | ✅ WORKS | Live document list |
| Upload — Supabase Storage `documents` bucket | ✅ WORKS | Writes to storage then inserts to `documents` table |
| Delete document | ✅ WORKS | Deletes from `documents` table |
| View / Download | ✅ WORKS | Anchor tags with signed URLs |
| "Upload Now" sidebar buttons | ✅ WORKS | Trigger file input |
| Storage usage bar | ✅ WORKS | Calculated from actual file sizes |

---

## 14. Messages

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads/creates: `chat_conversations`, `chat_messages` | ✅ WORKS | `getOrCreateConversation` pattern |
| Send message | ✅ WORKS | Inserts user message; calls Gemini; persists bot response |
| Search bar input | ❌ BROKEN | Input rendered but not connected to any filter logic |
| Phone / Video / MoreVertical icon buttons | ❌ BROKEN | No `onClick` handlers |
| Context panel "Suggested Actions" buttons | ❌ BROKEN | No `onClick` handlers |
| 65% readiness in sidebar | 🔲 STATIC | Hardcoded value |

---

## 15. Floating Chat

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| Create/reuse `chat_conversations` (contact `nexus-support`) | ✅ WORKS | `getOrCreateConversation` |
| Send message + DB persist | ✅ WORKS | Inserts user message |
| Auto-acknowledge canned response | ✅ WORKS | 800ms timeout inserts bot response to DB |
| Quick chips by active tab | ✅ WORKS | Context-aware suggestions |
| Feature flag check order | ⚠️ PARTIAL | `isFeatureEnabled` called before hooks complete — React rules violation; may misbehave under Strict Mode |

---

## 16. Notifications

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| Fetch notifications on mount | ✅ WORKS | Reads `notifications` table |
| Real-time subscription (Supabase Realtime) | ✅ WORKS | Subscribes to INSERT events |
| Toast for priority >= 2 | ✅ WORKS | Auto-dismisses |
| Mark read | ✅ WORKS | Updates `read_at` in DB |
| Mark all read | ✅ WORKS | Bulk update |
| Dismiss notification | ✅ WORKS | Updates `dismissed_at` in DB |
| "View all" link | ✅ WORKS | Calls `onOpenPage` callback |
| Dropdown shows last 10 | ✅ WORKS | Sliced from sorted array |

---

## 17. Action Center

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `tasks` | ✅ WORKS | Live task list |
| Starter tasks fallback | ⚠️ PARTIAL | `STARTER_TASKS` have fake IDs 0–6; `handleComplete` silently skips them (ID length <= 1 guard) |
| "Complete" task toggle (real tasks) | ✅ WORKS | Updates DB for genuine UUID tasks |
| "Refresh" button | ❌ BROKEN | No `onClick` handler |
| "Chat with Advisor" button | ❌ BROKEN | No `onClick` or navigation |
| Business Setup checklist | 🔲 STATIC | Hardcoded items; not DB-driven |
| Recent Alerts | 🔲 STATIC | Hardcoded; not from `notifications` table |
| "Grants Eligible: 3" | 🔲 STATIC | Hardcoded count |

---

## 18. Account

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `user_profiles`, `business_entities`, `user_access_overrides` | ✅ WORKS | Live data |
| Edit display name | ✅ WORKS | Writes to `user_profiles` |
| Pilot access badge | ✅ WORKS | Shown when `subscription_required === false` |
| Profile completion widget | ✅ WORKS | Dynamic percentage from DB fields |
| "Add Credits" button | ❌ BROKEN | No `onClick` handler |
| "Security & Privacy" settings button | ❌ BROKEN | No navigation |
| "Notifications" settings button | ❌ BROKEN | No navigation |
| "Integrations" settings button | ❌ BROKEN | No navigation |
| Sign Out | ✅ WORKS | Calls `signOut` from AuthProvider |
| Nexus Credits display | 🔲 STATIC | Hardcoded $0 / 0 credits |

---

## 19. Settings

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `user_profiles`, `user_settings`, `business_entities` | ✅ WORKS | Live data |
| Profile name save | ✅ WORKS | Writes to `user_profiles` |
| Notification toggles | ✅ WORKS | Write to `user_settings` |
| 2FA toggle | ✅ WORKS | Writes to `user_settings` |
| Avatar upload button | ❌ BROKEN | No file handler |
| "Change Password" button | ❌ BROKEN | No `onClick` handler |
| "Download My Data" button | ❌ BROKEN | No `onClick` handler |
| "Help Center" button | ❌ BROKEN | No `onClick` handler |
| "Contact Support" button | ❌ BROKEN | No `onClick` handler |
| "Manage Subscription" button | ❌ BROKEN | No `onClick` handler |
| Security tab content | 🔲 STATIC | Placeholder text only |
| Integrations tab content | 🔲 STATIC | Placeholder text only |

---

## 20. Admin Portal

### 20a. Admin Dashboard

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `user_profiles`, `documents`, `funding_applications`, `bot_profiles` | ✅ WORKS | Live metrics |
| Client list with key metrics | ✅ WORKS | DB-driven |
| "View" button on client rows | ❌ BROKEN | No `onClick` handler |
| "System Report" button | ❌ BROKEN | No `onClick` handler |

### 20b. Admin Clients

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `user_profiles` | ✅ WORKS | All clients listed |
| Search by name / plan | ✅ WORKS | Client-side filter |
| Sort by readiness / joined / plan | ✅ WORKS | Client-side sort |
| "Manage" button per client row | ❌ BROKEN | No `onClick` handler |

### 20c. Admin Invite Users

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| Invite form submit | ✅ WORKS | Inserts to `invited_users` |
| Update invite status | ✅ WORKS | Updates `invited_users` in DB |
| "Activate" subscription | ✅ WORKS | Updates `invited_users` + `user_access_overrides` + inserts `notifications` |
| "Revoke" / "Restore" access | ✅ WORKS | Updates `user_access_overrides` |
| "Send Welcome Email" | ⚠️ PARTIAL | Updates `invite_status` to 'sent' in DB only; no actual email sent (no Edge Function call) |

### 20d. Admin Grant Reviews

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `grant_review_requests` | ✅ WORKS | All requests with stats (total / pending / completed) |
| "Respond to Request" → textarea + submit | ✅ WORKS | Updates `grant_review_requests`, inserts notification to user |
| Status badges | ✅ WORKS | Visual pending/completed display |

### 20e. Admin AI Workforce

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `bot_profiles` | ✅ WORKS | Live agent list |
| Agent selection / detail panel | ✅ WORKS | Shows efficiency, status, division, description |
| System prompt textarea | ⚠️ PARTIAL | Editable in UI; Save button has no `onClick` — not persisted |
| Pause / Restart buttons | ❌ BROKEN | No `onClick` handlers |
| "Deploy New AI" button | ❌ BROKEN | No `onClick` handler |
| DB reads Activity tab: `ai_employee_runs` | ✅ WORKS | Live run history |
| DB reads Events tab: `ai_agent_events` | ✅ WORKS | Live event log |
| "Refresh" button | ✅ WORKS | Calls `loadActivity` |
| Agent search input | ❌ BROKEN | Input rendered; not connected to any filter |

### 20f. Admin Funding

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `funding_applications` via `getAllFundingApplications` | ✅ WORKS | All clients' applications |
| Stats: pipeline total, avg deal, approval rate, pending count | ✅ WORKS | Computed from live data |
| Applications table with search | ✅ WORKS | Search by lender/product/status |
| Per-row action buttons | ❌ BROKEN | No way for admin to update application status or add notes |

### 20g. Admin Credit Ops

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| DB reads: `credit_reports`, `credit_disputes` | ✅ WORKS | Live data from all users |
| Disputes / Reports tab switch | ✅ WORKS | Correct table rendered |
| Search disputes and reports | ✅ WORKS | Client-side filter |
| "New Case" button | ❌ BROKEN | No `onClick` handler |
| Per-row dispute actions | ❌ BROKEN | Admin cannot update dispute status or resolve cases |

### 20h. Admin Settings / Subscription Settings

| Widget / Action | Status | Notes |
|----------------|--------|-------|
| Settings section navigation | ✅ WORKS | Switches section within panel |
| "Billing & Plans" → AdminSubscriptionSettings | ✅ WORKS | Section switch works |
| Subscription plan price / commission / Stripe ID edits | ✅ WORKS | Local state updated |
| Save plans | ✅ WORKS | Upserts all plans to `subscription_plans` |
| Active toggle per plan | ✅ WORKS | Saved via Save button |
| All other settings items (Branding, Email, Auth, API Keys, Backup, Integrations) | ❌ BROKEN | No functional implementations; "Configure" is hover-only decoration |
| "View System Logs" button | ❌ BROKEN | No `onClick` handler |

---

## Summary Counts

| Status | Count |
|--------|-------|
| ✅ WORKS | 91 |
| ⚠️ PARTIAL | 13 |
| ❌ BROKEN | 47 |
| 🔲 STATIC | 12 |
| **Total items audited** | **163** |

**Critical crash bug:** `GrantsFinder.tsx` references an `opportunities` variable in JSX that is never defined anywhere in the component — causes a `ReferenceError` that crashes the entire Grants page on load for every user.
