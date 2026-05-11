-- research_execution_handoff.sql
-- Structured implementation handoff for approved research recommendations.

CREATE TABLE IF NOT EXISTS public.implementation_projects (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_id     uuid        NOT NULL,
  domain                text        NOT NULL CHECK (domain IN ('business', 'trading')),
  project_type          text        NOT NULL,
  title                 text        NOT NULL,
  summary               text,
  status                text        NOT NULL DEFAULT 'queued'
                                  CHECK (status IN ('queued', 'in_progress', 'blocked', 'completed', 'cancelled')),
  owner_hint            text,
  source_table          text,
  source_id             uuid,
  workflow_id           uuid,
  metadata              jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT implementation_projects_recommendation_unique UNIQUE (recommendation_id)
);

CREATE TABLE IF NOT EXISTS public.implementation_tasks (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            uuid        NOT NULL,
  task_order            integer     NOT NULL DEFAULT 0,
  task_type             text        NOT NULL DEFAULT 'implementation',
  title                 text        NOT NULL,
  details               text,
  assigned_team         text,
  status                text        NOT NULL DEFAULT 'pending'
                                  CHECK (status IN ('pending', 'ready', 'in_progress', 'blocked', 'completed', 'cancelled')),
  metadata              jsonb       NOT NULL DEFAULT '{}'::jsonb,
  created_at            timestamptz NOT NULL DEFAULT now(),
  updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_implementation_projects_domain
  ON public.implementation_projects (domain);

CREATE INDEX IF NOT EXISTS idx_implementation_projects_status
  ON public.implementation_projects (status);

CREATE INDEX IF NOT EXISTS idx_implementation_projects_created_at
  ON public.implementation_projects (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_implementation_tasks_project_id
  ON public.implementation_tasks (project_id);

CREATE INDEX IF NOT EXISTS idx_implementation_tasks_status
  ON public.implementation_tasks (status);

CREATE INDEX IF NOT EXISTS idx_implementation_tasks_assigned_team
  ON public.implementation_tasks (assigned_team);

COMMENT ON TABLE public.implementation_projects IS
  'Execution projects generated from approved research recommendations. Business recommendations become build/launch projects; trading recommendations become execution-validation projects.';

COMMENT ON TABLE public.implementation_tasks IS
  'Worker-readable task rows generated from recommendation execution plans and backend handoff lists.';
