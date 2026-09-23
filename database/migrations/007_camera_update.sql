-- =============================================================================
-- CrowdEye AI - Migration 007: Camera Table Enhancement
-- Modifies existing cameras table without dropping it
-- =============================================================================

ALTER TABLE public.cameras ADD COLUMN IF NOT EXISTS location TEXT;
ALTER TABLE public.cameras ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'ACTIVE';
ALTER TABLE public.cameras ADD COLUMN IF NOT EXISTS zone_config JSONB;

-- Index for camera status filtering
CREATE INDEX IF NOT EXISTS idx_cameras_status ON public.cameras (status);
