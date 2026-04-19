/**
 * DisclaimerModal — shown once on first visit, requires explicit acknowledgment.
 *
 * Legal basis: Under the Investment Advisers Act of 1940 (15 U.S.C. § 80b),
 * a person who provides investment advice for compensation must register with
 * the SEC. Capital Lens does not charge for advice and provides only general
 * informational content, qualifying for the "publisher exemption" under
 * Section 202(a)(11)(D). This disclaimer makes that distinction explicit.
 *
 * Stores acknowledgment in localStorage so it only shows once per browser.
 */

import { useState, useEffect } from 'react'

const STORAGE_KEY = 'cl_disclaimer_v1'

export default function DisclaimerModal() {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      setVisible(true)
    }
  }, [])

  function accept() {
    localStorage.setItem(STORAGE_KEY, '1')
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm px-4">
      <div className="bg-white border border-[#111] max-w-lg w-full shadow-2xl">

        {/* Header */}
        <div className="px-6 py-5 border-b border-[#e0e0e0]">
          <p className="label text-[#999] mb-1">Before you continue</p>
          <h2 className="text-lg font-bold tracking-tight text-[#111]">
            Informational Use Only
          </h2>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4 text-xs text-[#444] leading-relaxed font-light">
          <p>
            <strong className="font-semibold text-[#111]">Capital Lens is not a financial adviser.</strong>{' '}
            Nothing on this platform — including AI-generated summaries, investment signals,
            market impact assessments, sector tags, or personal takeaways — constitutes
            investment advice, financial advice, trading advice, legal advice, or any other
            type of professional advice.
          </p>
          <p>
            Capital Lens aggregates publicly available financial data and applies AI
            commentary for <strong className="font-semibold text-[#111]">general informational and educational purposes only</strong>.
            It is not registered as an investment adviser with the U.S. Securities and
            Exchange Commission (SEC), FINRA, or any other regulatory authority.
          </p>
          <p>
            <strong className="font-semibold text-[#111]">AI-generated content may be inaccurate, incomplete, or outdated.</strong>{' '}
            Data may be delayed. Always verify information against primary sources before
            making any financial decision. Past performance of any security or asset is
            not indicative of future results.
          </p>
          <p>
            You are solely responsible for your investment decisions. By continuing, you
            acknowledge that you have read and understood this disclaimer and agree to
            use this platform for informational purposes only.
          </p>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[#e0e0e0] flex items-center justify-between gap-4">
          <p className="text-[10px] text-[#bbb] font-light leading-snug">
            Investment Advisers Act of 1940 · SEC Release IA-1092 · Not a registered adviser
          </p>
          <button
            onClick={accept}
            className="flex-shrink-0 px-5 py-2 bg-[#111] text-white text-xs font-medium uppercase tracking-[0.06em] hover:bg-[#333] transition-colors duration-200"
          >
            I understand
          </button>
        </div>
      </div>
    </div>
  )
}
