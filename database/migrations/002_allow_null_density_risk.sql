-- =============================================================================
-- CrowdEye AI - Database Migration 002
-- Allow NULL values for density and risk_score in crowd_logs
-- Needed for Phase 2 raw person detection before density & risk models are added
-- =============================================================================

ALTER TABLE public.crowd_logs ALTER COLUMN density DROP NOT NULL;
ALTER TABLE public.crowd_logs ALTER COLUMN risk_score DROP NOT NULL;
