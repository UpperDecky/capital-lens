import { entityInitials } from '../lib/format'

export default function EntityAvatar({ name, size = 'md' }) {
  const dims = { sm: 28, md: 36, lg: 48 }[size] || 36
  const font = { sm: 10, md: 12, lg: 16 }[size] || 12

  return (
    <div
      style={{ width: dims, height: dims, minWidth: dims }}
      className="border border-[#111] bg-[#111] flex items-center justify-center flex-shrink-0"
    >
      <span
        style={{ fontSize: font }}
        className="font-bold text-white font-mono tracking-tight leading-none"
      >
        {entityInitials(name)}
      </span>
    </div>
  )
}
