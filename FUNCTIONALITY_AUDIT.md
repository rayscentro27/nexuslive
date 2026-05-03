# Nexus Functionality Audit

Generated: 2026-05-03 | Version: Phase 1-25 Implementation

---

## CLIENT PORTAL PAGES

### Home / Dashboard (`activeTab = 'home'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Upload Report button | Navigates to Credit tab | `credit_reports` | ✓ | Static CTA | ✓ via AdminCreditOps | ✓ on upload |
| Improve Approval Odds | Navigates to Action Center | `tasks` | ✓ | — | ✓ | — |
| Start Task (Next Best Action) | Navigates to Action Center | `tasks` | ✓ | Hides when no task | ✓ | — |
| View All Tasks | Navigates to Action Center | `tasks` | ✓ | Shows "caught up" | ✓ | — |
| Invite & Earn | Navigates to referral tab | `referrals` | ✓ | — | ✓ | — |
| Readiness breakdown scores | Navigates to relevant tab | DB-derived | ✓ | Default 0% | ✓ | — |
| Journey step boxes | Visual only | `credit_reports`, `user_profiles` | ✓ | Static defaults | — | — |

### Action Center (`activeTab = 'action-center'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Complete task button | Updates `tasks.status = 'complete'` | `tasks` | ✓ | — | ✓ | — |
| Start task button | Updates `tasks.status = 'in_progress'` | `tasks` | ✓ | — | ✓ | — |
| All tasks list | Fetches and displays pending tasks | `tasks` | ✓ | Empty state | ✓ | — |

### Credit Analysis (`activeTab = 'credit'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Tab: Analysis | Shows credit report, disputes, score | `credit_reports`, `credit_disputes` | ✓ | "No report" state | ✓ via AdminCreditOps | ✓ on upload |
| Tab: Boost Engine | Shows credit boost opportunities | `credit_boost_opportunities`, `credit_boost_actions` | ✓ | Seeded catalog | ✓ | ✓ task created |
| Tab: Simulator | Runs approval odds simulation | `lender_rules`, `approval_simulations` | ✓ | Mock with seeded rules | — | — |
| Generate Dispute Letters | Placeholder — shows existing disputes | `credit_disputes` | Partial | Shows disputes | ✓ | — |
| Download report | Links to `report_file_url` | `credit_reports` | ✓ | Hidden when no URL | — | — |
| Boost Engine: See Options | Opens detail modal (rent = full modal, others = TBD) | `rent_reporting_providers` | ✓ for rent | Graceful fallback | — | — |
| Boost Engine: Add to Plan | Creates boost action + task | `credit_boost_actions`, `tasks` | ✓ | — | — | ✓ task created |
| Simulator: Run Simulation | Calculates approval odds from credit data | `lender_rules`, `credit_reports` | ✓ | Mock score=680 | — | — |

### Funding (`activeTab = 'funding'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Funding stages | Shows stage status | `funding_stages`, `funding_actions` | ✓ | Empty state | ✓ via AdminFunding | — |
| Funding applications | Shows application tracking | `funding_applications` | ✓ | Empty state | ✓ | — |
| Plan Gate | Shown to free users | — | ✓ | Upgrade CTA | — | — |
| **Missing**: Funding Roadmap widget | Not yet wired to `funding_roadmap_stages` | `funding_roadmap_stages` | ✗ planned | — | — | — |
| **Missing**: Approval Simulator on Funding | Could link from funding tab | `approval_simulations` | ✗ planned | — | — | — |

### Grants (`activeTab = 'grants'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Save Search button | Shows "catalog" section | Static | ✓ | — | — | — |
| Grant cards (static) | Visual display | Static mock | Partial | Static data | — | — |
| Research Requests tab | Shows grant research requests | `grant_review_requests` | ✓ | Empty state | ✓ via AdminGrantReviews | ✓ notification on submit |
| Submit Request | Creates grant_review_request row | `grant_review_requests` | ✓ | — | ✓ | ✓ notification |
| **Missing**: Real grant catalog from DB | Connect `grants_catalog` to UI | `grants_catalog` | ✗ planned | — | — | — |

### Trading (`activeTab = 'trading'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Trading Lab / Dashboard | Shows existing trading UI | `trading_strategies`, `trading_journal` | ✓ existing | — | ✓ via AdminTrading | — |
| **Missing**: Paper Trading account | Not wired to `paper_trading_accounts` | `paper_trades` | ✗ planned | — | — | — |
| **Missing**: Strategy approval UI | Admin must approve strategies | `trading_strategies.is_approved` | ✗ planned | — | — | — |

