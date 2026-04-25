import { Link } from 'react-router-dom'

function Section({ title, children }) {
  return (
    <section className="mb-8">
      <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-[#999] mb-2">{title}</p>
      <div className="text-sm text-[#333] leading-relaxed font-light space-y-3">{children}</div>
    </section>
  )
}

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-2xl mx-auto px-6 py-12">

        <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#bbb] mb-6">
          <Link to="/" className="hover:text-[#666] transition-colors">Capital Lens</Link>
          {' / '}
          <span>Legal</span>
          {' / '}
          <span className="text-[#111]">Terms of Service</span>
        </p>

        <h1 className="text-2xl font-bold tracking-tight text-[#111] mb-2">Terms of Service</h1>
        <p className="text-xs text-[#999] mb-10">
          Effective date: January 1, 2025 &middot; Version 1.0
        </p>

        <Section title="Acceptance of Terms">
          <p>
            By accessing or using Capital Lens ("the Platform"), you agree to be bound by
            these Terms of Service and all applicable laws and regulations. If you do not
            agree to these terms, do not use the Platform.
          </p>
        </Section>

        <Section title="Description of Service">
          <p>
            Capital Lens is a self-hosted financial data aggregation and research tool. It
            ingests publicly available information from sources including SEC filings,
            congressional trade disclosures, government databases, and news feeds, and
            presents that information alongside AI-generated commentary for informational
            purposes.
          </p>
          <p>
            The Platform is not a broker-dealer, investment adviser, financial planner, or
            any other type of regulated financial service provider. We do not execute
            trades, manage portfolios, or provide personalised financial advice.
          </p>
        </Section>

        <Section title="Permitted Use">
          <p>You may use the Platform for:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Personal research and education</li>
            <li>Staying informed about publicly reported financial events</li>
            <li>Aggregating publicly available data for your own analysis</li>
          </ul>
          <p>You may not:</p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Redistribute, resell, or sublicense access to the Platform</li>
            <li>Use the Platform to provide investment advice to third parties</li>
            <li>Attempt to reverse-engineer or scrape the Platform at scale</li>
            <li>Use the Platform in any way that violates applicable law</li>
            <li>Claim that output from the Platform constitutes professional financial advice</li>
          </ul>
        </Section>

        <Section title="Accounts and Security">
          <p>
            You are responsible for maintaining the confidentiality of your account
            credentials. You are liable for all activities that occur under your account.
            Notify us immediately of any unauthorised use. We recommend enabling
            two-factor authentication.
          </p>
        </Section>

        <Section title="Intellectual Property">
          <p>
            The Platform's source code, design, and proprietary content are owned by
            Capital Lens. Public data sourced from government agencies (SEC, Congress,
            FRED, etc.) is in the public domain. AI-generated commentary is provided
            under these terms.
          </p>
        </Section>

        <Section title="Disclaimer of Warranties">
          <p>
            The Platform is provided "as-is" and "as available" without any warranty of
            any kind, express or implied, including but not limited to warranties of
            merchantability, fitness for a particular purpose, or non-infringement. We do
            not warrant that the Platform will be uninterrupted, error-free, or free of
            harmful components.
          </p>
        </Section>

        <Section title="Limitation of Liability">
          <p>
            See our full <Link to="/legal/disclaimer" className="underline text-[#111] hover:text-[#555]">Disclaimer</Link>.
            To the maximum extent permitted by law, Capital Lens is not liable for any
            direct, indirect, incidental, special, consequential, or punitive damages
            arising from your use of or inability to use the Platform.
          </p>
        </Section>

        <Section title="Changes to Terms">
          <p>
            We may update these terms at any time. Changes are effective immediately upon
            posting. Continued use of the Platform after changes constitutes acceptance.
            Significant changes will be communicated via the in-app disclaimer modal.
          </p>
        </Section>

        <Section title="Governing Law">
          <p>
            These terms are governed by the laws of the jurisdiction in which Capital Lens
            operates, without regard to conflict of law provisions. Any disputes shall be
            resolved by binding arbitration or, where applicable, in the appropriate courts
            of that jurisdiction.
          </p>
        </Section>

        <div className="mt-12 pt-6 border-t border-[#f0f0f0] flex flex-wrap gap-4 text-[10px] font-medium uppercase tracking-[0.08em]">
          <Link to="/legal/disclaimer" className="text-[#bbb] hover:text-[#111] transition-colors">Disclaimer</Link>
          <Link to="/legal/privacy"    className="text-[#bbb] hover:text-[#111] transition-colors">Privacy Policy</Link>
          <Link to="/legal/risk"       className="text-[#bbb] hover:text-[#111] transition-colors">Risk Warning</Link>
          <Link to="/"                 className="text-[#bbb] hover:text-[#111] transition-colors ml-auto">Back to App</Link>
        </div>
      </div>
    </div>
  )
}
