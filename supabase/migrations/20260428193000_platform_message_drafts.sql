create extension if not exists pgcrypto;

create table if not exists public.message_logs (
  id uuid primary key default gen_random_uuid(),
  platform text not null,
  direction text not null,
  event_type text not null,
  external_ref text,
  content_topic text,
  intent_category text,
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'logged',
  created_at timestamptz not null default now()
);

create table if not exists public.social_comments (
  id uuid primary key default gen_random_uuid(),
  platform text not null,
  external_ref text,
  author_handle text,
  content_topic text,
  comment_text text not null,
  reply_draft text,
  status text not null default 'draft_pending_approval',
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

drop trigger if exists trg_social_comments_touch on public.social_comments;
create trigger trg_social_comments_touch
before update on public.social_comments
for each row execute function public.touch_updated_at();