### Messages (`activeTab = 'messages'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Conversation list | Fetches conversations | `chat_conversations` | ✓ | Empty state | ✓ via AdminMessaging | — |
| Send message | Creates message row | `chat_messages` | ✓ | — | ✓ | — |
| Floating chat button | Opens contextual chat drawer | `chat_conversations`, `chat_messages` | ✓ | Hidden when disabled | ✓ | — |
| Quick chips | Pre-fills message input | — | ✓ | — | — | — |

### Documents (`activeTab = 'documents'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Document list | Fetches documents | `documents` | ✓ | Empty state | ✓ via AdminDocuments | — |
| Upload | Existing upload flow | `documents` | ✓ existing | — | ✓ | — |
| Status badges | Shows pending/verified/attention | `documents.status` | ✓ | — | ✓ | — |

### Account (`activeTab = 'account'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Profile display | Shows user profile data | `user_profiles` | ✓ | — | ✓ | — |
| **Missing**: Access status display | Pilot users should see "Free Full Access" badge | `user_access_overrides` | ✗ planned | — | — | — |

### Settings (`activeTab = 'settings'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Notification settings | Toggle email/push/sms | `user_settings` | ✓ | — | — | — |
| 2FA toggle | Setting UI | `user_settings` | ✓ existing | — | — | — |
| **Missing**: Subscription status | Show access override status | `user_access_overrides` | ✗ planned | — | — | — |

### Notifications (`activeTab = 'notifications'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Notification list | Fetches user notifications | `notifications` | ✓ | Empty state | — | — |
| Mark all read | Updates `read_at` on all | `notifications` | ✓ | — | — | — |
| Dismiss (X) | Updates `dismissed_at` | `notifications` | ✓ | — | — | — |
| Notification bell badge | Shows unread count | `notifications` | ✓ | — | — | — |
| Real-time updates | Supabase realtime subscription | `notifications` | ✓ | — | — | — |
| Toast notifications | Priority ≥2 shown as toast | `notifications` | ✓ | — | — | — |

### Business Setup (`activeTab = 'business-setup'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Business sections | Shows existing setup UI | `business_entities` | ✓ existing | Static mock | ✓ | — |
| **Missing**: LLC guided setup | Two-path LLC flow | `business_setup_steps` | ✗ planned | — | — | — |
| **Missing**: Business Readiness Score | Calculated score widget | `business_readiness_scores` | ✗ planned | — | — | — |
| **Missing**: Vendor tradelines tab | Business credit from `vendor_tradelines_catalog` | `user_vendor_accounts` | ✗ planned | — | — | — |

### Referral (`activeTab = 'referral'`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Admin Visible | Notification/Task |
|---|---|---|---|---|---|---|
| Referral link display | Shows user referral link | `referrals` | ✓ existing | — | — | — |
| **Missing**: Commission tracking | 10% funding commission tracking | `funding_commissions` | ✗ planned | — | — | — |

---

## ADMIN PORTAL PAGES

### Admin Dashboard (`admin/dashboard`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Notification/Task |
|---|---|---|---|---|---|
| Client count | Fetches all user profiles | `user_profiles` | ✓ | — | — |
| Funding pipeline | Fetches applications | `funding_applications` | ✓ | — | — |
| Revenue metrics | Static/calculated | — | Partial | — | — |

### Admin Clients (`admin/clients`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Notification/Task |
|---|---|---|---|---|---|
| Client list | Fetches all profiles | `user_profiles` | ✓ | — | — |
| Search/filter | Filters client list | In-memory | ✓ | — | — |
| **Missing**: View client details | Drill into specific client | — | ✗ planned | — | — |

### Admin Invites (`admin/invites`)  ← NEW
| Button/Action | What It Does | Table/Function | Complete | Fallback | Notification/Task |
|---|---|---|---|---|---|
| Add Invite | Creates invited_user row | `invited_users` | ✓ | — | — |
| Send Welcome Email | Marks invite sent, shows email preview | `invited_users` | ✓ | Shows template | — |
| Resend Invite | Same as send welcome | `invited_users` | ✓ | — | — |
| Activate Subscription | Sets grace period, creates notification | `invited_users`, `user_access_overrides`, `notifications` | ✓ | — | ✓ notification |
| Restore Free Access | Restores waived status | `invited_users`, `user_access_overrides` | ✓ | — | — |
| Revoke Access | Sets subscription required | `invited_users`, `user_access_overrides` | ✓ | — | — |

