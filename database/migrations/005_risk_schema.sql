-- =============================================================================
-- CrowdEye AI - Phase 5: Crowd Risk Prediction & Early Warning Schema
-- Migration 005: Crowd Risk Evaluations & Diagnostic Reasoning
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. CROWD_RISK TABLE
-- Stores evaluated crowd safety risk scores, levels, diagnostic reasons, and feature vectors
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.crowd_risk (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID NULL REFERENCES public.cameras(id) ON DELETE SET NULL,
    zone_id UUID NULL REFERENCES public.camera_zones(id) ON DELETE SET NULL,
    zone_name TEXT NOT NULL,
    risk_score FLOAT NOT NULL,
    risk_level TEXT NOT NULL, -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    risk_reason JSONB NOT NULL, -- JSON array of human-readable diagnostic reasons
    density_value FLOAT NOT NULL DEFAULT 0.0,
    speed_value FLOAT NOT NULL DEFAULT 0.0,
    chaos_value FLOAT NOT NULL DEFAULT 0.0,
    growth_value FLOAT NOT NULL DEFAULT 0.0,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_crowd_risk_timestamp ON public.crowd_risk (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_crowd_risk_level ON public.crowd_risk (risk_level);
CREATE INDEX IF NOT EXISTS idx_crowd_risk_zone_name ON public.crowd_risk (zone_name);
CREATE INDEX IF NOT EXISTS idx_crowd_risk_camera_id ON public.crowd_risk (camera_id);

ALTER TABLE public.crowd_risk ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow authenticated read crowd_risk"
    ON public.crowd_risk
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow service role full access crowd_risk"
    ON public.crowd_risk
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


-- -----------------------------------------------------------------------------
-- 2. RISK_JOBS TABLE
-- Tracks asynchronous risk prediction analysis tasks and progress
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.risk_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    completed_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_risk_jobs_status ON public.risk_jobs (status);

ALTER TABLE public.risk_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow authenticated read risk_jobs"
    ON public.risk_jobs
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow service role full access risk_jobs"
    ON public.risk_jobs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
