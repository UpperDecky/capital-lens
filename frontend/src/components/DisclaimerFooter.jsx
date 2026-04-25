/**
 * DisclaimerFooter -- persistent legal strip shown on every authenticated page.
 */
import { Link } from 'react-router-dom'

export default function DisclaimerFooter() {
  const year = new Date().getFullYear()
  return (
    <footer className="flex-shrink-0 border-t border-[#f0f0f0] bg-[#fafafa] px-6 py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-1.5">

        {/* Left: disclaimer text */}
        <p className="text-[10px] text-[#bbb] font-light leading-none">
          <span className="font-medium text-[#ccc] uppercase tracking-[0.06em] mr-2">Disclaimer</span>
          For informational purposes only. Not financial advice. AI content may be inaccurate.
          Capital Lens is not a registered investment adviser. Always do your own research.
        </p>

        {/* Right: legal links + copyright */}
        <div className="flex items-center gap-4 flex-shrink-0">
          <nav className="flex items-center gap-3">
            {[
              { to: '/legal/disclaimer', label: 'Disclaimer' },
              { to: '/legal/terms',      label: 'Terms'      },
              { to: '/legal/privacy',    label: 'Privacy'    },
              { to: '/legal/risk',       label: 'Risk'       },
            ].map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className="text-[9px] font-medium uppercase tracking-[0.08em] text-[#ccc] hover:text-[#666] transition-colors"
              >
                {label}
              </Link>
            ))}
          </nav>
          <p className="text-[9px] text-[#ddd] font-light whitespace-nowrap">
            &copy; {year} Capital Lens
          </p>
        </div>
      </div>
    </footer>
  )
}