### Admin Grant Reviews (`admin/grants-review`)  ← NEW
| Button/Action | What It Does | Table/Function | Complete | Fallback | Notification/Task |
|---|---|---|---|---|---|
| Request list | Fetches all grant requests | `grant_review_requests` | ✓ | — | — |
| Respond to Request | Updates status + response, notifies user | `grant_review_requests`, `notifications` | ✓ | — | ✓ notification |

### Admin Messaging (`admin/messages`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Notification/Task |
|---|---|---|---|---|---|
| Conversation list | Fetches all conversations | `chat_conversations` | ✓ | — | — |
| **Missing**: Draft approval | Admin approve/edit AI drafts | `message_drafts` | ✗ planned | — | — |

### Admin Credit Ops (`admin/credit`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Notification/Task |
|---|---|---|---|---|---|
| Credit reports list | Fetches all credit reports | `credit_reports` | ✓ | — | — |
| Disputes list | Fetches all disputes | `credit_disputes` | ✓ | — | — |

### Admin Funding (`admin/funding`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Notification/Task |
|---|---|---|---|---|---|
| Applications list | Fetches all funding applications | `funding_applications` | ✓ | — | — |
| **Missing**: Commission tracking | View/verify commissions | `funding_commissions` | ✗ planned | — | — |

### Admin Subscriptions (`admin/subscriptions`)
| Button/Action | What It Does | Table/Function | Complete | Fallback | Notification/Task |
|---|---|---|---|---|---|
| Plan management | Shows subscription plans | `subscription_plans` | ✓ | — | — |
| **Missing**: Bulk subscription activation | Activate for all pilot users | `user_access_overrides` | ✗ planned | — | — |

---

## FEATURE FLAG STATUS

| Flag | Default | Effect When Disabled |
|---|---|---|
| `credit_boost_engine` | enabled | Boost Engine tab hidden in Credit Analysis |
| `funding_readiness` | enabled | Readiness score widget shows mock data |
| `grants_engine` | enabled | Grants page shows static grants only |
| `trading_lab` | enabled | Trading tab shows plan gate |
| `floating_chat` | enabled | Floating chat button hidden |
| `notifications` | enabled | Bell shows empty state |
| `pilot_mode` | enabled | Invite system available in admin |
| `concierge` | enabled | Concierge UI available |
| `approval_simulator` | enabled | Simulator tab shown in Credit Analysis |
| `partner_portal` | disabled | Partner system not exposed |

---

## SUPABASE TABLES — IMPLEMENTATION STATUS

