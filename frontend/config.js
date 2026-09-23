/**
 * CrowdEye AI - Frontend Supabase Configuration
 */
const SUPABASE_CONFIG = {
  url: "",
  anonKey: "" // Paste your public anon key here if using client-side auth
};

if (typeof module !== "undefined" && module.exports) {
  module.exports = SUPABASE_CONFIG;
}
