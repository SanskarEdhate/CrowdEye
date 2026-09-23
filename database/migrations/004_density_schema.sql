-- =============================================================================
-- CrowdEye AI - Phase 4: Crowd Density & Zone Heatmap Schema
-- Migration 004: Camera Zones & Crowd Density Telemetry
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. CAMERA_ZONES TABLE
-- Stores spatial partitioning geometries and nominal capacities per camera zone
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.camera_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID NULL REFERENCES public.cameras(id) ON DELETE SET NULL,
    zone_name TEXT NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 100,
    coordinates JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_camera_zones_camera_id ON public.camera_zones (camera_id);
CREATE INDEX IF NOT EXISTS idx_camera_zones_name ON public.camera_zones (zone_name);

ALTER TABLE public.camera_zones ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow authenticated read camera_zones"
    ON public.camera_zones
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow service role full access camera_zones"
    ON public.camera_zones
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


-- -----------------------------------------------------------------------------
-- 2. CROWD_DENSITY TABLE
-- Stores 5-second interval density telemetry per zone (people, score, level)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.crowd_density (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID NULL REFERENCES public.cameras(id) ON DELETE SET NULL,
    zone_id UUID NULL REFERENCES public.camera_zones(id) ON DELETE SET NULL,
    zone_name TEXT NOT NULL,
    people_count INTEGER NOT NULL DEFAULT 0,
    density_score FLOAT NOT NULL DEFAULT 0.0,
    density_level TEXT NOT NULL, -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    timestamp TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

CREATE INDEX IF NOT EXISTS idx_crowd_density_timestamp ON public.crowd_density (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_crowd_density_zone_name ON public.crowd_density (zone_name);
CREATE INDEX IF NOT EXISTS idx_crowd_density_camera_id ON public.crowd_density (camera_id);

ALTER TABLE public.crowd_density ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow authenticated read crowd_density"
    ON public.crowd_density
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow service role full access crowd_density"
    ON public.crowd_density
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


-- -----------------------------------------------------------------------------
-- 3. DENSITY_JOBS TABLE
-- Tracks asynchronous density processing tasks and progress
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.density_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_name TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    completed_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_density_jobs_status ON public.density_jobs (status);

ALTER TABLE public.density_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow authenticated read density_jobs"
    ON public.density_jobs
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow service role full access density_jobs"
    ON public.density_jobs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
