/**
 * FlowMap - dark-canvas entity connection graph.
 * D3 force simulation, curved bezier edges, vivid sector colors, SVG glow filters.
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import * as d3 from 'd3'
import { formatAmount } from '../lib/format'

// ---- Design tokens ---------------------------------------------------------------

const SECTOR_COLOR = {
  Technology:   '#818cf8',
  Finance:      '#60a5fa',
  'E-Commerce': '#22d3ee',
  Energy:       '#fbbf24',
  Healthcare:   '#34d399',
  Defense:      '#f87171',
  Aerospace:    '#c084fc',
  Retail:       '#f472b6',
  Automotive:   '#fb923c',
  Government:   '#94a3b8',
}

const SECTORS = Object.keys(SECTOR_COLOR)

const EDGE_META = {
  board:               { stroke: '#e2e8f0', dash: 'none',    label: 'Board / Control'    },
  investment:          { stroke: '#60a5fa', dash: 'none',    label: 'Investment'          },
  acquisition:         { stroke: '#a78bfa', dash: 'none',    label: 'Acquisition'         },
  partner:             { stroke: '#34d399', dash: '6,3',     label: 'Partnership'         },
  competitor:          { stroke: '#f87171', dash: '3,3',     label: 'Competitor'          },
  customer:            { stroke: '#fbbf24', dash: '8,4',     label: 'Customer'            },
  supplier:            { stroke: '#fb923c', dash: '8,4',     label: 'Supplier'            },
  political_trade:     { stroke: '#f472b6', dash: '4,2,1,2', label: 'Political Trade'     },
  political:           { stroke: '#94a3b8', dash: '4,2',     label: 'Political'           },
  congressional_trade: { stroke: '#f472b6', dash: '4,2,1,2', label: 'Congressional Trade' },
  investor:            { stroke: '#60a5fa', dash: 'none',    label: 'Investment'          },
  subsidiary:          { stroke: '#a78bfa', dash: 'none',    label: 'Subsidiary'          },
}

function edgeMeta(type) {
  return EDGE_META[type] || { stroke: '#475569', dash: '4,2', label: type || 'Linked' }
}

function bezierPath(sx, sy, tx, ty) {
  const dx = tx - sx
  const dy = ty - sy
  const mx = (sx + tx) / 2 - dy * 0.18
  const my = (sy + ty) / 2 + dx * 0.18
  return `M${sx},${sy} Q${mx},${my} ${tx},${ty}`
}

// ---- Panel sub-components --------------------------------------------------------

function PanelSection({ title, children }) {
  return (
    <div className="px-5 py-4 border-b border-[#f0f0f0]">
      <p className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#bbb] mb-3">{title}</p>
      {children}
    </div>
  )
}

// ---- Main component --------------------------------------------------------------

export default function FlowMap() {
  const svgRef   = useRef(null)
  const wrapRef  = useRef(null)
  const simRef   = useRef(null)
  const zoomRef  = useRef(null)
  const navigate = useNavigate()

  const [data,             setData]            = useState(null)
  const [loading,          setLoading]         = useState(true)
  const [error,            setError]           = useState(null)
  const [sectorFilter,     setSectorFilter]    = useState('')
  const [typeFilter,       setTypeFilter]      = useState('')
  const [selectedNode,     setSelectedNode]    = useState(null)
  const [searchTerm,       setSearchTerm]      = useState('')
  const [edgeTooltip,      setEdgeTooltip]     = useState(null)
  const [portfolio,        setPortfolio]       = useState(null)
  const [portfolioLoading, setPortfolioLoading] = useState(false)

  useEffect(() => {
    if (!selectedNode) { setPortfolio(null); return }
    setPortfolioLoading(true)
    fetch(`/entities/${selectedNode.id}/portfolio`)
      .then(r => r.json())
      .then(d => setPortfolio(d))
      .catch(() => setPortfolio(null))
      .finally(() => setPortfolioLoading(false))
  }, [selectedNode])

  const fetchFlow = useCallback(() => {
    setLoading(true)
    const qs = new URLSearchParams()
    if (sectorFilter) qs.set('sector', sectorFilter)
    if (typeFilter)   qs.set('type', typeFilter)
    fetch(`/flow${qs.toString() ? '?' + qs : ''}`)
      .then(r => r.json())
      .then(d => { setData(d); setError(null) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [sectorFilter, typeFilter])

  useEffect(() => { fetchFlow() }, [fetchFlow])
  useEffect(() => { setSelectedNode(null); setSearchTerm('') }, [sectorFilter, typeFilter])

  function handleResetZoom() {
    if (!svgRef.current || !zoomRef.current) return
    d3.select(svgRef.current)
      .transition().duration(500)
      .call(zoomRef.current.transform, d3.zoomIdentity)
  }

  // ---- D3 render -----------------------------------------------------------------
  useEffect(() => {
    if (!data || loading || !svgRef.current || !wrapRef.current) return

    const { nodes: rawNodes, edges: rawEdges } = data
    const rect = wrapRef.current.getBoundingClientRect()
    const w = (rect.width  > 0 ? rect.width  : 1000)
    const h = (rect.height > 0 ? rect.height : 600)

    const nodes = rawNodes.map(n => ({ ...n }))
    const nodeIds = new Set(nodes.map(n => n.id))
    const edges = rawEdges
      .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map(e => ({ ...e }))

    const adjacency = {}
    const edgesByNode = {}
    nodes.forEach(n => { adjacency[n.id] = new Set(); edgesByNode[n.id] = [] })
    edges.forEach((e, i) => {
      const sid = typeof e.source === 'object' ? e.source.id : e.source
      const tid = typeof e.target === 'object' ? e.target.id : e.target
      adjacency[sid]?.add(tid)
      adjacency[tid]?.add(sid)
      edgesByNode[sid]?.push(i)
      edgesByNode[tid]?.push(i)
    })

    // SVG setup
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()
    svg.attr('viewBox', `0 0 ${w} ${h}`)

    // Glow filter defs
    const defs = svg.append('defs')
    ;[['glow-soft', 3], ['glow-strong', 8]].forEach(([id, dev]) => {
      const f = defs.append('filter')
        .attr('id', id)
        .attr('x', '-60%').attr('y', '-60%')
        .attr('width', '220%').attr('height', '220%')
      f.append('feGaussianBlur').attr('stdDeviation', dev).attr('result', 'blur')
      const merge = f.append('feMerge')
      merge.append('feMergeNode').attr('in', 'blur')
      merge.append('feMergeNode').attr('in', 'SourceGraphic')
    })

    // Zoom + pan
    const g = svg.append('g')
    const zoom = d3.zoom()
      .scaleExtent([0.1, 8])
      .on('zoom', ({ transform }) => g.attr('transform', transform))
    svg.call(zoom)
    zoomRef.current = zoom
    svg.on('click', ev => { if (ev.target === svgRef.current) setSelectedNode(null) })

    const maxWorth = d3.max(nodes, d => d.net_worth || 0) || 1
    const rScale = d3.scaleSqrt().domain([0, maxWorth]).range([7, 32])

    // Edges
    const edgeGroup = g.append('g').attr('class', 'edges')
    const edgeSel = edgeGroup.selectAll('path.fl-edge')
      .data(edges)
      .join('path')
      .attr('class', 'fl-edge')
      .attr('fill', 'none')
      .attr('stroke', d => edgeMeta(d.type).stroke)
      .attr('stroke-width', d => Math.max(0.8, (d.weight || 1) * 0.65))
      .attr('stroke-dasharray', d => {
        const dash = edgeMeta(d.type).dash
        return dash === 'none' ? null : dash
      })
      .attr('opacity', 0.28)
      .attr('cursor', 'crosshair')
      .on('mouseenter', function(event, d) {
        d3.select(this).attr('opacity', 1).attr('stroke-width', 2)
        setEdgeTooltip({ label: d.label, type: d.type, confidence: d.confidence, x: event.pageX, y: event.pageY })
      })
      .on('mousemove', ev => setEdgeTooltip(t => t ? { ...t, x: ev.pageX, y: ev.pageY } : t))
      .on('mouseleave', function(event, d) {
        d3.select(this)
          .attr('opacity', 0.28)
          .attr('stroke-width', Math.max(0.8, (d.weight || 1) * 0.65))
        setEdgeTooltip(null)
      })

    // Nodes
    const nodeGroup = g.append('g').attr('class', 'nodes')
    const nodeSel = nodeGroup.selectAll('g.fl-node')
      .data(nodes)
      .join('g')
      .attr('class', 'fl-node')
      .attr('cursor', 'pointer')
      .call(d3.drag()
        .on('start', (ev, d) => {
          if (!ev.active) simRef.current?.alphaTarget(0.3).restart()
          d.fx = d.x; d.fy = d.y
        })
        .on('drag',  (ev, d) => { d.fx = ev.x; d.fy = ev.y })
        .on('end',   (ev, d) => {
          if (!ev.active) simRef.current?.alphaTarget(0)
          d.fx = null; d.fy = null
        })
      )
      .on('click', (ev, d) => {
        ev.stopPropagation()
        setSelectedNode(prev => prev?.id === d.id ? null : d)
      })
      .on('dblclick', (ev, d) => {
        ev.stopPropagation()
        navigate(`/entities/${d.id}`)
      })

    // Halo (ambient glow ring)
    nodeSel.append('circle').attr('class', 'node-halo')
      .attr('r', d => rScale(d.net_worth || 0) + 10)
      .attr('fill', d => SECTOR_COLOR[d.sector] || '#818cf8')
      .attr('opacity', 0.07)
      .attr('pointer-events', 'none')

    // Main filled circle
    nodeSel.append('circle').attr('class', 'node-circle')
      .attr('r', d => rScale(d.net_worth || 0))
      .attr('fill', d => SECTOR_COLOR[d.sector] || '#818cf8')
      .attr('stroke', '#0d1117')
      .attr('stroke-width', 1.5)
      .attr('filter', 'url(#glow-soft)')

    // Pulse ring (shown + animated on selection)
    nodeSel.append('circle').attr('class', 'node-ring')
      .attr('r', d => rScale(d.net_worth || 0) + 6)
      .attr('fill', 'none')
      .attr('stroke', d => SECTOR_COLOR[d.sector] || '#818cf8')
      .attr('stroke-width', 1.5)
      .attr('opacity', 0)
      .attr('pointer-events', 'none')

    // External label
    nodeSel.append('text').attr('class', 'node-label')
      .text(d => {
        const r = rScale(d.net_worth || 0)
        const words = d.name.split(' ')
        if (r > 20) return words.slice(0, 2).join(' ')
        if (r > 11) return words[0].slice(0, 7)
        return ''
      })
      .attr('text-anchor', 'middle')
      .attr('dy', d => rScale(d.net_worth || 0) + 14)
      .attr('font-size', 8.5)
      .attr('font-family', '"IBM Plex Mono", "Courier New", monospace')
      .attr('fill', '#64748b')
      .attr('letter-spacing', '0.03em')
      .attr('pointer-events', 'none')

    // Force simulation
    const sim = d3.forceSimulation(nodes)
      .force('link',    d3.forceLink(edges).id(d => d.id)
        .distance(d => 95 + (5 - (d.weight || 2)) * 20)
        .strength(0.18))
      .force('charge',  d3.forceManyBody().strength(d => -170 - rScale(d.net_worth || 0) * 3.5))
      .force('center',  d3.forceCenter(w / 2, h / 2))
      .force('collide', d3.forceCollide(d => rScale(d.net_worth || 0) + 14))
      .on('tick', () => {
        edgeSel.attr('d', d => bezierPath(
          d.source.x || 0, d.source.y || 0,
          d.target.x || 0, d.target.y || 0,
        ))
        nodeSel.attr('transform', d => `translate(${d.x || 0},${d.y || 0})`)
      })
    simRef.current = sim

    // Store refs for reactive highlight effect
    svgRef.current.__edgeSel     = edgeSel
    svgRef.current.__nodeSel     = nodeSel
    svgRef.current.__adjacency   = adjacency
    svgRef.current.__edgesByNode = edgesByNode
    svgRef.current.__edges       = edges
    svgRef.current.__rScale      = rScale

    return () => sim.stop()
  }, [data, loading, navigate]) // eslint-disable-line

  // ---- Highlight / spotlight effect -----------------------------------------------
  useEffect(() => {
    if (!svgRef.current) return
    const edgeSel     = svgRef.current.__edgeSel
    const nodeSel     = svgRef.current.__nodeSel
    const adjacency   = svgRef.current.__adjacency
    const edgesByNode = svgRef.current.__edgesByNode
    if (!edgeSel || !nodeSel) return

    const connectedIds      = selectedNode ? (adjacency[selectedNode.id] || new Set()) : new Set()
    const connectedEdgeIdxs = selectedNode ? new Set(edgesByNode[selectedNode.id] || []) : new Set()
    const hasSearch = searchTerm.trim().length > 0
    const lc = searchTerm.trim().toLowerCase()

    nodeSel.select('.node-circle')
      .attr('opacity', d => {
        if (hasSearch) return d.name.toLowerCase().includes(lc) ? 1 : 0.06
        if (!selectedNode) return 1
        return (d.id === selectedNode.id || connectedIds.has(d.id)) ? 1 : 0.1
      })
      .attr('filter', d =>
        d.id === selectedNode?.id ? 'url(#glow-strong)' : 'url(#glow-soft)'
      )

    nodeSel.select('.node-halo')
      .attr('opacity', d => {
        if (hasSearch) return d.name.toLowerCase().includes(lc) ? 0.2 : 0.02
        if (!selectedNode) return 0.07
        return (d.id === selectedNode.id || connectedIds.has(d.id)) ? 0.2 : 0.02
      })

    nodeSel.select('.node-label')
      .attr('opacity', d => {
        if (hasSearch) return d.name.toLowerCase().includes(lc) ? 1 : 0.08
        if (!selectedNode) return 0.75
        return (d.id === selectedNode.id || connectedIds.has(d.id)) ? 1 : 0.07
      })
      .attr('fill', d => {
        if (d.id === selectedNode?.id) return '#e2e8f0'
        return '#64748b'
      })

    nodeSel.select('.node-ring')
      .attr('opacity', d => d.id === selectedNode?.id ? 0.85 : 0)
      .each(function(d) {
        d3.select(this).classed('is-pulsing', d.id === selectedNode?.id)
      })

    edgeSel
      .attr('opacity', (d, i) => {
        if (hasSearch) return 0.06
        if (!selectedNode) return 0.28
        return connectedEdgeIdxs.has(i) ? 0.9 : 0.04
      })
      .attr('stroke-width', (d, i) => {
        if (hasSearch || !selectedNode) return Math.max(0.8, (d.weight || 1) * 0.65)
        return connectedEdgeIdxs.has(i) ? Math.max(1.5, (d.weight || 1)) : 0.5
      })
  }, [selectedNode, searchTerm])

  const connectedEdges = selectedNode && svgRef.current?.__edges
    ? svgRef.current.__edges.filter((_, i) =>
        (svgRef.current.__edgesByNode[selectedNode.id] || []).includes(i)
      )
    : []

  const uniqueEdgeTypes = Object.entries(EDGE_META)
    .filter(([, s], i, arr) => arr.findIndex(([, x]) => x.label === s.label) === i)

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* Pulse animation style */}
      <style>{`
        @keyframes cl-pulse {
          0%   { transform: scale(1);   opacity: 0.75; }
          100% { transform: scale(2.4); opacity: 0;    }
        }
        .node-ring.is-pulsing {
          animation: cl-pulse 2s ease-out infinite;
          transform-box: fill-box;
          transform-origin: center;
        }
      `}</style>

      {/* ---- Dark header -------------------------------------------------------- */}
      <div className="flex items-center gap-2.5 px-4 h-11 bg-[#0d1117] border-b border-[#1e293b] flex-shrink-0">

        {/* Logo + title */}
        <div className="flex items-center gap-2 mr-1 flex-shrink-0">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="3"  cy="3"  r="2.2" stroke="#818cf8" strokeWidth="1.2"/>
            <circle cx="11" cy="3"  r="2.2" stroke="#60a5fa" strokeWidth="1.2"/>
            <circle cx="7"  cy="11" r="2.2" stroke="#34d399" strokeWidth="1.2"/>
            <line x1="5" y1="3"   x2="9"   y2="3"   stroke="#334155" strokeWidth="0.9"/>
            <line x1="4" y1="4.5" x2="6.3" y2="9"   stroke="#334155" strokeWidth="0.9"/>
            <line x1="10" y1="4.5" x2="7.7" y2="9"  stroke="#334155" strokeWidth="0.9"/>
          </svg>
          <span className="text-[11px] font-bold uppercase tracking-[0.1em] text-[#e2e8f0]">
            Connection Map
          </span>
        </div>

        {/* Stats pill */}
        {data && (
          <div className="hidden sm:flex items-center gap-2.5 px-2.5 py-1 bg-[#1e293b] flex-shrink-0">
            <span className="text-[9px] font-mono text-[#64748b]">
              <span className="text-[#94a3b8] font-bold">{data.nodes.length}</span> nodes
            </span>
            <span className="w-px h-3 bg-[#2d3f56]" />
            <span className="text-[9px] font-mono text-[#64748b]">
              <span className="text-[#94a3b8] font-bold">{data.edges.length}</span> edges
            </span>
          </div>
        )}

        <div className="flex-1" />

        {/* Spotlight search */}
        <div className="relative flex-shrink-0">
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none"
            className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-[#475569]">
            <circle cx="4.5" cy="4.5" r="3" stroke="currentColor" strokeWidth="1.2"/>
            <line x1="7" y1="7" x2="10" y2="10" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
          </svg>
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder="Spotlight..."
            className="pl-7 pr-3 py-1.5 w-36 text-[11px] bg-[#1e293b] text-[#e2e8f0] placeholder-[#475569] border border-[#2d3f56] focus:border-[#818cf8] focus:outline-none transition-colors"
          />
        </div>

        {/* Sector filter */}
        <select
          value={sectorFilter}
          onChange={e => setSectorFilter(e.target.value)}
          className="px-2.5 py-1.5 text-[10px] font-medium uppercase tracking-[0.05em] bg-[#1e293b] text-[#94a3b8] border border-[#2d3f56] focus:border-[#818cf8] focus:outline-none cursor-pointer"
        >
          <option value="">All Sectors</option>
          {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        {/* Type filter */}
        <select
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
          className="px-2.5 py-1.5 text-[10px] font-medium uppercase tracking-[0.05em] bg-[#1e293b] text-[#94a3b8] border border-[#2d3f56] focus:border-[#818cf8] focus:outline-none cursor-pointer"
        >
          <option value="">All Types</option>
          <option value="company">Companies</option>
          <option value="individual">People</option>
        </select>

        {/* Reset zoom */}
        <button
          onClick={handleResetZoom}
          title="Reset zoom"
          className="flex items-center justify-center w-7 h-7 bg-[#1e293b] border border-[#2d3f56] hover:border-[#818cf8] text-[#64748b] hover:text-[#818cf8] transition-colors flex-shrink-0"
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M1 4V1h3M11 4V1H8M1 8v3h3M11 8v3H8"
              stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>

      {/* ---- Main area ---------------------------------------------------------- */}
      <div className="flex flex-1 overflow-hidden">

        {/* Canvas */}
        <div
          ref={wrapRef}
          className="relative flex-1 overflow-hidden"
          style={{
            background: '#0d1117',
            backgroundImage: 'radial-gradient(circle, #1e293b 1px, transparent 1px)',
            backgroundSize: '28px 28px',
          }}
        >
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="w-48 h-px bg-[#1e293b] relative overflow-hidden mb-4">
                  <div className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-[#818cf8] to-transparent animate-scan" />
                </div>
                <p className="text-[9px] font-mono uppercase tracking-[0.14em] text-[#475569]">
                  Mapping connections
                </p>
              </div>
            </div>
          )}

          {error && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <p className="text-[10px] font-mono text-[#f87171] uppercase tracking-wider mb-1">
                  Connection Error
                </p>
                <p className="text-[9px] text-[#475569]">Start uvicorn on port 8000</p>
              </div>
            </div>
          )}

          <svg ref={svgRef} className="w-full h-full" />

          {!loading && data && (
            <p className="absolute bottom-3 left-1/2 -translate-x-1/2 text-[9px] font-mono uppercase tracking-[0.1em] text-[#1e293b] pointer-events-none select-none whitespace-nowrap">
              scroll to zoom &middot; drag nodes &middot; click to explore &middot; dbl-click for profile
            </p>
          )}
        </div>

        {/* ---- Right panel ---------------------------------------------------- */}
        <div className="w-72 border-l border-[#e8e8e8] bg-white flex flex-col overflow-hidden flex-shrink-0">

          {selectedNode ? (

            /* Selected node panel */
            <div className="flex flex-col overflow-y-auto h-full">

              {/* Entity header */}
              <div className="px-5 pt-5 pb-4 border-b border-[#f0f0f0]">
                <div className="flex items-start gap-3">
                  {/* Sector dot with glow */}
                  <div
                    className="w-3 h-3 rounded-full flex-shrink-0 mt-1"
                    style={{
                      background: SECTOR_COLOR[selectedNode.sector] || '#94a3b8',
                      boxShadow: `0 0 10px ${SECTOR_COLOR[selectedNode.sector] || '#94a3b8'}99`,
                    }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-bold text-[#111] leading-snug tracking-tight">
                      {selectedNode.name}
                    </p>
                    <p className="text-[9px] font-semibold uppercase tracking-[0.07em] text-[#aaa] mt-0.5">
                      {selectedNode.type} &middot; {selectedNode.sector}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="text-[#ccc] hover:text-[#111] transition-colors flex-shrink-0 text-lg leading-none mt-0.5"
                  >
                    &times;
                  </button>
                </div>

                {selectedNode.net_worth > 0 && (
                  <p className="font-mono text-xs font-bold text-[#111] mt-3">
                    {formatAmount(selectedNode.net_worth)}
                  </p>
                )}
                {selectedNode.description && (
                  <p className="text-[10px] text-[#777] font-light mt-2 leading-relaxed line-clamp-3">
                    {selectedNode.description}
                  </p>
                )}
              </div>

              {/* Portfolio loading */}
              {portfolioLoading && (
                <div className="px-5 py-4 border-b border-[#f0f0f0]">
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-px bg-[#f0f0f0] relative overflow-hidden">
                      <div className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-[#ddd] to-transparent animate-scan" />
                    </div>
                    <p className="text-[9px] uppercase tracking-[0.1em] text-[#ccc]">Loading...</p>
                  </div>
                </div>
              )}

              {portfolio && !portfolioLoading && (
                <>
                  {/* Investment lean with colored bars */}
                  {portfolio.sector_exposure?.length > 0 && (
                    <PanelSection title="Investment Lean">
                      <div className="space-y-2">
                        {(() => {
                          const max = Math.max(...portfolio.sector_exposure.map(s => s.count), 1)
                          return portfolio.sector_exposure.slice(0, 6).map(s => (
                            <div key={s.sector}>
                              <div className="flex justify-between items-center mb-1">
                                <span className="text-[9px] font-medium uppercase tracking-[0.05em] text-[#555]">
                                  {s.sector}
                                </span>
                                <span className="text-[9px] font-mono text-[#999]">{s.count}</span>
                              </div>
                              <div className="h-0.5 bg-[#f0f0f0] w-full rounded-full overflow-hidden">
                                <div
                                  className="h-full rounded-full transition-all duration-500"
                                  style={{
                                    width: `${(s.count / max) * 100}%`,
                                    background: SECTOR_COLOR[s.sector] || '#818cf8',
                                  }}
                                />
                              </div>
                            </div>
                          ))
                        })()}
                      </div>
                    </PanelSection>
                  )}

                  {/* Activity mix */}
                  {portfolio.event_breakdown?.length > 0 && (
                    <PanelSection title="Activity Mix">
                      <div className="space-y-1.5">
                        {portfolio.event_breakdown.slice(0, 5).map(e => (
                          <div key={e.event_type} className="flex justify-between items-center">
                            <span className="text-[9px] font-medium uppercase tracking-[0.05em] text-[#555]">
                              {e.event_type.replace(/_/g, ' ')}
                            </span>
                            <span className="text-[9px] font-mono font-bold text-[#111]">{e.count}</span>
                          </div>
                        ))}
                        {portfolio.total_capital_tracked > 0 && (
                          <div className="pt-1.5 mt-0.5 border-t border-[#f5f5f5] flex justify-between items-center">
                            <span className="text-[9px] font-medium uppercase tracking-[0.05em] text-[#aaa]">
                              Capital Tracked
                            </span>
                            <span className="text-[9px] font-mono font-bold text-[#111]">
                              {formatAmount(portfolio.total_capital_tracked)}
                            </span>
                          </div>
                        )}
                      </div>
                    </PanelSection>
                  )}

                  {/* Congress trades */}
                  {portfolio.congressional_trades?.total > 0 && (
                    <PanelSection title="Congress Trades">
                      <div className="flex gap-2">
                        <div className="flex-1 border border-[#f0f0f0] p-2.5 text-center">
                          <p className="text-sm font-bold text-[#111] font-mono">
                            {portfolio.congressional_trades.buys}
                          </p>
                          <p className="text-[8px] uppercase tracking-[0.08em] text-[#22c55e] mt-0.5">Buys</p>
                        </div>
                        <div className="flex-1 border border-[#f0f0f0] p-2.5 text-center">
                          <p className="text-sm font-bold text-[#111] font-mono">
                            {portfolio.congressional_trades.sells}
                          </p>
                          <p className="text-[8px] uppercase tracking-[0.08em] text-[#ef4444] mt-0.5">Sells</p>
                        </div>
                      </div>
                    </PanelSection>
                  )}

                  {/* Largest moves */}
                  {portfolio.top_events?.length > 0 && (
                    <PanelSection title="Largest Moves">
                      <div className="space-y-2.5">
                        {portfolio.top_events.map((ev, i) => (
                          <div key={i} className="flex items-start gap-2">
                            <span className="text-[9px] font-mono font-bold text-[#111] flex-shrink-0 mt-0.5">
                              {formatAmount(ev.amount)}
                            </span>
                            <span className="text-[9px] text-[#666] leading-tight line-clamp-2">
                              {ev.headline}
                            </span>
                          </div>
                        ))}
                      </div>
                    </PanelSection>
                  )}
                </>
              )}

              {/* Connections */}
              {connectedEdges.length > 0 && (
                <PanelSection title={`${connectedEdges.length} Connection${connectedEdges.length !== 1 ? 's' : ''}`}>
                  <div className="space-y-2.5">
                    {connectedEdges.slice(0, 8).map((edge, i) => {
                      const sid = typeof edge.source === 'object' ? edge.source.id : edge.source
                      const tid = typeof edge.target === 'object' ? edge.target.id : edge.target
                      const otherId = sid === selectedNode.id ? tid : sid
                      const other = data.nodes.find(n => n.id === otherId)
                      const meta = edgeMeta(edge.type)
                      return (
                        <div key={i} className="flex items-start gap-2">
                          <span
                            className="flex-shrink-0 w-1.5 h-1.5 rounded-full mt-1.5"
                            style={{ background: meta.stroke }}
                          />
                          <div className="min-w-0">
                            <p className="text-[10px] font-semibold text-[#111] truncate">
                              {other?.name || 'Unknown'}
                            </p>
                            <p className="text-[9px] text-[#999]">{edge.label || meta.label}</p>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </PanelSection>
              )}

              {/* CTA */}
              <div className="px-5 py-4 mt-auto border-t border-[#f0f0f0]">
                <button
                  onClick={() => navigate(`/entities/${selectedNode.id}`)}
                  className="w-full py-2.5 text-[10px] font-semibold uppercase tracking-[0.1em] border border-[#111] text-[#111] hover:bg-[#111] hover:text-white transition-all duration-200"
                >
                  View Full Profile
                </button>
              </div>
            </div>

          ) : (

            /* Legend / idle state */
            <div className="flex flex-col overflow-y-auto h-full">

              {/* Panel intro */}
              <div className="px-5 pt-5 pb-4 border-b border-[#f0f0f0]">
                <p className="text-[9px] font-bold uppercase tracking-[0.1em] text-[#bbb] mb-1">
                  Intelligence Layer
                </p>
                <p className="text-sm font-bold text-[#111] tracking-tight">Connection Map</p>
                {data && (
                  <p className="text-[10px] text-[#aaa] font-light mt-1">
                    {data.nodes.length} entities &middot; {data.edges.length} connections
                  </p>
                )}
                <p className="text-[9px] text-[#bbb] mt-3 leading-relaxed">
                  Click any node to explore its network. Double-click to open a full profile.
                </p>
              </div>

              {/* Sector legend */}
              <PanelSection title="Sectors">
                <div className="space-y-1.5">
                  {Object.entries(SECTOR_COLOR).map(([sector, color]) => (
                    <div key={sector} className="flex items-center gap-2.5">
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: color, boxShadow: `0 0 5px ${color}99` }}
                      />
                      <span className="text-[9px] font-medium uppercase tracking-[0.05em] text-[#555]">
                        {sector}
                      </span>
                    </div>
                  ))}
                </div>
              </PanelSection>

              {/* Edge type legend */}
              <PanelSection title="Connection Types">
                <div className="space-y-2">
                  {uniqueEdgeTypes.map(([type, meta]) => (
                    <div key={type} className="flex items-center gap-2.5">
                      <svg width="22" height="10" className="flex-shrink-0">
                        <line x1="0" y1="5" x2="22" y2="5"
                          stroke={meta.stroke}
                          strokeWidth="1.5"
                          strokeDasharray={meta.dash === 'none' ? undefined : meta.dash}
                        />
                      </svg>
                      <span className="text-[9px] font-medium uppercase tracking-[0.05em] text-[#555]">
                        {meta.label}
                      </span>
                    </div>
                  ))}
                </div>
              </PanelSection>

              {/* Tips */}
              <PanelSection title="How to use">
                <div className="space-y-2">
                  {[
                    ['Spotlight', 'Type to isolate matching nodes'],
                    ['Select',    'Click node to dim unrelated'],
                    ['Profile',   'Double-click to open detail view'],
                    ['Pin',       'Drag any node to anchor it'],
                    ['Zoom',      'Scroll or pinch the canvas'],
                    ['Reset',     'Use the icon in the toolbar'],
                  ].map(([key, val]) => (
                    <div key={key} className="flex items-start gap-2">
                      <span className="text-[9px] font-bold uppercase tracking-[0.07em] text-[#ccc] flex-shrink-0 w-14">
                        {key}
                      </span>
                      <span className="text-[9px] text-[#999]">{val}</span>
                    </div>
                  ))}
                </div>
              </PanelSection>

            </div>
          )}
        </div>
      </div>

      {/* Edge tooltip */}
      {edgeTooltip && (
        <div
          className="fixed z-50 bg-[#0d1117] border border-[#1e293b] px-3 py-2 pointer-events-none"
          style={{ left: edgeTooltip.x + 12, top: edgeTooltip.y - 48 }}
        >
          <p
            className="text-[9px] font-bold uppercase tracking-[0.08em]"
            style={{ color: edgeMeta(edgeTooltip.type).stroke }}
          >
            {edgeMeta(edgeTooltip.type).label}
          </p>
          {edgeTooltip.label && (
            <p className="text-[10px] text-[#94a3b8] mt-0.5">{edgeTooltip.label}</p>
          )}
          {edgeTooltip.confidence && (
            <div className="flex items-center gap-1 mt-1.5">
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{
                  background: edgeTooltip.confidence === 'high' ? '#22c55e'
                    : edgeTooltip.confidence === 'medium' ? '#f59e0b' : '#64748b',
                }}
              />
              <span className="text-[8px] uppercase tracking-wider"
                style={{
                  color: edgeTooltip.confidence === 'high' ? '#22c55e'
                    : edgeTooltip.confidence === 'medium' ? '#f59e0b' : '#64748b',
                }}>
                {edgeTooltip.confidence} confidence
              </span>
            </div>
          )}
        </div>
      )}

    </div>
  )
}
