import axios from 'axios'
import { supabase } from './supabase'

// Create an Axios instance
// All API calls go through this instead of raw axios
const api = axios.create({
  baseURL: '/api',
})

// ── Request interceptor ───────────────────────────────────────────
// Runs BEFORE every request goes out.
// Automatically attaches the JWT token to the Authorization header.
// This is why no component ever has to think about auth headers —
// it's handled once here, centrally.

api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }

  return config
})

// ── Response interceptor ──────────────────────────────────────────
// Runs AFTER every response comes back.
// Watches for 401 Unauthorized — which means the JWT token has
// expired (tokens last 1 hour, set by Supabase).
//
// When a 401 is detected:
// 1. Sign the user out via Supabase (clears the session)
// 2. Redirect to the login page
//
// Without this, every panel would independently show a broken/error
// state when the token expires, with no explanation to the user.
// With this, the app handles expiry gracefully and automatically.
//
// The two-argument pattern:
// - First argument:  called on SUCCESS (2xx responses) → pass through
// - Second argument: called on FAILURE (4xx/5xx) → inspect and handle

api.interceptors.response.use(
  // Success handler — do nothing, just return the response
  (response) => response,

  // Error handler — runs on any non-2xx response
  async (error) => {
    const status = error.response?.status

    if (status === 401) {
      // JWT expired or invalid.
      // Sign out clears the Supabase session in memory.
      // This triggers ProtectedRoute's onAuthStateChange listener,
      // which sees session = null and redirects to login.
      await supabase.auth.signOut()

      // Belt-and-suspenders redirect in case the listener is slow.
      // window.location.href does a hard redirect — clears all state.
      // We use this instead of React Router's navigate() because
      // this interceptor lives outside the React component tree and
      // doesn't have access to the router.
      window.location.href = '/'
    }

    // For all other errors (500, 403, 404, network errors etc),
    // pass the error through to the component's catch block.
    // Each component handles non-auth errors in its own way.
    return Promise.reject(error)
  }
)

export default api