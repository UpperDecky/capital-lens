import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

/** Capital Lens wordmark — abstract routing mark matching NavBar */
function LogoMark({ size = 32 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2"  y="2"  width="10" height="10" stroke="#111" strokeWidth="1.5" fill="none" />
      <rect x="20" y="20" width="10" height="10" stroke="#111" strokeWidth="1.5" fill="none" />
      <line x1="12" y1="7"  x2="20" y2="7"  stroke="#111" strokeWidth="1" />
      <line x1="20" y1="7"  x2="20" y2="20" stroke="#111" strokeWidth="1" />
      <line x1="12" y1="25" x2="20" y2="25" stroke="#bbb" strokeWidth="1" strokeDasharray="2 2" />
      <line x1="12" y1="25" x2="12" y2="12" stroke="#bbb" strokeWidth="1" strokeDasharray="2 2" />
    </svg>
  )
}

export default function Login() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')  // 'login' | 'register'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const fn = mode === 'login' ? api.login : api.register
      const data = await fn(email, password)
      localStorage.setItem('cl_token', data.access_token)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="w-full max-w-sm">

        {/* Wordmark */}
        <div className="mb-10 flex flex-col items-center gap-3">
          <LogoMark size={40} />
          <div className="text-center">
            <h1 className="text-xl font-bold tracking-tight text-[#111]">Capital Lens</h1>
            <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-[#999] mt-0.5">
              Financial Intelligence
            </p>
          </div>
        </div>

        {/* Mode tabs */}
        <div className="flex border border-[#e0e0e0] mb-6">
          {['login', 'register'].map(m => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(null) }}
              className={`flex-1 py-2.5 text-[10px] font-medium uppercase tracking-[0.08em] transition-colors duration-200 ${
                mode === m
                  ? 'bg-[#111] text-white'
                  : 'bg-white text-[#999] hover:text-[#111]'
              }`}
            >
              {m === 'login' ? 'Sign In' : 'Register'}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-0 border border-[#e0e0e0]">
          <div className="border-b border-[#e0e0e0]">
            <label className="block px-4 pt-3 pb-0 text-[9px] font-medium uppercase tracking-[0.1em] text-[#999]">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              className="w-full px-4 pb-3 pt-1 text-sm text-[#111] bg-white focus:outline-none placeholder-[#ccc] font-light"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="block px-4 pt-3 pb-0 text-[9px] font-medium uppercase tracking-[0.1em] text-[#999]">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full px-4 pb-3 pt-1 text-sm text-[#111] bg-white focus:outline-none placeholder-[#ccc] font-light"
              placeholder="••••••••"
            />
          </div>
        </form>

        {/* Error */}
        {error && (
          <div className="mt-3 border border-[#111] px-4 py-3">
            <p className="text-xs font-light text-[#111]">{error}</p>
          </div>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full mt-4 py-3 bg-[#111] text-white text-[10px] font-medium uppercase tracking-[0.1em] hover:bg-[#000] disabled:opacity-40 transition-colors duration-200"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
              Please wait
            </span>
          ) : mode === 'login' ? 'Sign In' : 'Create Account'}
        </button>

        {/* Footer */}
        <p className="mt-6 text-center text-[10px] font-light text-[#ccc]">
          Self-hosted · All data stays on your machine
        </p>
      </div>
    </div>
  )
}
