/**
 * DisclaimerFooter — permanent one-line legal strip at the bottom of every page.
 * Always visible so users are reminded the content is not financial advice.
 */
export default function DisclaimerFooter() {
  return (
    <footer className="flex-shrink-0 border-t border-[#f0f0f0] bg-[#fafafa] px-6 py-2 flex items-center justify-between gap-4">
      <p className="text-[10px] text-[#bbb] font-light leading-none">
        <span className="font-medium text-[#ccc] uppercase tracking-[0.06em] mr-2">Disclaimer</span>
        For informational purposes only. Not financial advice. AI-generated content may be
        inaccurate. Capital Lens is not a registered investment adviser. Always do your own research.
      </p>
      <p className="text-[10px] text-[#ccc] font-light flex-shrink-0">
        Data may be delayed · Not affiliated with SEC, FINRA, or any regulator
      </p>
    </footer>
  )
}
