export default function TagPill({ tag, onClick, active }) {
  return (
    <button
      onClick={onClick}
      className={`tag transition-all duration-200 ${active ? 'active' : ''}`}
    >
      {tag}
    </button>
  )
}
