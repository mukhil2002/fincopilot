import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

export default function Dashboard() {
  const navigate = useNavigate()

  async function handleLogout() {
    await supabase.auth.signOut()
    navigate('/')
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ background: '#f4f6fb' }}
    >
      <div className="text-center">
        <div
          className="w-16 h-16 rounded-[14px] flex items-center justify-center mx-auto mb-4"
          style={{ background: 'linear-gradient(135deg, #4f8ef7, #2563eb)' }}
        >
          <svg width="28" height="28" viewBox="0 0 18 18" fill="none">
            <path d="M9 2L14 7H10V16H8V7H4L9 2Z" fill="white" />
          </svg>
        </div>

        <h1 className="text-[24px] font-semibold mb-2" style={{ color: '#0f1c3f' }}>
          You're in. 🎉
        </h1>
        <p className="text-[14px] mb-6" style={{ color: '#9ca3af' }}>
          Dashboard coming on Day 11. Auth is working perfectly.
        </p>

        <button
          onClick={handleLogout}
          className="text-[13px] font-medium px-4 py-2 rounded-lg transition-colors"
          style={{ color: '#dc2626', background: '#fef2f2', border: '1px solid #fecaca' }}
        >
          Sign out
        </button>
      </div>
    </div>
  )
}