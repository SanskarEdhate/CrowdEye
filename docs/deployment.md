# CrowdEye AI - Production Deployment Guide (Phase 7)

This guide documents the production deployment architecture, step-by-step provisioning instructions, environment configuration, and monitoring procedures for the **CrowdEye AI** platform.

---

## 1. Production Architecture Overview

CrowdEye AI employs a decoupled three-tier architecture ensuring heavy AI inference workloads never degrade the responsiveness of the security command center:

```
[ Frontend: Vercel ]
        |
        | HTTPS REST & WSS (/ws/realtime)
        v
[ Backend API Server: Render / Railway / AWS EC2 ]
        |
        +-----------------------------------+
        |                                   |
        v                                   v
[ Database: Supabase PostgreSQL ]    [ AI Worker: GPU / Cloud Instance ]
(Managed Cloud DB + RLS)             (YOLOv8 + DeepSORT + Kinematics)
```

---

## 2. Frontend Deployment (Vercel)

The frontend is a static web application built with Vanilla HTML5, modern CSS3 (Cyber-Telemetry Design System), and ES6 JavaScript.

### Steps:
1. **Connect GitHub Repository**:
   - Navigate to [Vercel Dashboard](https://vercel.com/new).
   - Import `https://github.com/SanskarEdhate/CrowdEye.git`.
2. **Configure Project Settings**:
   - **Framework Preset**: Other / None (Static Site).
   - **Root Directory**: `frontend`.
   - **Build Command**: None (leave empty).
   - **Output Directory**: `.` (or root of `frontend`).
3. **Environment Variables**:
   In Vercel Project Settings > Environment Variables:
   ```env
   VITE_API_URL=https://api.crowdeye.ai
   VITE_SUPABASE_URL=https://pltnbqykliyuueeobfly.supabase.co
   VITE_SUPABASE_ANON_KEY=<YOUR_SUPABASE_ANON_KEY>
   ```
4. **Deploy**:
   Click **Deploy**. Your control room dashboard will be accessible at:
   `https://crowdeye-ai.vercel.app` (or custom domain).

---

## 3. Backend Deployment (Render / Railway / AWS EC2)

The backend is an asynchronous Python 3.11+ service running on FastAPI and Uvicorn.

### Option A: Railway / Render (Containerized)
1. **Create Web Service**:
   - Connect repository `https://github.com/SanskarEdhate/CrowdEye.git`.
   - Select **Dockerfile** deployment.
   - Set Dockerfile path: `Dockerfile.backend`.
   - Set context: `.` (repository root).
2. **Environment Variables**:
   ```env
   HOST=0.0.0.0
   PORT=8000
   ENVIRONMENT=production
   DEBUG=False
   SUPABASE_URL=https://pltnbqykliyuueeobfly.supabase.co
   SUPABASE_SERVICE_KEY=<YOUR_SUPABASE_SERVICE_ROLE_KEY>
   SUPABASE_JWT_SECRET=<YOUR_SUPABASE_JWT_SECRET>
   FRONTEND_URL=https://crowdeye-ai.vercel.app
   CORS_ORIGINS=https://crowdeye-ai.vercel.app
   DEMO_MODE=false
   INTERNAL_SERVICE_KEY=<SECURE_INTERNAL_SHARED_SECRET>
   ```
3. **Health Check Endpoint**:
   - Health check path: `/health`
   - Expected response: `HTTP 200` with `{"api": "healthy", ...}`

### Option B: AWS EC2 / Docker Compose
On a Linux Ubuntu EC2 instance (`t3.medium` or higher):
```bash
git clone https://github.com/SanskarEdhate/CrowdEye.git
cd CrowdEye
cp backend/.env.example .env
# Edit .env with your production Supabase keys
docker compose -f docker-compose.yml up -d backend
```

---

## 4. Dedicated AI Worker Deployment (GPU Instance / Dedicated Worker)

The AI Worker runs YOLOv8 and DeepSORT tracking independently from the HTTP API server.

### Hardware Recommendations:
- **Optimal**: AWS `g4dn.xlarge` or NVIDIA RTX 3060/4090 with CUDA 12.x.
- **Minimum**: 4 vCPU, 8 GB RAM (CPU fallback mode).
- **Demo Mode**: Any environment with `DEMO_MODE=true`.

### Deployment Steps:
1. Build and launch with Docker:
   ```bash
   docker build -t crowdeye-ai-worker -f Dockerfile.ai .
   docker run -d \
     --name crowdeye-ai-worker \
     --restart unless-stopped \
     -e API_BASE_URL=https://api.crowdeye.ai \
     -e SUPABASE_URL=https://pltnbqykliyuueeobfly.supabase.co \
     -e SUPABASE_SERVICE_ROLE_KEY=<YOUR_KEY> \
     -e AI_DEVICE=cpu \
     -e DEMO_MODE=false \
     -v $(pwd)/logs:/app/logs \
     crowdeye-ai-worker
   ```
2. Or run via Docker Compose:
   ```bash
   docker compose up -d ai_worker
   ```

---

## 5. Database Setup (Supabase PostgreSQL)

CrowdEye AI uses a managed Supabase database. Apply migrations in sequential order via the Supabase SQL Editor:

1. `001_initial_schema.sql`: Core tables (`users`, `events`, `cameras`, `crowd_logs`, `alerts`) + baseline RLS.
2. `002_tracking_schema.sql`: Trajectories & movements.
3. `003_tracking_jobs.sql`: Asynchronous job registry.
4. `004_density_schema.sql`: Spatial zones & homography.
5. `005_risk_schema.sql`: Temporal risk evaluation logs.
6. `006_alerts.sql`: Alerts lifecycle, duplicate protection constraint, profiles table & RLS policies.
7. `007_camera_update.sql`: Modifies existing `cameras` table with `location`, `status DEFAULT 'ACTIVE'`, and `zone_config JSONB`.
8. `008_production_indexes.sql`: High-throughput performance indexes on `alerts`, `crowd_risk`, and `crowd_density`.

---

## 6. Rate Limiting & Security Hardening

- **SlowAPI Rate Limiter**:
  - Public endpoints: Max 100 requests/minute per client IP.
  - Authenticated endpoints: Max 300 requests/minute per user token.
  - Internal AI Worker: Exempt from rate limiting using `X-Service-Key`.
- **CORS**:
  - Restricts browser cross-origin requests strictly to `FRONTEND_URL` in production.
  - Wildcard `*` is prohibited.
- **Log Files**:
  All operational logs are stored in `logs/`:
  - `logs/api.log`: HTTP request methods, status codes, and latency in milliseconds.
  - `logs/ai_worker.log`: Inference FPS, frame counts, and batch telemetry inserts.
  - `logs/database.log`: Database connection and query exceptions.
  - `logs/auth.log`: Authentication attempts and RBAC 403 Forbidden events.
