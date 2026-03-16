import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { supabase } from '../lib/supabase'

export default function Login() {
  const navigate = useNavigate()

  // State — four pieces of data this component tracks
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  async function handleLogin(e) {
    e.preventDefault()  // stop the browser from reloading the page
    setError('')         // clear any previous error
    setLoading(true)

    const { error } = await supabase.auth.signInWithPassword({ email, password })

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    // Login successful — go to dashboard
    navigate('/dashboard')
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: '#f4f6fb' }}
    >
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <div
            className="w-9 h-9 rounded-[10px] flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #4f8ef7, #2563eb)' }}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M9 2L14 7H10V16H8V7H4L9 2Z" fill="white" />
            </svg>
          </div>
          <div>
            <div className="text-[16px] font-semibold" style={{ color: '#0f1c3f' }}>
              FinCopilot
            </div>
            <div className="text-[10px] font-semibold tracking-[0.04em]" style={{ color: '#2563eb' }}>
              AI · BOOKKEEPING
            </div>
          </div>
        </div>

        {/* Card */}
        <div
          className="bg-white rounded-[14px] p-8"
          style={{ border: '1px solid #e8ecf4' }}
        >
          <h1 className="text-[20px] font-semibold mb-1" style={{ color: '#0f1c3f' }}>
            Welcome back
          </h1>
          <p className="text-[13px] mb-6" style={{ color: '#9ca3af' }}>
            Sign in to your FinCopilot account
          </p>

          <form onSubmit={handleLogin} className="space-y-4">

            {/* Error message */}
            {error && (
              <div
                className="text-[12px] px-3 py-2.5 rounded-lg"
                style={{ background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca' }}
              >
                {error}
              </div>
            )}

            {/* Email */}
            <div>
              <label className="block text-[12px] font-medium mb-1.5" style={{ color: '#374151' }}>
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                className="w-full px-3 py-2 rounded-lg text-[13px] outline-none transition-all"
                style={{ border: '1px solid #e5e7eb', color: '#1f2937' }}
                onFocus={e => e.target.style.borderColor = '#2563eb'}
                onBlur={e => e.target.style.borderColor = '#e5e7eb'}
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-[12px] font-medium mb-1.5" style={{ color: '#374151' }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full px-3 py-2 rounded-lg text-[13px] outline-none transition-all"
                style={{ border: '1px solid #e5e7eb', color: '#1f2937' }}
                onFocus={e => e.target.style.borderColor = '#2563eb'}
                onBlur={e => e.target.style.borderColor = '#e5e7eb'}
              />
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg text-[13px] font-semibold text-white transition-opacity disabled:opacity-50"
              style={{ background: '#2563eb' }}
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>

          </form>
        </div>

        {/* Link to signup */}
        <p className="text-center text-[12px] mt-4" style={{ color: '#9ca3af' }}>
          Don't have an account?{' '}
          <Link to="/signup" className="font-medium" style={{ color: '#2563eb' }}>
            Sign up
          </Link>
        </p>

      </div>
    </div>
  )
}                       