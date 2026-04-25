import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

function LogoMark({ size = 32, dark = false }) {
  const c = dark ? '#fff' : '#111'
  const d = dark ? 'rgba(255,255,255,0.3)' : '#bbb'
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2"  y="2"  width="10" height="10" stroke={c} strokeWidth="1.5" fill="none" />
      <rect x="20" y="20" width="10" height="10" stroke={c} strokeWidth="1.5" fill="none" />
      <line x1="12" y1="7"  x2="20" y2="7"  stroke={c} strokeWidth="1" />
      <line x1="20" y1="7"  x2="20" y2="20" stroke={c} strokeWidth="1" />
      <line x1="12" y1="25" x2="20" y2="25" stroke={d} strokeWidth="1" strokeDasharray="2 2" />
      <line x1="12" y1="25" x2="12" y2="12" stroke={d} strokeWidth="1" strokeDasharray="2 2" />
    </svg>
  )
}

const FEATURES = [
  {
    icon: (
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <rect x="1" y="1" width="5" height="5" stroke="rgba(255,255,255,0.6)" strokeWidth="1"/>
        <rect x="8" y="8" width="5" height="5" stroke="rgba(255,255,255,0.6)" strokeWidth="1"/>
        <line x1="6" y1="3.5" x2="8" y2="3.5" stroke="rgba(255,255,255,0.6)" strokeWidth="1"/>
        <line x1="8" y1="3.5" x2="8" y2="8" stroke="rgba(255,255,255,0.6)" strokeWidth="1"/>
      </svg>
    ),
    text: 'Real-time SEC filings, congressional trades, and insider moves -- all in one feed',
  },
  {
    icon: (
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <circle cx="7" cy="7" r="5.5" stroke="rgba(255,255,255,0.6)" strokeWidth="1"/>
        <line x1="7" y1="1.5" x2="7" y2="12.5" stroke="rgba(255,255,255,0.6)" strokeWidth="1"/>
        <line x1="1.5" y1="7" x2="12.5" y2="7" stroke="rgba(255,255,255,0.6)" strokeWidth="1"/>
      </svg>
    ),
    text: 'Geopolitical signals mapped with conflict status, aircraft, maritime, and satellite data',
  },
  {
    icon: (
      <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
        <path d="M2 10 L5 6 L8 8 L12 3" stroke="rgba(255,255,255,0.6)" strokeWidth="1" fill="none"/>
        <circle cx="12" cy="3" r="1.5" fill="rgba(255,255,255,0.6)"/>
      </svg>
    ),
    text: 'AI-enriched events with plain-English summaries and investment signals',
  },
]

function ShieldIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
      <path d="M5 1L9 2.5V5C9 7 7 8.5 5 9C3 8.5 1 7 1 5V2.5L5 1Z"
        stroke="currentColor" strokeWidth="1" fill="none" strokeLinejoin="round"/>
      <path d="M3.5 5L4.5 6L6.5 4" stroke="currentColor" strokeWidth="1"
        strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

