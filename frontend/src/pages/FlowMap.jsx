/**
 * FlowMap — Obsidian-style knowledge graph of entity connections.
 *
 * Features:
 *  - Nodes: all entities, sized by market cap. Click to select.
 *  - Edges: typed (board, investment, partner, competitor, political_trade, etc.)
 *           each type has a distinct stroke style (solid/dashed/dotted).
 *  - Selection: clicking a node highlights it + all direct connections,
 *               fades unconnected nodes/edges (exactly like Obsidian).
 *  - Edge hover: shows a tooltip with the edge label.
 *  - Info panel: selected node details in bottom-left corner.
 *  - Sector filter + entity type filter.
 *  - Zoom + pan + drag nodes.
 * D3 is used ONLY on this page (spec requirement).
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import * as d3 from 'd3'
import { formatAmount } from '../lib/format'

const BASE = ''
const SECTORS = [
  'Technology', 'Finance', 'E-Commerce', 'Energy',
  'Healthcare', 'Defense', 'Aerospace', 'Retail', 'Automotive', 'Government',
]

// ── Edge type visual styles ──────────────────────────────────────────────────
const EDGE_STYLES = {
  board:              { dash: 'none',    stroke: '#111', label: 'Control / Board'    },
  investment:         { dash: 'none',    stroke: '#555', label: 'Investment'          },
  acquisition:        { dash: 'none',    stroke: '#333', label: 'Acquisition'         },
  partner:            { dash: '6,3',     stroke: '#777', label: 'Partnership'         },
  competitor:         { dash: '3,3',     stroke: '#aaa', label: 'Competitor'          },
  customer:           { dash: '8,4',     stroke: '#888', label: 'Customer'            },
  supplier:           { dash: '8,4',     stroke: '#888', label: 'Supplier'            },
  political_trade:    { dash: '4,2,1,2', stroke: '#444', label: 'Political Trade'     },
  political:          { dash: '4,2',     stroke: '#666', label: 'Political'           },
  congressional_trade:{ dash: '4,2,1,2', stroke: '#444', label: 'Congressional Trade' },
  investor:           { dash: 'none',    stroke: '#555', label: 'Investment'          },
  subsidiary:         { dash: 'none',    stroke: '#333', label: 'Subsidiary'          },
}

// ── Sector node fill shades ──────────────────────────────────────────────────
const SECTOR_FILL = {
  Technology:   '#222',
  Finance:      '#3a3a3a',
  'E-Commerce': '#444',
  Energy:       '#555',
  Healthcare:   '#4a4a4a',
  Defense:      '#333',
  Aerospace:    '#2a2a2a',
  Retail:       '#5a5a5a',
  Automotive:   '#484848',
  Government:   '#666',
}

export default function FlowMap() {
  const svgRef   = useRef(null)
  const wrapRef  = useRef(null)
  const simRef   = useRef(null)
  const navigate = useNavigate()

  const [data,          setData]         = useState(null)
  const [loading,       setLoading]      = useState(true)
  const [error,         setError]        = useState(null)
  const [sectorFilter,  setSectorFilter] = useState('')
  const [typeFilter,    setTypeFilter]   = useState('')
  const [selectedNode,  setSelectedNode] = useState(null)
  const [edgeTooltip,      setEdgeTooltip]      = useState(null)
  const [nodeTooltip,      setNodeTooltip]      = useState(null)
  const [portfolio,        setPortfolio]        = useState(null)
  const [portfolioLoading, setPortfolioLoading] = useState(false)

  // Fetch portfolio when a node is selected
  useEffect(() => {
    if (!selectedNode) { setPortfolio(null); return }
    setPortfolioLoading(true)
    fetch(`${BASE}/entities/${selectedNode.id}/portfolio`)
      .then(r => r.json())
      .then(d => setPortfolio(d))
      .catch(() => setPortfolio(null))
      .finally(() => setPortfolioLoading(false))
  }, [selectedNode])

  // Fetch flow data
  const fetchFlow = useCallback(() => {
    setLoading(true)
    const qs = new URLSearchParams()
    if (sectorFilter) qs.set('sector', sectorFilter)
    if (typeFilter)   qs.set('type', typeFilter)
    fetch(`${BASE}/flow${qs.toString() ? '?' + qs : ''}`)
      .then(r => r.json())
      .then(d => { setData(d); setError(null) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [sectorFilter, typeFilter])

  useEffect(() => { fetchFlow() }, [fetchFlow])
  useEffect(() => { setSelectedNode(null) }, [sectorFilter, typeFilter])

  // ── D3 render ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!data || loading || !svgRef.current || !wrapRef.current) return

    const { nodes: rawNodes, edges: rawEdges } = data
    const rect = wrapRef.current.getBoundingClientRect()
    const w = (rect.width  > 0 ? rect.width  : wrapRef.current.clientWidth)  || 1000
    const h = (rect.height > 0 ? rect.height : wrapRef.current.clientHeight) || 600

    // Clone so D3 can mutate freely
    const nodes = rawNodes.map(n => ({ ...n }))
    const nodeById = Object.fromEntries(nodes.map(n => [n.id, n]))

    // Only include edges where both endpoints are in current node set
    const nodeIds = new Set(nodes.map(n => n.id))
    const edges = rawEdges
      .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map(e => ({ ...e }))

    // ── SVG setup ──────────────────────────────────────────────────────────
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    svg.attr('viewBox', `0 0 ${w} ${h}`)

    // Zoom behaviour
    const g = svg.append('g')
    const zoom = d3.zoom()
      .scaleExtent([0.15, 6])
      .on('zoom', ({ transform }) => g.attr('transform', transform))
    svg.call(zoom)
    svg.on('click', (event) => {
      if (event.target === svgRef.current) setSelectedNode(null)
    })

    // Faint grid
    const grid = g.append('g').attr('class', 'grid')
    for (let x = 0; x < w * 3; x += 48)
      grid.append('line').attr('x1', x - w).attr('y1', -h).attr('x2', x - w).attr('y2', h * 3)
        .attr('stroke', '#f2f2f2').attr('stroke-width', 0.5)
    for (let y = 0; y < h * 3; y += 48)
      grid.append('line').attr('x1', -w).attr('y1', y - h).attr('x2', w * 3).attr('y2', y - h)
        .attr('stroke', '#f2f2f2').attr('stroke-width', 0.5)

    // Radius scale
    const maxWorth = d3.max(nodes, d => d.net_worth || 0) || 1
    const rScale = d3.scaleSqrt().domain([0, maxWorth]).range([5, 30])

    // ── Build adjacency for highlight logic ────────────────────────────────
    const adjacency = {}  // node_id → Set of neighbor ids
    const edgesByNode = {} // node_id → [edge indices]
    nodes.forEach(n => { adjacency[n.id] = new Set(); edgesByNode[n.id] = [] })
    edges.forEach((e, i) => {
      const sid = typeof e.source === 'object' ? e.source.id : e.source
      const tid = typeof e.target === 'object' ? e.target.id : e.target
      adjacency[sid]?.add(tid)
      adjacency[tid]?.add(sid)
      edgesByNode[sid]?.push(i)
      edgesByNode[tid]?.push(i)
    })

    // ── Arrow markers (one per edge type) ─────────────────────────────────
    const defs = svg.append('defs')
    Object.entries(EDGE_STYLES).forEach(([type, style]) => {
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('markerWidth', 6).attr('markerHeight', 6)
        .attr('refX', 6).attr('refY', 3)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,0 L0,6 L6,3 z')
        .attr('fill', style.stroke)
        .attr('opacity', 0.6)
    })

    // ── Edge layer ─────────────────────────────────────────────────────────
    const edgeGroup = g.append('g').attr('class', 'edges')
    const edgeSel = edgeGroup.selectAll('line')
      .data(edges)
      .join('line')
      .attr('stroke', d => (EDGE_STYLES[d.type] || EDGE_STYLES.partner).stroke)
      .attr('stroke-width', d => Math.max(0.8, (d.weight || 1) * 0.6))
      .attr('stroke-dasharray', d => (EDGE_STYLES[d.type] || EDGE_STYLES.partner).dash)
      .attr('opacity', 0.55)
      .attr('marker-end', d => `url(#arrow-${d.type})`)
      .attr('cursor', 'crosshair')
      .on('mouseenter', function (event, d) {
        d3.select(this).attr('opacity', 1).attr('stroke-width', d => Math.max(1.5, (d.weight || 1) * 0.9))
        setEdgeTooltip({ label: d.label, type: d.type, x: event.pageX, y: event.pageY })
      })
      .on('mousemove', (event) => {
        setEdgeTooltip(t => t ? { ...t, x: event.pageX, y: event.pageY } : t)
      })
      .on('mouseleave', function (event, d) {
        d3.select(this)
          .attr('opacity', 0.55)
          .attr('stroke-width', Math.max(0.8, (d.weight || 1) * 0.6))
        setEdgeTooltip(null)
      })

    // ── Node layer ─────────────────────────────────────────────────────────
    const nodeGroup = g.append('g').attr('class', 'nodes')
    const nodeSel = nodeGroup.selectAll('g')
      .data(nodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(d3.drag()
        .on('start', (ev, d) => { if (!ev.active) simRef.current?.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag',  (ev, d) => { d.fx = ev.x; d.fy = ev.y })
        .on('end',   (ev, d) => { if (!ev.active) simRef.current?.alphaTarget(0); d.fx = null; d.fy = null })
      )
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedNode(prev => prev?.id === d.id ? null : d)
        setNodeTooltip(null)
      })
      .on('dblclick', (event, d) => {
        event.stopPropagation()
        navigate(`/entities/${d.id}`)
      })
      .on('mouseenter', (event, d) => {
        setNodeTooltip({ ...d, x: event.pageX, y: event.pageY })
      })
      .on('mousemove', (event) => {
        setNodeTooltip(t => t ? { ...t, x: event.pageX, y: event.pageY } : t)
      })
      .on('mouseleave', () => setNodeTooltip(null))

    // Node circles
    nodeSel.append('circle')
      .attr('r', d => rScale(d.net_worth || 0))
      .attr('fill', d => SECTOR_FILL[d.sector] || '#555')
      .attr('stroke', '#fff')
      .attr('stroke-width', 1)

    // Node labels (abbreviate for smaller nodes)
    nodeSel.append('text')
      .text(d => {
        const r = rScale(d.net_worth || 0)
        if (r > 18) return d.name.split(' ')[0]
        if (r > 12) return d.name.split(' ')[0].slice(0, 4)
        return ''
      })
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('font-size', d => Math.min(rScale(d.net_worth || 0) * 0.55, 11))
      .attr('font-family', '"IBM Plex Mono", monospace')
      .attr('fill', '#fff')
      .attr('pointer-events', 'none')

    // ── Force simulation ───────────────────────────────────────────────────
    const sim = d3.forceSimulation(nodes)
      .force('link',    d3.forceLink(edges).id(d => d.id).distance(d => 80 + (5 - (d.weight || 2)) * 15).strength(0.2))
      .force('charge',  d3.forceManyBody().strength(d => -120 - rScale(d.net_worth || 0) * 3))
      .force('center',  d3.forceCenter(w / 2, h / 2))
      .force('collide', d3.forceCollide(d => rScale(d.net_worth || 0) + 8))
      .on('tick', () => {
        edgeSel
          .attr('x1', d => (d.source.x || 0))
          .attr('y1', d => (d.source.y || 0))
          .attr('x2', d => {
            const r = rScale((typeof d.target === 'object' ? d.target.net_worth : 0) || 0)
            const dx = (d.target.x || 0) - (d.source.x || 0)
            const dy = (d.target.y || 0) - (d.source.y || 0)
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            return (d.target.x || 0) - (dx / dist) * (r + 4)
          })
          .attr('y2', d => {
            const r = rScale((typeof d.target === 'object' ? d.target.net_worth : 0) || 0)
            const dx = (d.target.x || 0) - (d.source.x || 0)
            const dy = (d.target.y || 0) - (d.source.y || 0)
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            return (d.target.y || 0) - (dy / dist) * (r + 4)
          })
        nodeSel.attr('transform', d => `translate(${d.x || 0},${d.y || 0})`)
      })
    simRef.current = sim

    // ── Highlight on selectedNode change ──────────────────────────────────
    // We run this reactively via a separate effect (see below)
    // Store accessor fns on the elements for the highlight effect to call
    svgRef.current.__edgeSel = edgeSel
    svgRef.current.__nodeSel = nodeSel
    svgRef.current.__adjacency = adjacency
    svgRef.current.__edgesByNode = edgesByNode
    svgRef.current.__rScale = rScale
    svgRef.current.__edges = edges

    return () => sim.stop()
  }, [data, loading, navigate]) // eslint-disable-line

  // ── Highlight effect (runs whenever selectedNode changes) ─────────────────
  useEffect(() => {
    if (!svgRef.current) return
    const edgeSel     = svgRef.current.__edgeSel
    const nodeSel     = svgRef.current.__nodeSel
    const adjacency   = svgRef.current.__adjacency
    const edgesByNode = svgRef.current.__edgesByNode
    const rScale      = svgRef.current.__rScale
    if (!edgeSel || !nodeSel) return

    if (!selectedNode) {
      // Reset all to default
      nodeSel.select('circle')
        .attr('fill', d => SECTOR_FILL[d.sector] || '#555')
        .attr('stroke', '#fff')
        .attr('stroke-width', 1)
        .attr('opacity', 1)
      nodeSel.select('text').attr('opacity', 1)
      edgeSel.attr('opacity', 0.55)
      return
    }

    const connectedIds = adjacency[selectedNode.id] || new Set()
    const connectedEdgeIdxs = new Set(edgesByNode[selectedNode.id] || [])

    // Dim / highlight nodes
    nodeSel.select('circle')
      .attr('fill', d => {
        if (d.id === selectedNode.id) return '#111'
        if (connectedIds.has(d.id)) return SECTOR_FILL[d.sector] || '#555'
        return '#ccc'
      })
      .attr('stroke', d => d.id === selectedNode.id ? '#000' : '#fff')
      .attr('stroke-width', d => d.id === selectedNode.id ? 2 : 1)
      .attr('opacity', d =>
        d.id === selectedNode.id || connectedIds.has(d.id) ? 1 : 0.18
      )
    nodeSel.select('text')
      .attr('opacity', d =>
        d.id === selectedNode.id || connectedIds.has(d.id) ? 1 : 0.1
      )

    // Dim / highlight edges
    edgeSel
      .attr('opacity', (d, i) => connectedEdgeIdxs.has(i) ? 0.85 : 0.05)
      .attr('stroke-width', (d, i) =>
        connectedEdgeIdxs.has(i) ? Math.max(1.5, (d.weight || 1) * 0.9) : 0.5
      )
  }, [selectedNode])

  const connectedNodes = selectedNode && svgRef.current?.__adjacency
    ? [...(svgRef.current.__adjacency[selectedNode.id] || new Set())]
    : []

  const connectedEdges = selectedNode && svgRef.current?.__edges
    ? svgRef.current.__edges.filter((_, i) =>
        (svgRef.current.__edgesByNode[selectedNode.id] || []).includes(i)
      )
    : []

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="px-6 py-5 border-b border-[#e0e0e0] flex items-center justify-between flex-shrink-0">
        <div>
          <p className="label text-[#999] mb-0.5">Capital Lens</p>
          <h1 className="text-xl font-bold tracking-tight text-[#111]">Connection Map</h1>
          {data && (
            <p className="text-[10px] text-[#999] font-light mt-0.5">
              {data.nodes.length} entities · {data.edges.length} connections · click a node to explore · double-click to profile
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <select value={sectorFilter} onChange={e => setSectorFilter(e.target.value)}
            className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] bg-white text-[#666] focus:border-[#111] cursor-pointer">
            <option value="">All Sectors</option>
            {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
            className="px-3 py-1.5 text-xs font-medium uppercase tracking-[0.06em] border border-[#e0e0e0] bg-white text-[#666] focus:border-[#111] cursor-pointer">
            <option value="">Companies + People</option>
            <option value="company">Companies only</option>
            <option value="individual">People only</option>
          </select>
        </div>
      </div>

      {/* ── Main canvas area ────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Graph */}
        <div ref={wrapRef} className="relative flex-1 bg-white overflow-hidden">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="w-48 h-px bg-[#f0f0f0] relative overflow-hidden mb-3">
                  <div className="absolute inset-y-0 w-1/4 bg-gradient-to-r from-transparent via-[#ccc] to-transparent animate-scan" />
                </div>
                <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-[#bbb]">Building connection graph</p>
              </div>
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <p className="text-xs text-[#999]">Cannot reach backend — start uvicorn on port 8000</p>
            </div>
          )}
          <svg ref={svgRef} className="w-full h-full" />

          {/* Zoom hint */}
          {!loading && data && (
            <p className="absolute bottom-3 right-4 text-[9px] font-medium uppercase tracking-[0.08em] text-[#ccc] pointer-events-none">
              Scroll to zoom · Drag nodes · Click to select · Dbl-click to profile
            </p>
          )}
        </div>

        {/* ── Right panel: legend + selected node info ─────────────────── */}
        <div className="w-52 border-l border-[#e0e0e0] flex flex-col overflow-y-auto flex-shrink-0 bg-white">

          {/* Edge type legend */}
          <div className="p-4 border-b border-[#e0e0e0]">
            <p className="label text-[#bbb] mb-3">Connection Types</p>
            <div className="space-y-2">
              {Object.entries(EDGE_STYLES)
                .filter(([, s], i, arr) => arr.findIndex(([, x]) => x.label === s.label) === i)
                .map(([type, style]) => (
                  <div key={type} className="flex items-center gap-2">
                    <svg width="24" height="10" className="flex-shrink-0">
                      <line x1="0" y1="5" x2="24" y2="5"
                        stroke={style.stroke}
                        strokeWidth="1.5"
                        strokeDasharray={style.dash === 'none' ? undefined : style.dash}
                      />
                    </svg>
                    <span className="text-[9px] font-medium uppercase tracking-[0.06em] text-[#666] leading-none">
                      {style.label}
                    </span>
                  </div>
                ))}
            </div>
          </div>

          {/* Sector legend */}
          <div className="p-4 border-b border-[#e0e0e0]">
            <p className="label text-[#bbb] mb-3">Sectors</p>
            <div className="space-y-1.5">
              {Object.entries(SECTOR_FILL).map(([sector, fill]) => (
                <div key={sector} className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 flex-shrink-0" style={{ background: fill }} />
                  <span className="text-[9px] font-medium uppercase tracking-[0.06em] text-[#666] leading-none">{sector}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Selected node info + investment lean */}
          {selectedNode && (
            <div className="p-4 flex-1 overflow-y-auto">
              <div className="flex items-center justify-between mb-3">
                <p className="label text-[#bbb]">Selected</p>
                <button onClick={() => setSelectedNode(null)}
                  className="text-[10px] text-[#bbb] hover:text-[#111] transition-colors">×</button>
              </div>

              {/* Entity identity */}
              <div className="mb-3 pb-3 border-b border-[#f0f0f0]">
                <p className="text-sm font-bold text-[#111] tracking-tight leading-tight">{selectedNode.name}</p>
                <p className="text-[10px] uppercase tracking-[0.06em] text-[#999] mt-0.5">
                  {selectedNode.type} · {selectedNode.sector}
                </p>
                {selectedNode.net_worth > 0 && (
                  <p className="font-mono text-xs font-bold text-[#111] mt-1">
                    {formatAmount(selectedNode.net_worth)}
                  </p>
                )}
                {selectedNode.description && (
                  <p className="text-[10px] text-[#666] font-light mt-2 leading-relaxed">
                    {selectedNode.description}
                  </p>
                )}
              </div>

              {/* Investment lean — sector exposure */}
              {portfolioLoading && (
                <p className="text-[9px] uppercase tracking-[0.08em] text-[#ccc] mb-3">Loading portfolio…</p>
              )}
              {portfolio && !portfolioLoading && (
                <>
                  {/* Sector exposure bars */}
                  {portfolio.sector_exposure?.length > 0 && (
                    <div className="mb-3 pb-3 border-b border-[#f0f0f0]">
                      <p className="label text-[#bbb] mb-2">Investment Lean</p>
                      <div className="space-y-1.5">
                        {(() => {
                          const max = Math.max(...portfolio.sector_exposure.map(s => s.count), 1)
                          return portfolio.sector_exposure.slice(0, 6).map(s => (
                            <div key={s.sector}>
                              <div className="flex justify-between items-center mb-0.5">
                                <span className="text-[8px] font-medium uppercase tracking-[0.05em] text-[#555]">
                                  {s.sector}
                                </span>
                                <span className="text-[8px] font-mono text-[#999]">{s.count}</span>
                              </div>
                              <div className="h-1 bg-[#f0f0f0] w-full">
                                <div
                                  className="h-full bg-[#111] transition-all duration-300"
                                  style={{ width: `${(s.count / max) * 100}%` }}
                                />
                              </div>
                            </div>
                          ))
                        })()}
                      </div>
                    </div>
                  )}

                  {/* Event type breakdown */}
                  {portfolio.event_breakdown?.length > 0 && (
                    <div className="mb-3 pb-3 border-b border-[#f0f0f0]">
                      <p className="label text-[#bbb] mb-2">Activity Mix</p>
                      <div className="space-y-1">
                        {portfolio.event_breakdown.slice(0, 5).map(e => (
                          <div key={e.event_type} className="flex justify-between items-center">
                            <span className="text-[8px] font-medium uppercase tracking-[0.05em] text-[#555]">
                              {e.event_type.replace(/_/g, ' ')}
                            </span>
                            <span className="text-[8px] font-mono font-bold text-[#111]">{e.count}</span>
                          </div>
                        ))}
                      </div>
                      {portfolio.total_capital_tracked > 0 && (
                        <div className="mt-2 pt-2 border-t border-[#f0f0f0]">
                          <div className="flex justify-between items-center">
                            <span className="text-[8px] font-medium uppercase tracking-[0.05em] text-[#999]">
                              Capital Tracked
                            </span>
                            <span className="text-[8px] font-mono font-bold text-[#111]">
                              {formatAmount(portfolio.total_capital_tracked)}
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Congressional trade buy/sell split */}
                  {portfolio.congressional_trades?.total > 0 && (
                    <div className="mb-3 pb-3 border-b border-[#f0f0f0]">
                      <p className="label text-[#bbb] mb-2">Congress Trades</p>
                      <div className="flex gap-2">
                        <div className="flex-1 bg-[#f9f9f9] p-2 text-center">
                          <p className="text-base font-bold text-[#111] font-mono">{portfolio.congressional_trades.buys}</p>
                          <p className="text-[8px] uppercase tracking-[0.06em] text-[#22c55e]">Buys</p>
                        </div>
                        <div className="flex-1 bg-[#f9f9f9] p-2 text-center">
                          <p className="text-base font-bold text-[#111] font-mono">{portfolio.congressional_trades.sells}</p>
                          <p className="text-[8px] uppercase tracking-[0.06em] text-[#ef4444]">Sells</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Top events by amount */}
                  {portfolio.top_events?.length > 0 && (
                    <div className="mb-3 pb-3 border-b border-[#f0f0f0]">
                      <p className="label text-[#bbb] mb-2">Largest Moves</p>
                      <div className="space-y-1.5">
                        {portfolio.top_events.map((ev, i) => (
                          <div key={i}>
                            <p className="text-[9px] font-mono font-bold text-[#111]">
                              {formatAmount(ev.amount)}
                            </p>
                            <p className="text-[8px] text-[#666] leading-tight line-clamp-2">{ev.headline}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Connections list */}
              {connectedEdges.length > 0 && (
                <div className="mb-3">
                  <p className="label text-[#bbb] mb-2">{connectedEdges.length} Connection{connectedEdges.length !== 1 ? 's' : ''}</p>
                  <div className="space-y-1">
                    {connectedEdges.slice(0, 8).map((edge, i) => {
                      const otherId = (typeof edge.source === 'object' ? edge.source.id : edge.source) === selectedNode.id
                        ? (typeof edge.target === 'object' ? edge.target.id : edge.target)
                        : (typeof edge.source === 'object' ? edge.source.id : edge.source)
                      const other = data.nodes.find(n => n.id === otherId)
                      return (
                        <div key={i} className="flex items-start gap-1.5">
                          <svg width="12" height="10" className="flex-shrink-0 mt-0.5">
                            <line x1="0" y1="5" x2="12" y2="5"
                              stroke={(EDGE_STYLES[edge.type] || EDGE_STYLES.partner).stroke}
                              strokeWidth="1.5"
                              strokeDasharray={(EDGE_STYLES[edge.type] || EDGE_STYLES.partner).dash === 'none' ? undefined : (EDGE_STYLES[edge.type] || EDGE_STYLES.partner).dash}
                            />
                          </svg>
                          <span className="text-[9px] text-[#444] leading-tight">
                            <strong>{other?.name || 'Unknown'}</strong>
                            <br />
                            <span className="text-[#999]">{edge.label}</span>
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              <button
                onClick={() => navigate(`/entities/${selectedNode.id}`)}
                className="mt-2 w-full px-3 py-2 text-[10px] font-medium uppercase tracking-[0.08em] border border-[#111] text-[#111] hover:bg-[#111] hover:text-white transition-colors duration-200"
              >
                View Full Profile →
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Edge tooltip ────────────────────────────────────────────────── */}
      {edgeTooltip && (
        <div className="fixed z-50 bg-[#111] border border-[#333] px-2.5 py-2 pointer-events-none"
          style={{ left: edgeTooltip.x + 10, top: edgeTooltip.y - 36 }}>
          <p className="text-[10px] font-medium uppercase tracking-[0.06em] text-[#999]">
            {(EDGE_STYLES[edgeTooltip.type] || {}).label || edgeTooltip.type}
          </p>
          <p className="text-xs text-white font-light">{edgeTooltip.label}</p>
        </div>
      )}

      {/* ── Node hover tooltip ───────────────────────────────────────────── */}
      {nodeTooltip && !selectedNode && (
        <div className="fixed z-50 bg-[#111] border border-[#333] px-3 py-2.5 pointer-events-none"
          style={{ left: nodeTooltip.x + 14, top: nodeTooltip.y - 56 }}>
          <p className="text-xs font-bold text-white tracking-tight">{nodeTooltip.name}</p>
          <p className="text-[10px] uppercase tracking-[0.06em] text-[#999] mt-0.5">{nodeTooltip.sector}</p>
          {nodeTooltip.net_worth > 0 && (
            <p className="text-xs font-mono text-white mt-1">{formatAmount(nodeTooltip.net_worth)}</p>
          )}
          <p className="text-[9px] text-[#666] mt-1">Click to explore · Dbl-click for profile</p>
        </div>
      )}
    </div>
  )
}
