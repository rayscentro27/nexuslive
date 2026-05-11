alter table public.content_variants
  add column if not exists campaign_id uuid references public.marketing_campaigns(id) on delete set null,
  add column if not exists hashtags jsonb,
  add column if not exists cta text,
  add column if not exists created_by text default 'content_variant_generator';

create index if not exists content_variants_topic_platform_idx
  on public.content_variants (topic_id, platform);
