-- Content Studio: widen the status CHECK constraint
-- Migration: 20260605000005_content_status_constraint.sql
-- Applied: 2026-06-06
-- Purpose: The original status CHECK from migration 000001 only allowed
--          (draft, approval_needed, approved, scheduled, published, archived).
--          The Content Studio UI introduces a richer lifecycle. This widens the
--          constraint to the UNION of old + new values so NO existing rows break.
--
-- Safety: drops and recreates one CHECK constraint only. Existing data with
--         legacy values ('approval_needed') remains valid in the new set.

DO $$
BEGIN
  -- Drop the old constraint if it exists (name from migration 000001)
  IF EXISTS (
    SELECT 1 FROM information_schema.constraint_column_usage
    WHERE constraint_name = 'nexus_os_content_items_status_check'
  ) THEN
    ALTER TABLE public.nexus_os_content_items
      DROP CONSTRAINT nexus_os_content_items_status_check;
  END IF;
END;
$$;

-- Recreate with the full lifecycle set (legacy + new values, union — nothing lost)
ALTER TABLE public.nexus_os_content_items
  ADD CONSTRAINT nexus_os_content_items_status_check
  CHECK (status IN (
    -- legacy values (migration 000001) — kept for backward compatibility
    'approval_needed',
    -- full Content Studio lifecycle
    'idea','draft','needs_review','approval_requested','approved',
    'scheduled','published','archived'
  ));
