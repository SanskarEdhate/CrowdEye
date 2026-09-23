/**
 * CrowdEye AI - Supabase Client Initialization
 * Connects browser frontend to Supabase PostgreSQL & Auth using anon key.
 */

let supabaseClient = null;

function initSupabase() {
  if (typeof window.supabase === "undefined") {
    console.warn(
      "[CrowdEye] Supabase JS library not found. Please include the Supabase CDN script."
    );
    return null;
  }

  // Check if configuration exists
  if (
    typeof SUPABASE_CONFIG === "undefined" ||
    !SUPABASE_CONFIG.url ||
    SUPABASE_CONFIG.url.includes("your-project-id")
  ) {
    console.info(
      "[CrowdEye] Supabase client operating in standby/mock mode. Set SUPABASE_CONFIG in frontend/config.js to enable live connection."
    );
    return null;
  }

  try {
    supabaseClient = window.supabase.createClient(
      SUPABASE_CONFIG.url,
      SUPABASE_CONFIG.anonKey
    );
    console.log("[CrowdEye] Supabase client initialized successfully.");
    return supabaseClient;
  } catch (error) {
    console.error("[CrowdEye] Error initializing Supabase client:", error);
    return null;
  }
}

// Authentication Helpers
async function loginUser(email, password) {
  const client = supabaseClient || initSupabase();
  if (!client) {
    // Mock successful login for offline / prototype testing
    return {
      user: { email, name: email.split("@")[0], role: "Security Commander" },
      session: { access_token: "mock-session-token" },
      error: null
    };
  }
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  return { user: data?.user, session: data?.session, error };
}

async function logoutUser() {
  const client = supabaseClient || initSupabase();
  if (client) {
    await client.auth.signOut();
  }
  sessionStorage.removeItem("crowdeye_user");
  window.location.href = "login.html";
}

async function getCurrentUser() {
  const client = supabaseClient || initSupabase();
  if (!client) {
    const saved = sessionStorage.getItem("crowdeye_user");
    return saved ? JSON.parse(saved) : null;
  }
  const { data: { user } } = await client.auth.getUser();
  return user;
}

// Auto-initialize when script loads
if (typeof window !== "undefined") {
  window.addEventListener("DOMContentLoaded", () => {
    initSupabase();
  });
}
