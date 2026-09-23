-- =============================================================================
-- CrowdEye AI - Database Migration 002: Person Tracking Schema
-- Stores spatial-temporal movement vectors, headings, and speeds
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.person_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID REFERENCES public.cameras(id) ON DELETE SET NULL,
    person_id INTEGER NOT NULL,
    x_position FLOAT NOT NULL,
    y_position FLOAT NOT NULL,
    direction TEXT NOT NULL DEFAULT 'STATIONARY',
    speed FLOAT NOT NULL DEFAULT 0.0, -- In pixels/sec
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_person_tracking_camera_id ON public.person_tracking(camera_id);
CREATE INDEX IF NOT EXISTS idx_person_tracking_person_id ON public.person_tracking(person_id);
CREATE INDEX IF NOT EXISTS idx_person_tracking_timestamp ON public.person_tracking(timestamp DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.person_tracking ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Allow authenticated users to read person_tracking"
    ON public.person_tracking FOR SELECT TO authenticated USING (true);

CREATE POLICY "Allow service_role full access to person_tracking"
    ON public.person_tracking FOR ALL TO service_role USING (true) WITH CHECK (true);
