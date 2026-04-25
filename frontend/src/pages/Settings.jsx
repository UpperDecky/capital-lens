import { useState, useEffect, useRef } from 'react'
import { api } from '../lib/api'

// QR rendering via canvas using the 'qrcode' npm package
async function renderQr(canvas, uri) {
  const QRCode = (await import('qrcode')).default
  await QRCode.toCanvas(canvas, uri, {
    width: 200,
    margin: 2,
    color: { dark: '#111111', light: '#ffffff' },
  })
}

function SectionLabel({ children }) {
  return (
    <p className="text-[9px] font-medium uppercase tracking-[0.1em] text-[#999] mb-1">
      {children}
    </p>
  )
}

function StatusBadge({ enabled }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-1 text-[9px] font-bold uppercase tracking-[0.08em] border ${
        enabled
          ? 'border-[#111] text-[#111] bg-white'
          : 'border-[#ddd] text-[#999] bg-white'
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${enabled ? 'bg-[#111]' : 'bg-[#ccc]'}`}
      />
      {enabled ? 'Enabled' : 'Disabled'}
    </span>
  )
}

// ---- Sub-panels ------------------------------------------------------------

function EnablePanel({ onStart, loading }) {
  return (
    <div className="flex items-center justify-between py-4">
      <div>
        <p className="text-sm text-[#111] font-medium">Two-factor authentication is off.</p>
        <p className="text-xs text-[#999] mt-0.5 font-light">
          Use an authenticator app (Google Authenticator, Authy, etc.) to add a second factor.
        </p>
      </div>
      <button
        onClick={onStart}
        disabled={loading}
        className="ml-6 flex-shrink-0 px-4 py-2 text-[10px] font-medium uppercase tracking-[0.08em] bg-[#111] text-white hover:bg-[#000] disabled:opacity-40 transition-colors"
      >
        {loading ? 'Loading...' : 'Enable'}
      </button>
    </div>
  )
}

function QrPanel({ totp_uri, onNext }) {
  const canvasRef = useRef(null)
  const [qrError, setQrError] = useState(null)

  useEffect(() => {
    if (canvasRef.current && totp_uri) {
      renderQr(canvasRef.current, totp_uri).catch(err => {
        setQrError('Could not render QR code: ' + err.message)
      })
    }
  }, [totp_uri])

  return (
    <div className="py-4 space-y-5">
      <div>
        <p className="text-sm text-[#111] font-medium mb-1">Scan with your authenticator app</p>
        <p className="text-xs text-[#999] font-light">
          Open Google Authenticator, Authy, or any TOTP app and scan the QR code below.
        </p>
      </div>

      <div className="flex flex-col items-start gap-3">
        {qrError ? (
          <p className="text-xs text-[#c0392b]">{qrError}</p>
        ) : (
          <canvas
            ref={canvasRef}
            className="border border-[#e0e0e0]"
          />
        )}

        <details className="w-full">
          <summary className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#999] cursor-pointer hover:text-[#111] transition-colors">
            Can't scan? Enter manually
          </summary>
          <p className="mt-2 text-[11px] font-mono text-[#666] break-all bg-[#f9f9f9] p-3 border border-[#e0e0e0]">
            {totp_uri}
          </p>
        </details>
      </div>

      <button
        onClick={onNext}
        className="px-5 py-2.5 text-[10px] font-medium uppercase tracking-[0.08em] bg-[#111] text-white hover:bg-[#000] transition-colors"
      >
        I've scanned the code
      </button>
    </div>
  )
}

function VerifyPanel({ onVerified, onBack }) {
  const [code, setCode] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const data = await api.mfaVerify(code)
      onVerified(data.backup_codes)
    } catch (err) {
      setError(err.message)
      setCode('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="py-4 space-y-4">
      <div>
        <p className="text-sm text-[#111] font-medium mb-1">Confirm your authenticator</p>
        <p className="text-xs text-[#999] font-light">
          Enter the 6-digit code shown in your app to complete setup.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="border border-[#e0e0e0] max-w-xs">
        <label className="block px-4 pt-3 pb-0 text-[9px] font-medium uppercase tracking-[0.1em] text-[#999]">
          Code
        </label>
        <input
          type="text"
          inputMode="numeric"
          value={code}
          onChange={e => setCode(e.target.value.trim())}
          maxLength={6}
          required
          autoFocus
          autoComplete="one-time-code"
          className="w-full px-4 pb-3 pt-1 text-sm font-mono tracking-widest text-[#111] bg-white focus:outline-none placeholder-[#ccc]"
          placeholder="000000"
        />
      </form>

      {error && (
        <div className="border border-[#111] px-4 py-3 max-w-xs">
          <p className="text-xs font-light text-[#111]">{error}</p>
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={handleSubmit}
          disabled={loading || code.length !== 6}
          className="px-5 py-2.5 text-[10px] font-medium uppercase tracking-[0.08em] bg-[#111] text-white hover:bg-[#000] disabled:opacity-40 transition-colors"
        >
          {loading ? 'Verifying...' : 'Confirm'}
        </button>
        <button
          onClick={onBack}
          className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#999] hover:text-[#111] transition-colors"
        >
          Back
        </button>
      </div>
    </div>
  )
}

function BackupCodesPanel({ codes, onDone }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(codes.join('\n')).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="py-4 space-y-5">
      <div className="border border-[#111] px-4 py-3 bg-[#fafafa]">
        <p className="text-[10px] font-bold uppercase tracking-[0.08em] text-[#111] mb-0.5">
          Save these codes
        </p>
        <p className="text-xs text-[#666] font-light">
          Each code can be used once if you lose access to your authenticator. They will not be shown again.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-x-6 gap-y-2 max-w-xs font-mono text-sm text-[#111]">
        {codes.map((c, i) => (
          <span key={i} className="tracking-wider">{c}</span>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleCopy}
          className="px-4 py-2 text-[10px] font-medium uppercase tracking-[0.08em] border border-[#111] text-[#111] hover:bg-[#111] hover:text-white transition-colors"
        >
          {copied ? 'Copied' : 'Copy all'}
        </button>
        <button
          onClick={onDone}
          className="px-4 py-2 text-[10px] font-medium uppercase tracking-[0.08em] bg-[#111] text-white hover:bg-[#000] transition-colors"
        >
          I have saved my codes
        </button>
      </div>
    </div>
  )
}

function EnabledPanel({ onDisable }) {
  const [password, setPassword] = useState('')
  const [code, setCode]         = useState('')
  const [error, setError]       = useState(null)
  const [loading, setLoading]   = useState(false)
  const [open, setOpen]         = useState(false)

  async function handleDisable(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await api.mfaDisable(password, code)
      onDisable()
    } catch (err) {
      setError(err.message)
      setCode('')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="py-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-[#111] font-medium">Two-factor authentication is active.</p>
          <p className="text-xs text-[#999] mt-0.5 font-light">
            Your account is protected. You can disable 2FA below.
          </p>
        </div>
        <button
          onClick={() => { setOpen(v => !v); setError(null) }}
          className="ml-6 flex-shrink-0 px-4 py-2 text-[10px] font-medium uppercase tracking-[0.08em] border border-[#ccc] text-[#999] hover:border-[#111] hover:text-[#111] transition-colors"
        >
          Disable MFA
        </button>
      </div>

      {open && (
        <form onSubmit={handleDisable} className="space-y-3 max-w-xs">
          <div className="border border-[#e0e0e0]">
            <label className="block px-4 pt-3 pb-0 text-[9px] font-medium uppercase tracking-[0.1em] text-[#999]">
              Current Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full px-4 pb-3 pt-1 text-sm text-[#111] bg-white focus:outline-none placeholder-[#ccc] font-light"
              placeholder="••••••••"
            />
          </div>

          <div className="border border-[#e0e0e0]">
            <label className="block px-4 pt-3 pb-0 text-[9px] font-medium uppercase tracking-[0.1em] text-[#999]">
              Authenticator Code or Backup Code
            </label>
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={e => setCode(e.target.value.trim())}
              maxLength={8}
              required
              autoComplete="one-time-code"
              className="w-full px-4 pb-3 pt-1 text-sm font-mono tracking-widest text-[#111] bg-white focus:outline-none placeholder-[#ccc]"
              placeholder="000000"
            />
          </div>

          {error && (
            <div className="border border-[#111] px-4 py-3">
              <p className="text-xs font-light text-[#111]">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !password || code.length < 6}
            className="w-full py-2.5 text-[10px] font-medium uppercase tracking-[0.08em] bg-[#111] text-white hover:bg-[#000] disabled:opacity-40 transition-colors"
          >
            {loading ? 'Disabling...' : 'Confirm Disable'}
          </button>
        </form>
      )}
    </div>
  )
}

// ---- Main page -------------------------------------------------------------

export default function Settings() {
  // mfaState: 'loading' | 'disabled' | 'setup' | 'verify' | 'backup_codes' | 'enabled'
  const [mfaState, setMfaState]     = useState('loading')
  const [totpUri, setTotpUri]       = useState(null)
  const [backupCodes, setBackupCodes] = useState([])
  const [setupLoading, setSetupLoading] = useState(false)
  const [pageError, setPageError]   = useState(null)

  useEffect(() => {
    api.getMe()
      .then(me => setMfaState(me.mfa_enabled ? 'enabled' : 'disabled'))
      .catch(() => setPageError('Could not load account details.'))
  }, [])

  async function handleStartSetup() {
    setSetupLoading(true)
    setPageError(null)
    try {
      const data = await api.mfaSetup()
      setTotpUri(data.totp_uri)
      setMfaState('setup')
    } catch (err) {
      setPageError(err.message)
    } finally {
      setSetupLoading(false)
    }
  }

  function handleVerified(codes) {
    setBackupCodes(codes)
    setMfaState('backup_codes')
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-12 pt-20">

      <div className="mb-10">
        <h1 className="text-xl font-bold tracking-tight text-[#111]">Settings</h1>
        <p className="text-xs text-[#999] font-light mt-1">Account and security preferences</p>
      </div>

      {pageError && (
        <div className="mb-6 border border-[#111] px-4 py-3">
          <p className="text-xs text-[#111] font-light">{pageError}</p>
        </div>
      )}

      {/* MFA section */}
      <section>
        <div className="flex items-center justify-between mb-1">
          <SectionLabel>Two-Factor Authentication</SectionLabel>
          {mfaState !== 'loading' && (
            <StatusBadge enabled={mfaState === 'enabled' || mfaState === 'backup_codes'} />
          )}
        </div>
        <div className="border border-[#e0e0e0] px-5">
          {mfaState === 'loading' && (
            <div className="py-6 flex items-center gap-2 text-[10px] text-[#999] uppercase tracking-widest">
              <span className="w-3 h-3 border border-[#999] border-t-transparent rounded-full animate-spin" />
              Loading
            </div>
          )}

          {mfaState === 'disabled' && (
            <EnablePanel onStart={handleStartSetup} loading={setupLoading} />
          )}

          {mfaState === 'setup' && totpUri && (
            <QrPanel
              totp_uri={totpUri}
              onNext={() => setMfaState('verify')}
            />
          )}

          {mfaState === 'verify' && (
            <VerifyPanel
              onVerified={handleVerified}
              onBack={() => setMfaState('setup')}
            />
          )}

          {mfaState === 'backup_codes' && (
            <BackupCodesPanel
              codes={backupCodes}
              onDone={() => setMfaState('enabled')}
            />
          )}

          {mfaState === 'enabled' && (
            <EnabledPanel onDisable={() => setMfaState('disabled')} />
          )}
        </div>
      </section>
    </div>
  )
}
