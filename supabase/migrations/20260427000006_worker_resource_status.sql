-- ── Worker API resource status — rate-limit signalling bus ──────────────────
-- Workers write here when they hit a rate limit or API error.
-- Other workers read before making API calls to skip known-bad providers.
CREATE TABLE IF NOT EXISTS public.worker_resource_status (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  worker_name  text        NOT NULL,
  resource     text        NOT NULL,   -- 'groq', 'openrouter', 'cohere', 'nvidia', etc.
  status       text        NOT NULL DEFAULT 'ok',  -- 'ok', 'rate_limited', 'error'
  retry_after  timestamptz,            -- when it's safe to retry
  error_detail text,
  updated_at   timestamptz DEFAULT now(),
  UNIQUE (worker_name, resource)
);

ALTER TABLE public.worker_resource_status ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_full_access" ON public.worker_resource_status
  USING (true) WITH CHECK (true);

-- fast lookup: any worker checking a specific resource
CREATE INDEX IF NOT EXISTS wrs_resource_idx
  ON public.worker_resource_status (resource, status, retry_after);
