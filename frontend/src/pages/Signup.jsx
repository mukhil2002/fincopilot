import { useState } from 'react'
import { Link } from 'react-router-dom'
import { supabase } from '../lib/supabase'

export default function Signup() {

  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [success, setSuccess]   = useState(false)

  async function handleSignup(e) {
    e.preventDefault()
    setError('')
    setLoading(true)

    const { error } = await supabase.auth.signUp({ email, password })

    if (error) {
      setError(error.message)
      setLoading(false)
      return
    }

    // Show success message — user needs to confirm email
    setSuccess(true)
    setLoading(false)
  }

  // Success state — show confirmation message
  if (success) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-4"
        style={{ background: '#f4f6fb' }}
      >
        <div className="w-full max-w-sm">
          <div
            className="bg-white rounded-[14px] p-8 text-center"
            style={{ border: '1px solid #e8ecf4' }}
          >
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4"
              style={{ background: '#ecfdf5' }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M5 13l4 4L19 7" stroke="#059669" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <h2 className="text-[18px] font-semibold mb-2" style={{ color: '#0f1c3f' }}>
              Check your email
            </h2>
            <p className="text-[13px] mb-6" style={{ color: '#9ca3af' }}>
              We sent a confirmation link to <strong>{email}</strong>. Click it to activate your account.
            </p>
            <Link
              to="/"
              className="block w-full py-2.5 rounded-lg text-[13px] font-semibold text-white text-center"
              style={{ background: '#2563eb' }}
            >
              Back to sign in
            </Link>
          </div>
        </div>
      </div>
    )
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
            Create account
          </h1>
          <p className="text-[13px] mb-6" style={{ color: '#9ca3af' }}>
            Start managing your finances with AI
          </p>

          <form onSubmit={handleSignup} className="space-y-4">

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
                minLength={6}
                className="w-full px-3 py-2 rounded-lg text-[13px] outline-none transition-all"
                style={{ border: '1px solid #e5e7eb', color: '#1f2937' }}
                onFocus={e => e.target.style.borderColor = '#2563eb'}
                onBlur={e => e.target.style.borderColor = '#e5e7eb'}
              />
              <p className="text-[11px] mt-1" style={{ color: '#9ca3af' }}>
                Minimum 6 characters
              </p>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg text-[13px] font-semibold text-white transition-opacity disabled:opacity-50"
              style={{ background: '#2563eb' }}
            >
              {loading ? 'Creating account...' : 'Create account'}
            </button>

          </form>
        </div>

        {/* Link to login */}
        <p className="text-center text-[12px] mt-4" style={{ color: '#9ca3af' }}>
          Already have an account?{' '}
          <Link to="/" className="font-medium" style={{ color: '#2563eb' }}>
            Sign in
          </Link>
        </p>

      </div>
    </div>
  )
}