-- =============================================================================
-- CrowdEye AI - Database Migration 003: Tracking Jobs Schema
-- Persists tracking job lifecycle, state, progress, and unique person counts
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.tracking_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued', -- 'queued', 'processing', 'completed', 'failed'
    progress INTEGER NOT NULL DEFAULT 0,  -- 0 to 100
    total_people INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_tracking_jobs_status ON public.tracking_jobs(status);
CREATE INDEX IF NOT EXISTS idx_tracking_jobs_created_at ON public.tracking_jobs(created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.tracking_jobs ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Allow authenticated users to read tracking_jobs"
    ON public.tracking_jobs FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow service_role full access to tracking_jobs"
    ON public.tracking_jobs FOR ALL TO service_role USING (true) WITH CHECK (true);
