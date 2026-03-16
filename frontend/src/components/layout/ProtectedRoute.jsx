import { useState, useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { supabase } from '../../lib/supabase'

export default function ProtectedRoute({ children }) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if user has an active session when component mounts
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    // Listen for auth changes — login, logout, token refresh
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session)
      }
    )

    // Cleanup — unsubscribe when component unmounts
    return () => subscription.unsubscribe()
  }, [])

  // Still checking — render nothing
  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: '#f4f6fb' }}
      >
        <div className="w-6 h-6 rounded-full border-2 border-t-transparent animate-spin"
             style={{ borderColor: '#2563eb', borderTopColor: 'transparent' }} />
      </div>
    )
  }

  // Not logged in — redirect to login
  if (!session) {
    return <Navigate to="/" replace />
  }

  // Logged in — render the protected page
  return children
}