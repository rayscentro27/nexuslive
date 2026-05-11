create extension if not exists pgcrypto;

create table if not exists public.marketing_campaigns (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  category text not null,
  title text not null,
  description text,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.content_topics (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid references public.marketing_campaigns(id) on delete set null,
  slug text not null unique,
  topic text not null,
  theme text,
  target_stage text default 'prelaunch',
  status text not null default 'idea',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.content_variants (
  id uuid primary key default gen_random_uuid(),
  topic_id uuid not null references public.content_topics(id) on delete cascade,
  platform text not null,
  variant_type text not null default 'short_form',
  hook_draft text,
  script_draft text,
  caption_draft text,
  compliance_notes text,
  status text not null default 'draft_review',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.content_calendar (
  id uuid primary key default gen_random_uuid(),
  variant_id uuid references public.content_variants(id) on delete set null,
  platform text not null,
  scheduled_for timestamptz,
  posting_mode text not null default 'manual',
  status text not null default 'ready_to_post_manually',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.content_approvals (
  id uuid primary key default gen_random_uuid(),
  variant_id uuid not null references public.content_variants(id) on delete cascade,
  approval_type text not null default 'content_review',
  decision text not null default 'pending',
  reviewed_by text,
  review_note text,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.content_performance (
  id uuid primary key default gen_random_uuid(),
  variant_id uuid references public.content_variants(id) on delete set null,
  platform text not null,
  views integer not null default 0,
  likes integer not null default 0,
  comments integer not null default 0,
  saves integer not null default 0,
  shares integer not null default 0,
  clicks integer not null default 0,
  signups integer not null default 0,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.content_learning_notes (
  id uuid primary key default gen_random_uuid(),
  topic_id uuid references public.content_topics(id) on delete set null,
  variant_id uuid references public.content_variants(id) on delete set null,
  note_type text not null default 'learning',
  note text not null,
  created_by text default 'system',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.referrals (
  id uuid primary key default gen_random_uuid(),
  referrer_user_id uuid,
  referred_user_id uuid,
  referral_code text not null,
  status text not null default 'pending_review',
  created_at timestamptz not null default now(),
  converted_at timestamptz
);

create table if not exists public.referral_links (
  id uuid primary key default gen_random_uuid(),
  referrer_user_id uuid,
  referral_code text not null unique,
  destination_url text not null,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.referral_rewards (
  id uuid primary key default gen_random_uuid(),
  referral_id uuid references public.referrals(id) on delete cascade,
  reward_type text not null,
  reward_value numeric(10,2),
  status text not null default 'pending_review',
  reviewed_by text,
  review_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.dm_leads (
  id uuid primary key default gen_random_uuid(),
  handle text not null,
  platform text not null,
  content_topic text,
  intent_category text not null,
  status text not null default 'draft_pending_approval',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.dm_sequences (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references public.dm_leads(id) on delete cascade,
  sequence_name text not null,
  status text not null default 'draft_pending_approval',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.dm_messages (
  id uuid primary key default gen_random_uuid(),
  sequence_id uuid references public.dm_sequences(id) on delete cascade,
  message_order integer not null default 1,
  draft_text text not null,
  status text not null default 'draft_pending_approval',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.dm_approvals (
  id uuid primary key default gen_random_uuid(),
  message_id uuid references public.dm_messages(id) on delete cascade,
  decision text not null default 'pending',
  reviewed_by text,
  review_note text,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.influencer_prospects (
  id uuid primary key default gen_random_uuid(),
  handle text not null,
  platform text not null,
  niche text not null,
  audience_size integer not null default 0,
  status text not null default 'draft_prospect',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.influencer_outreach_messages (
  id uuid primary key default gen_random_uuid(),
  prospect_id uuid references public.influencer_prospects(id) on delete cascade,
  draft_text text not null,
  status text not null default 'draft_pending_approval',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.influencer_followups (
  id uuid primary key default gen_random_uuid(),
  prospect_id uuid references public.influencer_prospects(id) on delete cascade,
  followup_order integer not null default 1,
  draft_text text not null,
  status text not null default 'draft_pending_approval',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.influencer_deals (
  id uuid primary key default gen_random_uuid(),
  prospect_id uuid references public.influencer_prospects(id) on delete cascade,
  deal_type text,
  status text not null default 'pending_review',
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.lead_scores (
  id uuid primary key default gen_random_uuid(),
  lead_ref text not null unique,
  lead_score integer not null default 0,
  segment text not null default 'cold',
  recommended_next_step text,
  recommended_agent text,
  risk_notes text,
  score_payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.lead_events (
  id uuid primary key default gen_random_uuid(),
  lead_ref text not null,
  event_type text not null,
  event_value text,
  created_at timestamptz not null default now()
);

create table if not exists public.lead_segments (
  id uuid primary key default gen_random_uuid(),
  lead_ref text not null,
  segment text not null,
  assigned_at timestamptz not null default now(),
  notes text
);

create table if not exists public.onboarding_events (
  id uuid primary key default gen_random_uuid(),
  user_ref text not null,
  event_type text not null,
  event_value text,
  created_at timestamptz not null default now()
);

create table if not exists public.onboarding_dropoffs (
  id uuid primary key default gen_random_uuid(),
  user_ref text not null,
  stage text not null,
  risk_level text not null default 'medium',
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.onboarding_recommendations (
  id uuid primary key default gen_random_uuid(),
  user_ref text not null,
  user_stage text not null,
  recommended_message text,
  recommended_admin_action text,
  recommended_agent text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists trg_marketing_campaigns_touch on public.marketing_campaigns;
create trigger trg_marketing_campaigns_touch before update on public.marketing_campaigns for each row execute function public.touch_updated_at();
drop trigger if exists trg_content_topics_touch on public.content_topics;
create trigger trg_content_topics_touch before update on public.content_topics for each row execute function public.touch_updated_at();
drop trigger if exists trg_content_variants_touch on public.content_variants;
create trigger trg_content_variants_touch before update on public.content_variants for each row execute function public.touch_updated_at();
drop trigger if exists trg_content_calendar_touch on public.content_calendar;
create trigger trg_content_calendar_touch before update on public.content_calendar for each row execute function public.touch_updated_at();
drop trigger if exists trg_content_approvals_touch on public.content_approvals;
create trigger trg_content_approvals_touch before update on public.content_approvals for each row execute function public.touch_updated_at();
drop trigger if exists trg_content_performance_touch on public.content_performance;
create trigger trg_content_performance_touch before update on public.content_performance for each row execute function public.touch_updated_at();
drop trigger if exists trg_content_learning_notes_touch on public.content_learning_notes;
create trigger trg_content_learning_notes_touch before update on public.content_learning_notes for each row execute function public.touch_updated_at();
drop trigger if exists trg_referral_links_touch on public.referral_links;
create trigger trg_referral_links_touch before update on public.referral_links for each row execute function public.touch_updated_at();
drop trigger if exists trg_referral_rewards_touch on public.referral_rewards;
create trigger trg_referral_rewards_touch before update on public.referral_rewards for each row execute function public.touch_updated_at();
drop trigger if exists trg_dm_leads_touch on public.dm_leads;
create trigger trg_dm_leads_touch before update on public.dm_leads for each row execute function public.touch_updated_at();
drop trigger if exists trg_dm_sequences_touch on public.dm_sequences;
create trigger trg_dm_sequences_touch before update on public.dm_sequences for each row execute function public.touch_updated_at();
drop trigger if exists trg_dm_messages_touch on public.dm_messages;
create trigger trg_dm_messages_touch before update on public.dm_messages for each row execute function public.touch_updated_at();
drop trigger if exists trg_dm_approvals_touch on public.dm_approvals;
create trigger trg_dm_approvals_touch before update on public.dm_approvals for each row execute function public.touch_updated_at();
drop trigger if exists trg_influencer_prospects_touch on public.influencer_prospects;
create trigger trg_influencer_prospects_touch before update on public.influencer_prospects for each row execute function public.touch_updated_at();
drop trigger if exists trg_influencer_outreach_messages_touch on public.influencer_outreach_messages;
create trigger trg_influencer_outreach_messages_touch before update on public.influencer_outreach_messages for each row execute function public.touch_updated_at();
drop trigger if exists trg_influencer_followups_touch on public.influencer_followups;
create trigger trg_influencer_followups_touch before update on public.influencer_followups for each row execute function public.touch_updated_at();
drop trigger if exists trg_influencer_deals_touch on public.influencer_deals;
create trigger trg_influencer_deals_touch before update on public.influencer_deals for each row execute function public.touch_updated_at();
drop trigger if exists trg_lead_scores_touch on public.lead_scores;
create trigger trg_lead_scores_touch before update on public.lead_scores for each row execute function public.touch_updated_at();
drop trigger if exists trg_onboarding_dropoffs_touch on public.onboarding_dropoffs;
create trigger trg_onboarding_dropoffs_touch before update on public.onboarding_dropoffs for each row execute function public.touch_updated_at();
drop trigger if exists trg_onboarding_recommendations_touch on public.onboarding_recommendations;
create trigger trg_onboarding_recommendations_touch before update on public.onboarding_recommendations for each row execute function public.touch_updated_at();

insert into public.marketing_campaigns (slug, category, title, description)
values
  ('credit-and-fundability', 'Credit and Fundability', 'Credit and Fundability', 'Free-first education on becoming fundable before applying.'),
  ('business-setup', 'Business Setup', 'Business Setup', 'Foundational setup content for business credibility and readiness.'),
  ('tier-1-funding', 'Tier 1 Funding', 'Tier 1 Funding', 'Educational content around Tier 1 0% business credit timing and stacking.'),
  ('grants-and-opportunities', 'Grants and Opportunities', 'Grants and Opportunities', 'Opportunities, grants, and overlooked programs.'),
  ('trading-education', 'Trading Education', 'Trading Education', 'Beginner-safe trading education and expectation setting.'),
  ('sba-tier-2-funding', 'SBA / Tier 2 Funding', 'SBA / Tier 2 Funding', 'Preparation content for SBA and later-stage funding.'),
  ('business-opportunities', 'Business Opportunities', 'Business Opportunities', 'Online and offline business opportunities and side-hustle transitions.')
on conflict (slug) do update set
  category = excluded.category,
  title = excluded.title,
  description = excluded.description,
  updated_at = now();

with seed(slug, campaign_slug, topic, theme) as (
values
  ('denied-business-credit-reasons','credit-and-fundability','Why most people get denied for business credit','why most people get denied for business credit'),
  ('credit-score-not-only-issue','credit-and-fundability','Your credit score is not the only issue lenders check','credit score is not the only issue'),
  ('fix-profile-before-applying','credit-and-fundability','Fix your profile before applying for funding','fix your profile before applying'),
  ('llc-alone-not-enough','business-setup','An LLC alone is not enough to make you fundable','LLC alone is not enough'),
  ('ein-duns-why-both-matter','business-setup','Why EIN and DUNS still matter in business setup education','EIN DUNS business setup'),
  ('business-address-mistakes','business-setup','Business address mistakes that hurt credibility','business address'),
  ('business-phone-red-flags','business-setup','Business phone red flags lenders notice fast','business phone'),
  ('business-email-credibility','business-setup','Why a business email matters more than people think','business email'),
  ('website-trust-signals','business-setup','Website trust signals that help your business profile','website trust'),
  ('naics-code-fundability','business-setup','How NAICS code education affects fundability','best fundable NAICS code education'),
  ('tier-1-zero-percent-basics','tier-1-funding','Tier 1 0% business credit basics for beginners','Tier 1 0% business credit'),
  ('funding-timing-mistakes','tier-1-funding','Funding timing mistakes that cost approvals','funding timing'),
  ('stacking-business-credit-cards','tier-1-funding','Business credit card stacking explained carefully','business credit card stacking'),
  ('after-funding-next-steps','tier-1-funding','What to do after funding so you do not waste momentum','what to do after funding'),
  ('becoming-fundable-first','credit-and-fundability','Why becoming fundable comes first','why becoming fundable comes first'),
  ('grants-nobody-applies-for','grants-and-opportunities','Grants nobody applies for because they do not know where to look','grants nobody applies for'),
  ('online-business-opportunities','business-opportunities','Online business opportunities worth learning before spending money','online business opportunities'),
  ('offline-business-opportunities','business-opportunities','Offline business opportunities hiding in plain sight','offline business opportunities'),
  ('trading-beginner-mistakes','trading-education','Trading education beginner mistakes to avoid early','trading education beginner mistakes'),
  ('sba-preparation-basics','sba-tier-2-funding','SBA preparation basics before you ever apply','SBA preparation'),
  ('business-credit-vs-personal-credit','credit-and-fundability','Business credit versus personal credit confusion','credit education'),
  ('lender-credibility-checklist','business-setup','The lender credibility checklist most founders skip','business profile checklist'),
  ('underwriting-beyond-score','credit-and-fundability','What underwriting sees beyond a score','underwriting education'),
  ('fundability-red-flags','credit-and-fundability','Common fundability red flags hiding in your setup','fundability red flags'),
  ('virtual-address-risk','business-setup','When a virtual address helps and when it hurts','business address'),
  ('google-voice-vs-real-line','business-setup','Why your business phone choice matters','business phone'),
  ('domain-email-first-impression','business-setup','Your domain email is a first impression signal','business email'),
  ('website-pages-you-need','business-setup','The core website pages a credible business should have','website trust'),
  ('naics-code-risky-industries','business-setup','NAICS codes that raise risk questions','best fundable NAICS code education'),
  ('tier-1-before-sba','tier-1-funding','Why many founders should learn Tier 1 before SBA','funding timing'),
  ('too-early-to-apply','credit-and-fundability','You are probably applying for funding too early','funding timing'),
  ('stacking-without-chaos','tier-1-funding','How to think about stacking without creating chaos','business credit card stacking'),
  ('protecting-funding-after-approval','tier-1-funding','How to protect funding after approval','what to do after funding'),
  ('grant-readiness-basics','grants-and-opportunities','Grant readiness basics most people skip','grants nobody applies for'),
  ('grant-application-cleanup','grants-and-opportunities','Clean up these details before applying for grants','grants readiness'),
  ('side-hustle-to-business','business-opportunities','How to move from side hustle to real business structure','business opportunities'),
  ('service-business-fundability','business-opportunities','Can a service business become fundable?','business opportunities'),
  ('beginner-trading-expectations','trading-education','What beginners get wrong about trading expectations','trading education'),
  ('risk-management-first','trading-education','Why risk management comes before strategy','trading education'),
  ('sba-paperwork-before-you-need-it','sba-tier-2-funding','SBA paperwork to organize before you need it','SBA preparation'),
  ('tier-2-needs-tier-1-discipline','sba-tier-2-funding','Tier 2 funding needs Tier 1 discipline first','SBA / Tier 2 Funding'),
  ('fundable-profile-audit','credit-and-fundability','Quick audit: is your profile fundable yet?','fix your profile before applying'),
  ('llc-myth-busting','business-setup','LLC myth busting for new founders','LLC alone is not enough'),
  ('duns-ein-business-bureaucracy','business-setup','The setup paperwork that still matters','EIN DUNS business setup'),
  ('business-address-proof','business-setup','How to prove your business address cleanly','business address'),
  ('phone-directory-listing','business-setup','Why directory consistency still matters for business phones','business phone'),
  ('professional-email-trust','business-setup','Professional email trust signals explained','business email'),
  ('website-not-optional','business-setup','Why a real website is not optional for credibility','website trust'),
  ('naics-code-match-model','business-setup','Your NAICS code should match your actual business model','best fundable NAICS code education'),
  ('zero-percent-not-free-money','tier-1-funding','0% business credit is not free money if your timing is wrong','Tier 1 0% business credit'),
  ('post-funding-discipline','tier-1-funding','Discipline after funding is what creates long-term leverage','what to do after funding'),
  ('becoming-fundable-vs-going-viral','credit-and-fundability','Becoming fundable matters more than chasing hype','why becoming fundable comes first')
)
insert into public.content_topics (campaign_id, slug, topic, theme)
select c.id, s.slug, s.topic, s.theme
from seed s
join public.marketing_campaigns c on c.slug = s.campaign_slug
on conflict (slug) do update set
  campaign_id = excluded.campaign_id,
  topic = excluded.topic,
  theme = excluded.theme,
  updated_at = now();
