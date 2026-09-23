/**
 * CrowdEye AI - Frontend Supabase Configuration
 *
 * NOTE ON SECURITY:
 * The Supabase `anonKey` (Anonymous Key) is designed to be public and embedded
 * directly in client-side applications.
 *
 * Security is NOT enforced by hiding this key; it is strictly enforced in the
 * PostgreSQL database layer via Row Level Security (RLS) policies.
 *
 * - The backend uses `SUPABASE_SERVICE_KEY` in .env (NEVER expose to frontend).
 * - The frontend uses `anonKey` with Supabase Auth to query RLS-protected tables.
 */

const SUPABASE_CONFIG = {
  url: "https://your-project-id.supabase.co",
  anonKey: "your-anon-public-key"
};

// Export for module/script usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = SUPABASE_CONFIG;
}
