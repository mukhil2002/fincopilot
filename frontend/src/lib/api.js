import axios from 'axios'
import { supabase } from './supabase'

// Create an Axios instance
// All API calls go through this instead of raw axios
const api = axios.create({
  baseURL: '/api',
})

// Request interceptor — runs before every single API call
// Automatically attaches the JWT token to the Authorization header
api.interceptors.request.use(async (config) => {
  const { data: { session } } = await supabase.auth.getSession()

  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`
  }

  return config
})

export default api