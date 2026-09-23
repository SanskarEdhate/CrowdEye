# CrowdEye AI

> **AI-Powered Crowd Monitoring & Safety Platform for Large Public Events**

CrowdEye AI is an intelligent surveillance and incident prevention platform designed to protect lives at large-scale gatherings such as music festivals, religious pilgrimages, sports stadiums, and transport terminals. By transforming standard CCTV video feeds into real-time crowd density telemetry, movement vectors, and proactive stampede hazard warnings, CrowdEye AI equips security command centers with decisive operational foresight.

---

## Features Planned

- **Person Detection**: Real-time bounding-box identification of individuals in dense public crowds using YOLOv8.
- **Crowd Counting**: Accurate headcount estimation across camera perspectives and occluded zones.
- **Movement Tracking**: Continuous pedestrian trajectory vectorization with DeepSORT to detect flow anomalies and counter-flow turbulence.
- **Density Analysis**: High-density crowd mapping utilizing CSRNet (Congested Scene Recognition Network) to calculate people per square meter ($\text{ppl/m}^2$).
- **Risk Prediction**: Machine learning risk engine predicting stampede risks, dangerous bottlenecks, and surge pressures before escalation.
- **Real-Time Alerts**: Instant multi-channel notifications to security personnel when safe density thresholds are breached.
- **Security Command Dashboard**: Interactive geospatial map (Leaflet.js), dynamic telemetry charts (Chart.js), and incident dispatch workflows.

---

## Tech Stack

### Backend
- **Python 3.11+**
- **FastAPI**: Asynchronous high-performance REST framework
- **Uvicorn**: Lightning-fast ASGI production web server
- **Pydantic & Python-Dotenv**: Type-safe settings and environment variable validation

### Database & Security
- **Supabase PostgreSQL**: Relational time-series and event registry database
- **Supabase Row Level Security (RLS)**: Cryptographic isolation preventing unauthorized write access to telemetry and alerts
- **Supabase Authentication**: Role-based access control for security operators and commanders
- **Supabase Realtime**: WebSocket event streaming for instant alert distribution

### Frontend
- **HTML5 & Vanilla CSS3**: High-performance, responsive command-center design system
- **Vanilla ES6 JavaScript**: Buildless, lightweight client runtime
- **Fetch API**: Standardized backend API communication
- **Chart.js**: Real-time density timelines and risk distribution analytics
- **Leaflet.js**: Geospatial venue maps with zone-level telemetry and status overlays

### Future AI Modules (Phase 2 Roadmap)
- **YOLOv8**: Edge person detection
- **DeepSORT**: Multi-object tracking and trajectory analysis
- **CSRNet**: Dilated convolutional crowd density estimation
- **Predictive Risk Model**: Bottleneck and surge forecasting

---

## Project Structure

```
CrowdEye-AI/
├── backend/
│   ├── app/
│   │   ├── config/settings.py       # Configuration & environment variables
│   │   ├── database/supabase.py     # Reusable Supabase client & health checks
│   │   ├── routes/                  # API routers (health, crowd, alerts, events)
│   │   ├── services/                # Business logic services
│   │   ├── models/                  # Database models
│   │   ├── schemas/                 # Pydantic validation schemas
│   │   ├── utils/                   # Helper utilities
│   │   └── main.py                  # FastAPI instance & CORS middleware
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Environment variable template
│   └── .env                         # Local environment configuration
├── frontend/
│   ├── index.html                   # Platform landing portal
│   ├── pages/
│   │   ├── login.html               # Operator authentication
│   │   ├── dashboard.html           # Live command center dashboard
│   │   ├── monitoring.html          # Camera feed matrix
│   │   └── analytics.html           # Historical crowd telemetry & logs
│   ├── css/style.css                # Command center dark design system
│   ├── js/
│   │   ├── app.js                   # Dashboard Chart.js & Leaflet map controller
│   │   ├── api.js                   # Fetch API communication client
│   │   └── supabase.js              # Supabase JS auth & client helpers
│   ├── config.example.js            # Frontend public anon key template
│   └── assets/                      # Static assets & icons
├── database/
│   ├── migrations/
│   │   └── 001_initial_schema.sql   # Postgres schema, indexes & RLS policies
│   └── README.md                    # Database & RLS documentation
├── ai/
│   └── README.md                    # Future AI architecture roadmap (Phase 2)
├── datasets/                        # AI training datasets (gitignored)
├── videos/                          # Video feed samples (gitignored)
├── docs/
│   └── system_architecture.md       # Full end-to-end architectural blueprint
├── README.md
└── .gitignore
```

---

## Quickstart & Installation Steps

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Backend Setup

1. Open a terminal and navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. (Recommended) Create and activate a Python virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` to include your Supabase project credentials:
     ```env
     SUPABASE_URL=https://your-project.supabase.co
     SUPABASE_SERVICE_KEY=your-service-role-key-here
     ```

5. Launch the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. Verify backend health in your browser or curl:
   ```bash
   curl http://127.0.0.1:8000/
   ```
   Expected response:
   ```json
   {
     "project": "CrowdEye AI",
     "status": "Backend running"
   }
   ```
   Interactive Swagger API documentation is available at: `http://127.0.0.1:8000/docs`

---

### 3. Database Setup (Supabase)

1. Create a new project in [Supabase](https://supabase.com).
2. Open the **SQL Editor** in your Supabase project dashboard.
3. Open the file `database/migrations/001_initial_schema.sql` and run its contents in the SQL editor.
4. This script automatically:
   - Generates all five core tables (`users`, `events`, `cameras`, `crowd_logs`, `alerts`).
   - Enables Row Level Security (RLS).
   - Establishes policies ensuring only the backend service role can insert AI telemetry and safety alerts.

---

### 4. Frontend Setup

The frontend is built using standard Vanilla HTML5, CSS3, and ES6 JavaScript. No build step (Node.js/npm) is required!

1. Configure Supabase frontend keys:
   - Copy `frontend/config.example.js` to `frontend/config.js`:
     ```bash
     cp frontend/config.example.js frontend/config.js
     ```
   - Set your public `url` and `anonKey`.
2. Open `frontend/index.html` or `frontend/pages/dashboard.html` directly in any modern web browser, or serve it using Python's built-in HTTP server:
   ```bash
   # From the project root
   python -m http.server 3000 --directory frontend
   ```
3. Open `http://localhost:3000` in your browser.

---

## Phase 1 Status

✅ **Phase 1 Complete**: Full project architecture, FastAPI backend with CORS, Supabase database migration with RLS security policies, and an interactive dark command-center dashboard (Chart.js + Leaflet.js).
⏳ **Phase 2 (Upcoming)**: YOLOv8 person detection, DeepSORT trajectory tracking, CSRNet density estimation, and real-time inference worker pipeline.
