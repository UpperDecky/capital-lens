/**
 * DisclaimerModal -- shown on first visit; requires explicit checkbox acceptance.
 *
 * Legal basis: Under the Investment Advisers Act of 1940 (15 U.S.C. ss 80b),
 * a person who provides investment advice for compensation must register with
 * the SEC. Capital Lens does not charge for advice and provides only general
 * informational content, qualifying for the "publisher exemption" under
 * Section 202(a)(11)(D). This disclaimer makes that distinction explicit.
 *
 * Acceptance is stored in localStorage (gate) and synced to the backend DB
 * (audit trail) when the user is authenticated.
 */
import { useState, useEffect } from 'react'
import { api } from '../lib/api'

const STORAGE_KEY = 'cl_disclaimer_v1'

export default function DisclaimerModal() {
  const [visible, setVisible]   = useState(false)
  const [checked, setChecked]   = useState(false)
  const [syncing, setSyncing]   = useState(false)

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) setVisible(true)
  }, [])

  async function accept() {
    if (!checked) return
    setSyncing(true)
    localStorage.setItem(STORAGE_KEY, new Date().toISOString())
    setVisible(false)
    if (localStorage.getItem('cl_token')) {
      try { await api.acceptDisclaimer() } catch (_) { /* non-blocking */ }
    }
    setSyncing(false)
  }

  if (!visible) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm px-4">
      <div className="bg-white border border-[#111] max-w-lg w-full shadow-2xl flex flex-col max-h-[90vh]">

        {/* Header */}
        <div className="px-6 py-5 border-b border-[#e0e0e0] flex-shrink-0">
          <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-[#999] mb-1">
            Before you continue
          </p>
          <h2 className="text-lg font-bold tracking-tight text-[#111]">
            Informational Use Only
          </h2>
        </div>

        {/* Scrollable body */}
        <div className="px-6 py-5 space-y-4 text-xs text-[#444] leading-relaxed font-light overflow-y-auto flex-1">
          <p>
            <strong className="font-semibold text-[#111]">Capital Lens is not a financial adviser.</strong>{' '}
            Nothing on this platform -- including AI-generated summaries, investment signals,
            market impact assessments, sector tags, or personal takeaways -- constitutes
            investment advice, financial advice, trading advice, legal advice, or any other
            type of professional advice.
          </p>

          <p>
            Capital Lens aggregates publicly available financial data and applies AI commentary
            for{' '}
            <strong className="font-semibold text-[#111]">
              general informational and educational purposes only.
            </strong>{' '}
            It is not registered as an investment adviser with the U.S. Securities and Exchange
            Commission (SEC), FINRA, or any other regulatory authority.
          </p>

          <div className="border border-[#f0f0f0] bg-[#fafafa] p-3 space-y-2">
            <p className="text-[9px] font-semibold uppercase tracking-[0.1em] text-[#999]">
              Risk Warning
            </p>
            <p>
              Trading and investing carry a <strong className="font-semibold text-[#111]">substantial risk of loss</strong>.
              You could lose your entire investment. Historical performance does not guarantee
              future results. Backtesting results are simulated and do not account for real-world
              slippage, fees, or taxes.
            </p>
          </div>

          <p>
            <strong className="font-semibold text-[#111]">AI-generated content may be inaccurate, incomplete, or outdated.</strong>{' '}
            Data may be delayed. Always verify information against primary sources before making
            any financial decision. Past performance of any security or asset is not indicative
            of future results.
          </p>

          <p>
            You are <strong className="font-semibold text-[#111]">solely responsible</strong> for
            your investment decisions. Capital Lens accepts no liability for any trading or
            investment losses you may incur. Maximum liability is limited to amounts paid, if any.
          </p>

          <p>
            By continuing you acknowledge that you have read, understood, and accept the full{' '}
            <a href="/legal/disclaimer" target="_blank" rel="noopener noreferrer"
              className="underline text-[#111] hover:text-[#555]">
              Disclaimer
            </a>
            ,{' '}
            <a href="/legal/terms" target="_blank" rel="noopener noreferrer"
              className="underline text-[#111] hover:text-[#555]">
              Terms of Service
            </a>
            , and{' '}
            <a href="/legal/risk" target="_blank" rel="noopener noreferrer"
              className="underline text-[#111] hover:text-[#555]">
              Risk Warning
            </a>
            , and that you agree to use this platform for informational purposes only.
          </p>
        </div>

        {/* Acceptance checkbox + action */}
        <div className="px-6 py-4 border-t border-[#e0e0e0] flex-shrink-0 space-y-3">
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={checked}
              onChange={e => setChecked(e.target.checked)}
              className="mt-0.5 w-3.5 h-3.5 flex-shrink-0 cursor-pointer accent-[#111]"
            />
            <span className="text-[11px] text-[#555] leading-snug group-hover:text-[#111] transition-colors">
              I have read and understood the disclaimer. I accept that Capital Lens provides
              information only and is not financial advice. I take full responsibility for my
              own investment decisions.
            </span>
          </label>

          <div className="flex items-center justify-between gap-4">
            <p className="text-[9px] text-[#ccc] font-light leading-snug">
              Investment Advisers Act of 1940 · SEC Release IA-1092 · Not a registered adviser
            </p>
            <button
              onClick={accept}
              disabled={!checked || syncing}
              className="flex-shrink-0 px-5 py-2 bg-[#111] text-white text-xs font-medium uppercase tracking-[0.06em] hover:bg-[#333] disabled:opacity-30 disabled:cursor-not-allowed transition-colors duration-200"
            >
              {syncing ? 'Saving...' : 'I accept'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
