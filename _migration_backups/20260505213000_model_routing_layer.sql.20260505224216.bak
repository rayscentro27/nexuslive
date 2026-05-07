-- Migration: Hermes Unified Model Routing Layer
-- Description: Creates tables for tiered model routing, provider health tracking, and task-based routing rules.

-- 1. Create model_providers table
CREATE TABLE IF NOT EXISTS public.model_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE, -- e.g. 'netcup_ollama', 'gemini_flash'
    base_url TEXT NOT NULL,
    api_key_env_var TEXT, -- Name of the environment variable, e.g. 'GEMINI_API_KEY'
    model_name TEXT NOT NULL,
    format TEXT NOT NULL DEFAULT 'openai', -- openai, ollama_generate, anthropic
    
    -- Health & Selection
    is_healthy BOOLEAN NOT NULL DEFAULT true,
    last_failure_at TIMESTAMPTZ,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 10, -- Lower is higher priority
    cost_tier TEXT NOT NULL DEFAULT 'medium', -- low, medium, high
    
    -- Metadata & Audit
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast provider lookups
CREATE INDEX idx_model_providers_name ON public.model_providers(name);
CREATE INDEX idx_model_providers_health ON public.model_providers(is_healthy) WHERE is_healthy = false;

-- 2. Create model_routing_rules table
CREATE TABLE IF NOT EXISTS public.model_routing_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type TEXT NOT NULL UNIQUE, -- cheap, planning, coding, reason, critical
    provider_chain UUID[] NOT NULL, -- Ordered array of provider IDs
    fallback_provider_id UUID REFERENCES public.model_providers(id),
    
    -- Metadata & Audit
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for task type routing
CREATE INDEX idx_model_routing_rules_task_type ON public.model_routing_rules(task_type);

-- 3. Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trg_model_providers_updated_at
    BEFORE UPDATE ON public.model_providers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_model_routing_rules_updated_at
    BEFORE UPDATE ON public.model_routing_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. Initial Seed Data (Example)
-- Note: This is a placeholder. Actual IDs should be used for provider_chain.

/*
INSERT INTO public.model_providers (name, base_url, api_key_env_var, model_name, format, cost_tier, priority)
VALUES 
('netcup_ollama', 'http://localhost:11555/api/generate', NULL, 'llama3.2:3b', 'ollama_generate', 'low', 100),
('gemini_flash', 'https://generativelanguage.googleapis.com/v1beta/openai', 'GEMINI_API_KEY', 'gemini-1.5-flash', 'openai', 'low', 10);
*/

-- 5. RLS (Row Level Security) - Internal access only
ALTER TABLE public.model_providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_routing_rules ENABLE ROW LEVEL SECURITY;

-- model_providers: service_role only
CREATE POLICY "model_providers_select_service_role"
ON public.model_providers
FOR SELECT TO service_role
USING (true);

CREATE POLICY "model_providers_insert_service_role"
ON public.model_providers
FOR INSERT TO service_role
WITH CHECK (true);

CREATE POLICY "model_providers_update_service_role"
ON public.model_providers
FOR UPDATE TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "model_providers_delete_service_role"
ON public.model_providers
FOR DELETE TO service_role
USING (true);

-- model_routing_rules: service_role only
CREATE POLICY "model_routing_rules_select_service_role"
ON public.model_routing_rules
FOR SELECT TO service_role
USING (true);

CREATE POLICY "model_routing_rules_insert_service_role"
ON public.model_routing_rules
FOR INSERT TO service_role
WITH CHECK (true);

CREATE POLICY "model_routing_rules_update_service_role"
ON public.model_routing_rules
FOR UPDATE TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "model_routing_rules_delete_service_role"
ON public.model_routing_rules
FOR DELETE TO service_role
USING (true);