export default function Login() {
  const navigate = useNavigate()
  const mfaRef = useRef(null)

  useEffect(() => {
    if (localStorage.getItem('cl_token')) navigate('/', { replace: true })
  }, [navigate])

  const [authMode, setAuthMode] = useState('login')
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [mfaCode, setMfaCode]   = useState('')

  // mfaRequired: the backend returned mfa_required=true on the last attempt
  const [mfaRequired, setMfaRequired]   = useState(false)
  const [pendingToken, setPendingToken] = useState(null)

  const [error, setError]     = useState(null)
  const [loading, setLoading] = useState(false)

  // Auto-focus the MFA field when it slides in
  useEffect(() => {
    if (mfaRequired && mfaRef.current) mfaRef.current.focus()
  }, [mfaRequired])

  function switchMode(m) {
    setAuthMode(m)
    setError(null)
    setMfaRequired(false)
    setPendingToken(null)
    setMfaCode('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // If we already have a pending token (mfa_required was returned previously)
      // and the user has now filled in the code, verify directly.
      if (mfaRequired && pendingToken) {
        if (!mfaCode.trim()) {
          setError('Enter the 6-digit code from your authenticator app.')
          return
        }
        const data = await api.mfaChallenge(mfaCode.trim(), pendingToken)
        localStorage.setItem('cl_token', data.access_token)
        navigate('/')
        return
      }

      // First attempt: email + password (+ optional MFA code if user pre-filled it)
      const fn = authMode === 'login' ? api.login : api.register
      const data = await fn(email, password)

      if (data.mfa_required) {
        // Try to verify in one shot if user already typed a code
        if (mfaCode.trim()) {
          const mfaData = await api.mfaChallenge(mfaCode.trim(), data.access_token)
          localStorage.setItem('cl_token', mfaData.access_token)
          navigate('/')
          return
        }
        // No code yet -- reveal the MFA field and wait for re-submit
        setPendingToken(data.access_token)
        setMfaRequired(true)
      } else {
        localStorage.setItem('cl_token', data.access_token)
        navigate('/')
      }
    } catch (err) {
      setError(err.message)
      if (mfaRequired) setMfaCode('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex bg-white">

      {/* Left hero panel (md+) */}
      <div className="hidden md:flex flex-col w-1/2 bg-[#111] px-12 py-14">
        <div className="flex items-center gap-3 mb-auto">
          <LogoMark size={28} dark />
          <div>
            <p className="text-white text-sm font-bold tracking-tight uppercase">Capital Lens</p>
            <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-white/40 mt-0.5">
              Financial Intelligence
            </p>
          </div>
        </div>

        <div className="mt-auto mb-10">
          <h1 className="text-3xl font-bold text-white leading-tight tracking-tight">
            Institutional-grade<br />intelligence, self-hosted.
          </h1>
          <p className="mt-4 text-sm text-white/50 leading-relaxed max-w-xs">
            Fuse corporate filings, congressional trades, geopolitical events,
            aircraft tracking, and AI enrichment into a single real-time feed.
          </p>
        </div>

        <ul className="space-y-5 mb-14">
          {FEATURES.map((f, i) => (
            <li key={i} className="flex items-start gap-3">
              <span className="mt-0.5 flex-shrink-0">{f.icon}</span>
              <span className="text-[11px] text-white/60 leading-relaxed">{f.text}</span>
            </li>
          ))}
        </ul>

        <p className="text-[9px] font-medium uppercase tracking-[0.1em] text-white/20">
          Self-hosted -- All data stays on your machine
        </p>
      </div>

      {/* Right auth panel */}
      <div className="flex-1 flex flex-col items-center justify-center px-8 py-12">
        <div className="w-full max-w-sm">

          {/* Mobile-only wordmark */}
          <div className="md:hidden mb-10 flex flex-col items-center gap-3">
            <LogoMark size={36} />
            <div className="text-center">
              <h1 className="text-lg font-bold tracking-tight text-[#111] uppercase">Capital Lens</h1>
              <p className="text-[9px] font-medium uppercase tracking-[0.1em] text-[#999] mt-0.5">
                Financial Intelligence
              </p>
            </div>
          </div>

          {/* Mode tabs */}
          <div className="flex border border-[#e0e0e0] mb-6">
            {['login', 'register'].map(m => (
              <button
                key={m}
                onClick={() => switchMode(m)}
                className={`flex-1 py-2.5 text-[10px] font-medium uppercase tracking-[0.08em] transition-colors duration-200 ${
                  authMode === m ? 'bg-[#111] text-white' : 'bg-white text-[#999] hover:text-[#111]'
                }`}
              >
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          {/* Single unified form */}
          <form onSubmit={handleSubmit} noValidate>
            <div className="border border-[#e0e0e0]">

              {/* Email */}
              <div className="border-b border-[#e0e0e0]">
                <label className="block px-4 pt-3 pb-0 text-[9px] font-medium uppercase tracking-[0.1em] text-[#999]">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoFocus
                  autoComplete="email"
                  className="w-full px-4 pb-3 pt-1 text-sm text-[#111] bg-white focus:outline-none placeholder-[#ccc] font-light"
                  placeholder="you@example.com"
                />
              </div>

              {/* Password */}
              <div className={mfaRequired ? 'border-b border-[#e0e0e0]' : ''}>
                <label className="block px-4 pt-3 pb-0 text-[9px] font-medium uppercase tracking-[0.1em] text-[#999]">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  minLength={6}
                  autoComplete={authMode === 'login' ? 'current-password' : 'new-password'}
                  className="w-full px-4 pb-3 pt-1 text-sm text-[#111] bg-white focus:outline-none placeholder-[#ccc] font-light"
                  placeholder="••••••••"
                />
              </div>

              {/* Authenticator code -- slides in when mfaRequired */}
              <div
                className="overflow-hidden transition-all duration-300"
                style={{ maxHeight: mfaRequired ? '100px' : '0px' }}
              >
                <div className="bg-[#fafafa] border-t border-[#e8e8e8]">
                  <div className="flex items-center gap-1.5 px-4 pt-3 pb-0">
                    <span className="text-[#aaa]"><ShieldIcon /></span>
                    <label className="text-[9px] font-medium uppercase tracking-[0.1em] text-[#999]">
                      Authenticator Code
                    </label>
                  </div>
                  <input
                    ref={mfaRef}
                    type="text"
                    inputMode="numeric"
                    value={mfaCode}
                    onChange={e => setMfaCode(e.target.value.replace(/\s/g, ''))}
                    maxLength={8}
                    autoComplete="one-time-code"
                    className="w-full px-4 pb-3 pt-1 text-sm text-[#111] bg-[#fafafa] focus:outline-none placeholder-[#ccc] font-mono tracking-[0.2em]"
                    placeholder="000000"
                  />
                </div>
              </div>

            </div>

            {/* MFA hint (shown once field reveals) */}
            {mfaRequired && (
              <p className="mt-2 text-[10px] text-[#999] font-light">
                Enter the 6-digit code from your authenticator app, or an 8-character backup code.
              </p>
            )}

            {error && (
              <div className="mt-3 bg-[#111] px-4 py-3">
                <p className="text-xs text-white font-medium">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-4 py-3 bg-[#111] text-white text-[10px] font-medium uppercase tracking-[0.1em] hover:bg-[#000] disabled:opacity-40 transition-colors duration-200"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
                  {mfaRequired ? 'Verifying' : 'Please wait'}
                </span>
              ) : mfaRequired ? 'Verify & Sign In' : authMode === 'login' ? 'Sign In' : 'Create Account'}
            </button>

            {mfaRequired && (
              <button
                type="button"
                onClick={() => { setMfaRequired(false); setPendingToken(null); setMfaCode(''); setError(null) }}
                className="w-full mt-2 py-2 text-[10px] font-medium uppercase tracking-[0.08em] text-[#bbb] hover:text-[#555] transition-colors"
              >
                Use a different account
              </button>
            )}
          </form>

          <p className="mt-8 text-center text-[10px] font-light text-[#ccc]">
            Self-hosted -- All data stays on your machine
          </p>
        </div>
      </div>
    </div>
  )
}
