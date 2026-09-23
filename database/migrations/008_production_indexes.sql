-- =============================================================================
-- CrowdEye AI - Migration 008: Production Performance & Query Indexes (TASK 10)
-- =============================================================================

-- 1. ALERTS TABLE OPTIMIZATION
CREATE INDEX IF NOT EXISTS idx_alerts_camera_id ON public.alerts(camera_id);
CREATE INDEX IF NOT EXISTS idx_alerts_zone_id ON public.alerts(zone_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON public.alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON public.alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_camera_status ON public.alerts(camera_id, status);

-- 2. CROWD RISK TIMESERIES OPTIMIZATION
CREATE INDEX IF NOT EXISTS idx_crowd_risk_camera_id ON public.crowd_risk(camera_id);
CREATE INDEX IF NOT EXISTS idx_crowd_risk_timestamp ON public.crowd_risk(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_crowd_risk_camera_timestamp ON public.crowd_risk(camera_id, timestamp DESC);

-- 3. CROWD DENSITY TIMESERIES OPTIMIZATION
CREATE INDEX IF NOT EXISTS idx_crowd_density_camera_id ON public.crowd_density(camera_id);
CREATE INDEX IF NOT EXISTS idx_crowd_density_timestamp ON public.crowd_density(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_crowd_density_camera_timestamp ON public.crowd_density(camera_id, timestamp DESC);
