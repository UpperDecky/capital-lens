import { Link } from 'react-router-dom'

function Section({ title, children }) {
  return (
    <section className="mb-8">
      <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-[#999] mb-2">{title}</p>
      <div className="text-sm text-[#333] leading-relaxed font-light space-y-3">{children}</div>
    </section>
  )
}

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-2xl mx-auto px-6 py-12">

        <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#bbb] mb-6">
          <Link to="/" className="hover:text-[#666] transition-colors">Capital Lens</Link>
          {' / '}
          <span>Legal</span>
          {' / '}
          <span className="text-[#111]">Privacy Policy</span>
        </p>

        <h1 className="text-2xl font-bold tracking-tight text-[#111] mb-2">Privacy Policy</h1>
        <p className="text-xs text-[#999] mb-10">
          Effective date: January 1, 2025 &middot; Version 1.0
        </p>

        <Section title="Overview">
          <p>
            Capital Lens is self-hosted software. Your data lives on the server you control.
            We do not transmit your personal data to third parties except as explicitly
            described below. This policy explains what data we collect and how we use it.
          </p>
        </Section>

        <Section title="Data We Collect">
          <p><strong className="font-semibold text-[#111]">Account data:</strong></p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Email address (used for login; stored in your self-hosted database)</li>
            <li>Password hash (bcrypt; we never store or see your plaintext password)</li>
            <li>Tier (free/pro/admin) and account creation timestamp</li>
            <li>MFA secret (if enabled; stored encrypted)</li>
            <li>Disclaimer acceptance timestamp and ToS version accepted</li>
          </ul>
          <p className="mt-3"><strong className="font-semibold text-[#111]">Usage data:</strong></p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Daily event count (for free-tier rate limiting; resets each UTC day)</li>
            <li>Security audit log entries (login events, disclaimer acceptance)</li>
          </ul>
        </Section>

        <Section title="Data We Do NOT Collect">
          <ul className="list-disc pl-5 space-y-1">
            <li>Payment or billing information (no payments processed by this platform)</li>
            <li>Browser fingerprints or cross-site tracking cookies</li>
            <li>Location data beyond what is implicit in your IP address</li>
            <li>Behavioural analytics sent to external services</li>
          </ul>
        </Section>

        <Section title="Third-Party Data Sources">
          <p>
            Capital Lens fetches publicly available data from external APIs. Your identity
            is not transmitted to these services unless you configure credentials for them:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>OpenRouter / Anthropic -- AI enrichment (event summaries)</li>
            <li>SEC EDGAR, Twelve Data, CoinGecko, FRED -- financial data</li>
            <li>OpenSky Network, aisstream.io -- aircraft and maritime</li>
            <li>NASA FIRMS, Cloudflare Radar -- satellite and infrastructure</li>
            <li>Polymarket -- prediction markets</li>
          </ul>
          <p>
            API keys you configure in .env are stored on your server only and are never
            transmitted to Capital Lens or any party other than the respective API provider.
          </p>
        </Section>

        <Section title="How We Use Your Data">
          <ul className="list-disc pl-5 space-y-1">
            <li>To authenticate you and manage your session</li>
            <li>To enforce tier-based usage limits</li>
            <li>To maintain an audit trail for security and legal compliance</li>
            <li>To record disclaimer acceptance as required for legal protection</li>
          </ul>
          <p>We do not sell, rent, or share your personal data with any third party.</p>
        </Section>

        <Section title="Data Retention">
          <p>
            Account data is retained until you delete your account. Security audit logs
            are retained indefinitely as required by compliance obligations. Daily usage
            counters reset each UTC day.
          </p>
        </Section>

        <Section title="Security">
          <p>
            Passwords are hashed with bcrypt and never stored in plaintext. Optional
            field-level encryption for PII is available (see ENCRYPTION_KEY in .env).
            You are responsible for securing the server, database file, and .env secrets
            on your self-hosted deployment.
          </p>
        </Section>

        <Section title="Your Rights">
          <p>
            As the operator of your self-hosted instance, you have full control over all
            data. You may delete your account and associated data directly from the SQLite
            database at any time. We recommend reviewing SQLite database permissions and
            encryption settings for your deployment environment.
          </p>
        </Section>

        <Section title="Children">
          <p>
            Capital Lens is not directed at individuals under the age of 18. Do not use
            this platform if you are under 18.
          </p>
        </Section>

        <div className="mt-12 pt-6 border-t border-[#f0f0f0] flex flex-wrap gap-4 text-[10px] font-medium uppercase tracking-[0.08em]">
          <Link to="/legal/disclaimer" className="text-[#bbb] hover:text-[#111] transition-colors">Disclaimer</Link>
          <Link to="/legal/terms"      className="text-[#bbb] hover:text-[#111] transition-colors">Terms of Service</Link>
          <Link to="/legal/risk"       className="text-[#bbb] hover:text-[#111] transition-colors">Risk Warning</Link>
          <Link to="/"                 className="text-[#bbb] hover:text-[#111] transition-colors ml-auto">Back to App</Link>
        </div>
      </div>
    </div>
  )
}
