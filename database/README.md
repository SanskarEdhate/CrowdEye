# CrowdEye AI - Database Architecture & Security Policies

This directory contains the database migration scripts and security documentation for the CrowdEye AI PostgreSQL database hosted on **Supabase**.

---

## 1. Schema Overview

The database acts as the single source of truth for event venues, camera configurations, AI-derived crowd telemetry, and security alarms.

| Table | Purpose | Primary Key | Key Foreign Keys |
| :--- | :--- | :--- | :--- |
| `users` | Security personnel & platform operators | UUID | - |
| `events` | Public gatherings, festivals, stadiums | UUID | - |
| `cameras` | Video capture feeds mapped to event zones | UUID | `event_id` -> `events(id)` |
| `crowd_logs` | Time-series AI inferences (people count, density, risk) | UUID | `camera_id` -> `cameras(id)` |
| `alerts` | Real-time threshold violations & stampede risk warnings | UUID | `event_id` -> `events(id)` |

---

## 2. Row Level Security (RLS) Policy Summary

Row Level Security is explicitly enabled on all tables (`users`, `events`, `cameras`, `crowd_logs`, `alerts`).

### Security Principles:
1. **Public/Anon Access Disabled**: Anonymous public visitors have zero insert, update, or read access unless authenticated.
2. **Authenticated Read Access**: Validated security personnel (logged in via Supabase Auth) can inspect:
   - Events list and venue metadata
   - Camera feeds and zone designations
   - Crowd logs and density graphs
   - Active and resolved safety alerts
3. **Restricted AI Ingestion (Service Role Only)**:
   - **`crowd_logs`**: Only the backend AI perception worker holding the `SUPABASE_SERVICE_KEY` can insert crowd logs. Clients cannot spoof crowd statistics.
   - **`alerts`**: Only the backend risk engine can trigger official security alerts. Clients can never create fake alerts.

### Policy Details

| Table | Target Role | Permitted Actions | Policy Rule |
| :--- | :--- | :--- | :--- |
| `users` | `authenticated` | `SELECT` | Read user profile information |
| `events` | `authenticated` | `SELECT` | View active and upcoming public events |
| `events` | `service_role` | `ALL` | Full administrative control |
| `cameras` | `authenticated` | `SELECT` | View camera stream links and zone mappings |
| `cameras` | `service_role` | `ALL` | Full camera registry management |
| `crowd_logs` | `authenticated` | `SELECT` | Read crowd density history and charts |
| `crowd_logs` | `service_role` | `INSERT`, `ALL` | AI ingestion worker writes telemetry |
| `alerts` | `authenticated` | `SELECT` | Security team views active emergency alerts |
| `alerts` | `service_role` | `INSERT`, `UPDATE`, `ALL` | Backend risk engine publishes/resolves alerts |

---

## 3. How to Apply Migrations to Supabase

1. Open your **Supabase Dashboard** (`https://supabase.com/dashboard/project/<your-project-id>`).
2. Navigate to the **SQL Editor** tab in the left navigation.
3. Click **New query**.
4. Copy and paste the contents of:
   ```
   database/migrations/001_initial_schema.sql
   ```
5. Click **Run** to execute the script and apply the schema and RLS policies.
6. Verify under **Table Editor** that all 5 tables and their RLS badges are active.
