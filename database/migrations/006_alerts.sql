-- =============================================================================
-- CrowdEye AI - Migration 006: Alerts, Profiles & Role-Based Security
-- =============================================================================

-- 1. PROFILES TABLE FOR ROLE-BASED ACCESS CONTROL (ADMIN / OPERATOR)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'OPERATOR' CHECK (role IN ('ADMIN', 'OPERATOR')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow authenticated users to read profile"
    ON public.profiles FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

-- Helper function to verify admin role securely
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = auth.uid() AND role = 'ADMIN'
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. ALERTS TABLE
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID REFERENCES public.cameras(id) ON DELETE CASCADE,
    zone_id UUID,
    risk_score FLOAT,
    alert_level TEXT NOT NULL DEFAULT 'WARNING' CHECK (alert_level IN ('WARNING', 'CRITICAL')),
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'ACKNOWLEDGED', 'RESOLVED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Ensure backwards-compatibility if alerts table existed in 001
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS camera_id UUID REFERENCES public.cameras(id) ON DELETE CASCADE;
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS zone_id UUID;
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS risk_score FLOAT;
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS alert_level TEXT DEFAULT 'WARNING';
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS message TEXT;
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'ACTIVE';
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE public.alerts ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITH TIME ZONE;

-- 3. ALERT DUPLICATE PROTECTION
-- Partial unique index ensures only one ACTIVE alert per (camera_id, zone_id)
-- -----------------------------------------------------------------------------
CREATE UNIQUE INDEX IF NOT EXISTS idx_active_alert_unique
ON public.alerts (camera_id, COALESCE(zone_id, '00000000-0000-0000-0000-000000000000'::uuid))
WHERE status = 'ACTIVE';

CREATE INDEX IF NOT EXISTS idx_alerts_status ON public.alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON public.alerts(created_at DESC);

-- 4. ROW LEVEL SECURITY (RLS) POLICIES
-- -----------------------------------------------------------------------------
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users (both ADMIN & OPERATOR) to view alerts
CREATE POLICY "Allow authenticated read alerts"
    ON public.alerts FOR SELECT
    TO authenticated
    USING (true);

-- Allow service_role to manage all alerts
CREATE POLICY "Allow service_role full alerts access"
    ON public.alerts FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Allow OPERATOR and ADMIN to resolve alerts
CREATE POLICY "Allow authenticated users to resolve alerts"
    ON public.alerts FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (status IN ('ACKNOWLEDGED', 'RESOLVED'));

-- Camera RLS Policies:
-- ADMIN: Manage cameras (INSERT, UPDATE, DELETE)
-- OPERATOR: View cameras (SELECT)
CREATE POLICY "Allow authenticated view cameras"
    ON public.cameras FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Allow admin insert cameras"
    ON public.cameras FOR INSERT
    TO authenticated
    WITH CHECK (public.is_admin());

CREATE POLICY "Allow admin update cameras"
    ON public.cameras FOR UPDATE
    TO authenticated
    USING (public.is_admin())
    WITH CHECK (public.is_admin());

CREATE POLICY "Allow admin delete cameras"
    ON public.cameras FOR DELETE
    TO authenticated
    USING (public.is_admin());
