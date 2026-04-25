import { Link } from 'react-router-dom'

function Section({ title, children }) {
  return (
    <section className="mb-8">
      <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-[#999] mb-2">{title}</p>
      <div className="text-sm text-[#333] leading-relaxed font-light space-y-3">{children}</div>
    </section>
  )
}

export default function Disclaimer() {
  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-2xl mx-auto px-6 py-12">

        {/* Breadcrumb */}
        <p className="text-[10px] font-medium uppercase tracking-[0.08em] text-[#bbb] mb-6">
          <Link to="/" className="hover:text-[#666] transition-colors">Capital Lens</Link>
          {' / '}
          <span>Legal</span>
          {' / '}
          <span className="text-[#111]">Disclaimer</span>
        </p>

        <h1 className="text-2xl font-bold tracking-tight text-[#111] mb-2">Disclaimer</h1>
        <p className="text-xs text-[#999] mb-10">
          Effective date: January 1, 2025 &middot; Version 1.0
        </p>

        <Section title="Not Investment Advice">
          <p>
            Capital Lens is a data aggregation and research platform. Nothing on this
            platform -- including but not limited to AI-generated summaries, investment
            signals, market impact assessments, sector tags, personal takeaways, or any
            other content -- constitutes investment advice, financial advice, trading
            advice, legal advice, or any other type of professional advice.
          </p>
          <p>
            Capital Lens is not registered as an investment adviser with the U.S.
            Securities and Exchange Commission (SEC), the Financial Industry Regulatory
            Authority (FINRA), or any other regulatory authority in any jurisdiction.
            We qualify for the publisher exemption under Section 202(a)(11)(D) of the
            Investment Advisers Act of 1940.
          </p>
        </Section>

        <Section title="Your Responsibility">
          <p>
            All trading and investment decisions are solely your own. You must conduct
            your own analysis and due diligence before making any investment decision.
            Consult a licensed, registered financial adviser for advice tailored to your
            personal financial situation and goals.
          </p>
          <p>
            Capital Lens does not know your financial situation, risk tolerance, or
            investment objectives. We cannot and do not provide personalised advice.
            No fiduciary relationship exists between you and Capital Lens.
          </p>
        </Section>

        <Section title="Data Accuracy">
          <p>
            Information is sourced from publicly available records including SEC EDGAR
            filings, congressional trade disclosures, government databases, and third-party
            news feeds. Data is provided "as-is" without warranty of any kind.
          </p>
          <p>
            We are not liable for inaccuracies in source data, errors in our aggregation
            or processing, or AI-generated commentary that may be misleading or incorrect.
            Markets move rapidly; data displayed may be delayed or outdated. Always verify
            information against primary sources before acting.
          </p>
        </Section>

        <Section title="Limitation of Liability">
          <p>
            To the maximum extent permitted by applicable law, Capital Lens and its
            operators, contributors, and affiliates are not liable for:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Any trading or investment losses you incur</li>
            <li>Inaccuracies, delays, or errors in data or AI-generated content</li>
            <li>Decisions made based on information from this platform</li>
            <li>Any indirect, consequential, special, or punitive damages</li>
            <li>Loss of profits, revenue, data, or business opportunities</li>
          </ul>
          <p>
            Maximum aggregate liability is limited to amounts paid by you to Capital Lens,
            if any, during the three months preceding the claim.
          </p>
        </Section>

        <Section title="No Advisory Relationship">
          <p>
            Your use of Capital Lens does not create an advisory, fiduciary, or any other
            professional relationship. We provide information; you make decisions. Nothing
            in these terms or on this platform shall be construed to create such a
            relationship.
          </p>
        </Section>

        <Section title="Use at Own Risk">
          <p>
            By using Capital Lens you acknowledge that you have read and understood this
            disclaimer, accept all risks associated with using this platform and any
            decisions you make based on its content, and agree that Capital Lens bears no
            responsibility for outcomes of your investment decisions.
          </p>
        </Section>

        <div className="mt-12 pt-6 border-t border-[#f0f0f0] flex flex-wrap gap-4 text-[10px] font-medium uppercase tracking-[0.08em]">
          <Link to="/legal/terms"   className="text-[#bbb] hover:text-[#111] transition-colors">Terms of Service</Link>
          <Link to="/legal/privacy" className="text-[#bbb] hover:text-[#111] transition-colors">Privacy Policy</Link>
          <Link to="/legal/risk"    className="text-[#bbb] hover:text-[#111] transition-colors">Risk Warning</Link>
          <Link to="/"              className="text-[#bbb] hover:text-[#111] transition-colors ml-auto">Back to App</Link>
        </div>
      </div>
    </div>
  )
}