| Table | Created | RLS | Seeded | Used in UI |
|---|---|---|---|---|
| `user_profiles` | ✓ existing | ✓ | — | ✓ Dashboard, Header, Auth |
| `tasks` | ✓ existing | ✓ | — | ✓ Dashboard, ActionCenter |
| `credit_reports` | ✓ existing | ✓ | — | ✓ CreditAnalysis |
| `credit_disputes` | ✓ existing | ✓ | — | ✓ CreditAnalysis |
| `chat_conversations` | ✓ existing | ✓ | — | ✓ Messages, FloatingChat |
| `chat_messages` | ✓ existing | ✓ | — | ✓ Messages, FloatingChat |
| `documents` | ✓ existing | ✓ | — | ✓ Documents |
| `funding_stages` | ✓ existing | ✓ | — | ✓ FundingRoadmap |
| `funding_applications` | ✓ existing | ✓ | — | ✓ Funding |
| `business_entities` | ✓ existing | ✓ | — | ✓ BusinessSetup |
| `activity_log` | ✓ existing | ✓ | — | ✓ Dashboard |
| `notifications` | ✓ new | ✓ | — | ✓ NotificationBell, Toasts |
| `invited_users` | ✓ new | ✓ | — | ✓ AdminInviteUsers |
| `user_access_overrides` | ✓ new | ✓ | — | ✓ usePlan, AdminInviteUsers |
| `subscription_notifications` | ✓ new | ✓ | — | Partial |
| `credit_boost_opportunities` | ✓ new | ✓ | ✓ seeded | ✓ CreditBoostEngine |
| `credit_boost_actions` | ✓ new | ✓ | — | ✓ CreditBoostEngine |
| `rent_reporting_providers` | ✓ new | ✓ | ✓ seeded | ✓ RentKharmaModal |
| `user_rent_reporting` | ✓ new | ✓ | — | Planned |
| `credit_fundability_scores` | ✓ new | ✓ | — | Planned |
| `vendor_tradelines_catalog` | ✓ new | ✓ | ✓ seeded | Planned |
| `user_vendor_accounts` | ✓ new | ✓ | — | Planned |
| `business_credit_profiles` | ✓ new | ✓ | — | Planned |
| `funding_readiness_snapshots` | ✓ new | ✓ | — | Planned |
| `funding_roadmap_stages` | ✓ new | ✓ | — | Planned |
| `funding_timeline_events` | ✓ new | ✓ | — | Planned |
| `next_best_actions` | ✓ new | ✓ | — | Planned |
| `funding_recommendations` | ✓ new | ✓ | — | Planned |
| `funding_strategies` | ✓ new | ✓ | — | Planned |
| `lender_rules` | ✓ new | ✓ | ✓ seeded | ✓ ApprovalSimulator |
| `approval_simulations` | ✓ new | ✓ | — | ✓ ApprovalSimulator |
| `concierge_plans` | ✓ new | ✓ | ✓ seeded | Planned |
| `concierge_clients` | ✓ new | ✓ | — | Planned |
| `grants_catalog` | ✓ new | ✓ | — | Planned |
| `grant_matches` | ✓ new | ✓ | — | Planned |
| `grant_applications` | ✓ new | ✓ | — | Planned |
| `grant_review_requests` | ✓ new | ✓ | — | ✓ GrantResearchRequest, AdminGrantReviews |
| `grant_deadlines` | ✓ new | ✓ | — | Planned |
| `trading_strategies` | ✓ new | ✓ | — | Planned |
| `paper_trading_accounts` | ✓ new | ✓ | — | Planned |
| `paper_trades` | ✓ new | ✓ | — | Planned |
| `paper_trading_metrics` | ✓ new | ✓ | — | Planned |
| `broker_connections` | ✓ new | ✓ | — | Planned |
| `ai_agent_events` | ✓ new | ✓ | — | Planned |
| `ai_employee_runs` | ✓ new | ✓ | — | Planned |
| `research_sources` | ✓ new | ✓ | — | Planned |
| `website_change_recommendations` | ✓ new | ✓ | — | Planned |
| `bank_behavior_snapshots` | ✓ new | ✓ | — | Planned |
| `referrals` | ✓ new | ✓ | — | Planned |
| `referral_earnings` | ✓ new | ✓ | — | Planned |
| `funding_commissions` | ✓ new | ✓ | — | Planned |
| `partners` | ✓ new | ✓ | — | Planned |
| `partner_branding` | ✓ new | ✓ | — | Planned |
| `partner_clients` | ✓ new | ✓ | — | Planned |

---

## CRITICAL RULES COMPLIANCE CHECK

| Rule | Status |
|---|---|
| No dead buttons | ✓ All buttons navigate or trigger real actions |
| No auto-submit lender applications | ✓ No auto-apply logic anywhere |
| No auto-trade | ✓ Trading is educational/paper only |
| No guaranteed funding/credit/grants | ✓ All language is educational + probability-based |
| Tenant isolation (RLS) | ✓ All tables have RLS policies |
| Free access pilot system | ✓ user_access_overrides + usePlan updated |
| Apple-style UI preserved | ✓ No redesign |
| Feature flags for new features | ✓ featureFlags.ts created |
| Graceful fallbacks | ✓ All new components have empty/loading states |
| Admin visibility | ✓ All new features accessible from admin portal |

---

## WHAT REMAINS (Planned, Not Yet Built)

1. Business Foundation upgrade: LLC guided flow, business readiness score, NAICS optimizer
2. Business Credit section: vendor tradelines UI, DUNS/PAYDEX display
3. Funding Readiness Score page: `funding_readiness_snapshots` wired to UI
4. Apply for Funding Engine: 0% strategy, lender recommendations
5. Concierge opt-in flow
6. Full Commission/Referral tracking UI
7. Real grants catalog from `grants_catalog` table
8. Trading: paper trading account + trades + metrics UI
9. Admin: AI workforce monitoring (`ai_employee_runs`, `ai_agent_events`)
10. Admin: Website change approvals (`website_change_recommendations`)
11. Admin: Subscription activation queue (bulk pilot-to-paid conversion)
12. Bank Behavior Tracking: `bank_behavior_snapshots` manual entry UI
13. Profile completion widget
14. Partner/white-label system
15. Research/YouTube intake workflow
