/**
 * Formatting utilities for Capital Lens.
 */

export function formatAmount(amount, currency = 'USD') {
  if (amount == null) return null
  const abs = Math.abs(amount)
  let formatted
  if (abs >= 1e12)      formatted = `$${(amount / 1e12).toFixed(2)}T`
  else if (abs >= 1e9)  formatted = `$${(amount / 1e9).toFixed(1)}B`
  else if (abs >= 1e6)  formatted = `$${(amount / 1e6).toFixed(0)}M`
  else                   formatted = `$${amount.toLocaleString()}`
  return `${formatted} ${currency}`
}

export function formatDate(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    const now = new Date()
    const isToday     = d.toDateString() === now.toDateString()
    const isThisYear  = d.getFullYear() === now.getFullYear()
    if (isToday) {
      return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    }
    return d.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric',
      ...(isThisYear ? {} : { year: 'numeric' }),
    })
  } catch {
    return dateStr
  }
}

export function formatDateTime(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    const now = new Date()
    const isThisYear = d.getFullYear() === now.getFullYear()
    return d.toLocaleString('en-US', {
      month:  'short',
      day:    'numeric',
      ...(isThisYear ? {} : { year: 'numeric' }),
      hour:   '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateStr
  }
}

export function timeAgo(dateStr) {
  if (!dateStr) return ''
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diff = Math.floor((now - then) / 1000)
  if (diff < 60)   return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

export function entityInitials(name) {
  if (!name) return '?'
  const words = name.trim().split(/\s+/)
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return (words[0][0] + words[words.length - 1][0]).toUpperCase()
}

export function sectorColor(sector) {
  // Monochrome — all sectors use the same tag style
  return 'border border-[#e0e0e0] text-[#666]'
}

export function eventTypeLabel(type) {
  return {
    filing:       'SEC Filing',
    insider_sale: 'Insider Sale',
    acquisition:  'Acquisition',
    news:         'News',
  }[type] || type
}

export function eventTypeBadge(type) {
  // Monochrome — all event types use the same label style
  return 'border border-[#e0e0e0] text-[#666]'
}

// Financial jargon tooltip map
export const JARGON = {
  'capex':       'Capital Expenditure — money a company spends to buy or upgrade physical assets like buildings or equipment.',
  '13f':         'Form 13F — a quarterly report required from large institutional investors showing their stock holdings.',
  '10-k':        'Annual report — a comprehensive summary of a company\'s financial performance over the full year.',
  '10-q':        'Quarterly report — a summary of financial performance for a 3-month period.',
  '8-k':         'Current report — filed when a company has a major event that shareholders need to know about immediately.',
  'form 4':      'Insider ownership report — filed when a company executive buys or sells shares.',
  'short interest': 'The percentage of shares that investors are betting will go down in price.',
  'ebitda':      'Earnings Before Interest, Taxes, Depreciation, and Amortization — a measure of a company\'s core profitability.',
  'pe ratio':    'Price-to-Earnings ratio — how much investors pay per dollar of profit. Higher means more expensive.',
  'aum':         'Assets Under Management — the total market value of investments that a financial firm manages on behalf of clients.',
  'ipo':         'Initial Public Offering — when a private company first sells its shares to the public on a stock exchange.',
  'yoy':         'Year-Over-Year — comparing a metric to the same period twelve months earlier.',
  'fcf':         'Free Cash Flow — the cash a company has left after paying its operating expenses and capital expenditures.',
}
