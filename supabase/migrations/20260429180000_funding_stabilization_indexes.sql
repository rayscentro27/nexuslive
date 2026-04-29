-- Stabilization: DB-level duplicate guards for billing and active recommendations.
-- Complements Python-level checks already in billing_events.py and service.py.

-- One invoice per application result.
create unique index if not exists success_fee_invoices_result_unique
  on public.success_fee_invoices (application_result_id);

-- One referral earning per application result.
create unique index if not exists referral_earnings_result_unique
  on public.referral_earnings (application_result_id);

-- Prevent duplicate active funding recommendations for the same product/user slot.
-- Only enforced while the row is in an active state; historical rows are unconstrained.
create unique index if not exists funding_recommendations_active_dedup
  on public.funding_recommendations (
    user_id,
    coalesce(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid),
    tier,
    recommendation_type,
    institution_name,
    product_name,
    product_type
  )
  where status in ('recommended', 'pending_review', 'active');
