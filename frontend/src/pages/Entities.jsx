import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import EntityAvatar from '../components/EntityAvatar'
import { api } from '../lib/api'
import { formatAmount } from '../lib/format'

const SECTORS = ['Technology','Finance','E-Commerce','Energy','Healthcare','Defense','Aerospace','Retail','Automotive']

export default function Entities() {
  const navigate = useNavigate()
  const [entities, setEntities]     = useState([])
  const [loading, setLoading]       = useState(true)
  const [typeFilter, setTypeFilter] = useState('')
  const [sectorFilter, setSectorFilter] = useState('')
  const [search, setSearch]         = useState('')

  useEffect(() => {
    setLoading(true)
    api.getEntities({ type: typeFilter, sector: sectorFilter, q: search })
      .then(setEntities).catch(console.error).finally(() => setLoading(false))
  }, [typeFilter, sectorFilter, search])

  const companies   = entities.filter(e => e.type === 'company')
  const individuals = entities.filter(e => e.type === 'individual')

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">

      {/* Header */}
      <div className="pb-6 mb-8 border-b border-[#e0e0e0] flex items-end justify-between">
        <div>
          <p className="label text-[#999] mb-1">Directory</p>
          <h1 className="text-2xl font-bold tracking-tight text-[#111]">Entities</h1>
          <p className="text-xs text-[#999] font-light mt-1">{entities.length} tracked</p>
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          <div className="relative">
            <input type="text" value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search"
              className="pl-3 pr-3 py-1.5 text-xs w-36 border border-[#e0e0e0] focus:border-[#111] transition-colors duration-200" />
          </div>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
            className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] bg-white text-[#666] focus:border-[#111] transition-colors cursor-pointer">
            <option value="">All</option>
            <option value="company">Companies</option>
            <option value="individual">People</option>
          </select>
          <select value={sectorFilter} onChange={e => setSectorFilter(e.target.value)}
            className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] bg-white text-[#666] focus:border-[#111] transition-colors cursor-pointer">
            <option value="">All Sectors</option>
            {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-[#e0e0e0]">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="bg-white p-4 h-20 animate-pulse">
              <div className="flex gap-3">
                <div className="w-9 h-9 bg-[#f0f0f0]" />
                <div className="flex-1 space-y-2 pt-1">
                  <div className="h-2.5 w-28 bg-[#f0f0f0]" />
                  <div className="h-2 w-16 bg-[#f5f5f5]" />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-10">
          {(!typeFilter || typeFilter === 'company') && companies.length > 0 && (
            <section>
              {!typeFilter && (
                <div className="flex items-center gap-4 mb-4">
                  <p className="label text-[#999]">Companies</p>
                  <div className="flex-1 h-px bg-[#e0e0e0]" />
                  <p className="label text-[#ccc]">{companies.length}</p>
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-[#e0e0e0]">
                {companies.map(en => <EntityRow key={en.id} entity={en} onClick={() => navigate(`/entities/${en.id}`)} />)}
              </div>
            </section>
          )}
          {(!typeFilter || typeFilter === 'individual') && individuals.length > 0 && (
            <section>
              {!typeFilter && (
                <div className="flex items-center gap-4 mb-4">
                  <p className="label text-[#999]">Individuals</p>
                  <div className="flex-1 h-px bg-[#e0e0e0]" />
                  <p className="label text-[#ccc]">{individuals.length}</p>
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-px bg-[#e0e0e0]">
                {individuals.map(en => <EntityRow key={en.id} entity={en} onClick={() => navigate(`/entities/${en.id}`)} />)}
              </div>
            </section>
          )}
          {entities.length === 0 && (
            <p className="text-center py-16 text-xs text-[#999] font-light uppercase tracking-[0.1em]">
              No matches
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function EntityRow({ entity: en, onClick }) {
  return (
    <button onClick={onClick}
      className="bg-white p-4 text-left hover:bg-[#fafafa] transition-colors duration-200 group w-full border-0">
      <div className="flex items-center gap-3">
        <EntityAvatar name={en.name} size="md" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-[#111] truncate group-hover:underline">{en.name}</p>
          <p className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#999] mt-0.5">{en.sector}</p>
        </div>
        {en.net_worth && (
          <p className="text-xs font-mono font-bold text-[#111] flex-shrink-0 ml-2">
            {formatAmount(en.net_worth).replace(' USD', '')}
          </p>
        )}
      </div>
    </button>
  )
}
