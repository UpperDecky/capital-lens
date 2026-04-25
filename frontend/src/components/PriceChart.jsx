import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

const MARGIN = { top: 10, right: 12, bottom: 24, left: 48 }

export default function PriceChart({ data, height = 140 }) {
  const svgRef = useRef(null)

  useEffect(() => {
    if (!data?.points?.length) return
    const container = svgRef.current
    if (!container) return

    const W = container.clientWidth || 600
    const H = height
    const iW = W - MARGIN.left - MARGIN.right
    const iH = H - MARGIN.top - MARGIN.bottom

    // Parse dates + prices
    const parseDate = d3.timeParse('%Y-%m-%d')
    const points = data.points.map(p => ({ date: parseDate(p.date), close: p.close }))

    const xScale = d3.scaleTime()
      .domain(d3.extent(points, d => d.date))
      .range([0, iW])

    const [minClose, maxClose] = d3.extent(points, d => d.close)
    const pad = (maxClose - minClose) * 0.08
    const yScale = d3.scaleLinear()
      .domain([minClose - pad, maxClose + pad])
      .range([iH, 0])

    // Determine overall trend color
    const first = points[0].close
    const last  = points[points.length - 1].close
    const trendColor = last >= first ? '#27ae60' : '#e74c3c'

    // Line + area generators
    const line = d3.line()
      .x(d => xScale(d.date))
      .y(d => yScale(d.close))
      .curve(d3.curveMonotoneX)

    const area = d3.area()
      .x(d => xScale(d.date))
      .y0(iH)
      .y1(d => yScale(d.close))
      .curve(d3.curveMonotoneX)

    // Wipe and redraw
    d3.select(container).selectAll('*').remove()

    const svg = d3.select(container)
      .attr('width', W)
      .attr('height', H)

    const g = svg.append('g')
      .attr('transform', `translate(${MARGIN.left},${MARGIN.top})`)

    // Defs: area gradient
    const gradId = `chart-grad-${data.ticker}`
    const defs = svg.append('defs')
    const grad = defs.append('linearGradient')
      .attr('id', gradId)
      .attr('x1', '0').attr('y1', '0')
      .attr('x2', '0').attr('y2', '1')
    grad.append('stop').attr('offset', '0%').attr('stop-color', trendColor).attr('stop-opacity', 0.18)
    grad.append('stop').attr('offset', '100%').attr('stop-color', trendColor).attr('stop-opacity', 0)

    // Grid lines (horizontal only, subtle)
    const yTicks = yScale.ticks(4)
    g.append('g').attr('class', 'grid')
      .selectAll('line')
      .data(yTicks)
      .join('line')
      .attr('x1', 0).attr('x2', iW)
      .attr('y1', d => yScale(d)).attr('y2', d => yScale(d))
      .attr('stroke', '#f0f0f0')
      .attr('stroke-width', 1)

    // Area fill
    g.append('path')
      .datum(points)
      .attr('fill', `url(#${gradId})`)
      .attr('d', area)

    // Price line
    g.append('path')
      .datum(points)
      .attr('fill', 'none')
      .attr('stroke', trendColor)
      .attr('stroke-width', 1.5)
      .attr('d', line)

    // X axis (dates — sparse labels)
    const xAxis = d3.axisBottom(xScale)
      .ticks(5)
      .tickFormat(d3.timeFormat('%b %d'))
      .tickSize(3)
    g.append('g')
      .attr('transform', `translate(0,${iH})`)
      .call(xAxis)
      .call(ax => ax.select('.domain').remove())
      .call(ax => ax.selectAll('line').attr('stroke', '#e0e0e0'))
      .call(ax => ax.selectAll('text')
        .attr('font-size', 9)
        .attr('fill', '#bbb')
        .attr('font-family', 'inherit'))

    // Y axis (price labels)
    const yAxis = d3.axisLeft(yScale)
      .ticks(4)
      .tickFormat(v => `$${v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v.toFixed(2)}`)
      .tickSize(3)
    g.append('g')
      .call(yAxis)
      .call(ax => ax.select('.domain').remove())
      .call(ax => ax.selectAll('line').attr('stroke', '#e0e0e0'))
      .call(ax => ax.selectAll('text')
        .attr('font-size', 9)
        .attr('fill', '#bbb')
        .attr('font-family', 'inherit'))

    // Hover overlay
    const tooltipEl = d3.select(container.parentNode).select('.chart-tooltip')

    const bisect = d3.bisector(d => d.date).left
    const focusLine = g.append('line')
      .attr('stroke', '#bbb')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '3,3')
      .attr('y1', 0).attr('y2', iH)
      .style('opacity', 0)

    const focusDot = g.append('circle')
      .attr('r', 3.5)
      .attr('fill', trendColor)
      .attr('stroke', 'white')
      .attr('stroke-width', 1.5)
      .style('opacity', 0)

    g.append('rect')
      .attr('width', iW).attr('height', iH)
      .attr('fill', 'none')
      .attr('pointer-events', 'all')
      .on('mousemove', (event) => {
        const [mx] = d3.pointer(event)
        const date = xScale.invert(mx)
        const idx = Math.max(0, bisect(points, date, 1) - 1)
        const p = points[idx]
        if (!p) return
        const x = xScale(p.date)
        const y = yScale(p.close)
        focusLine.attr('x1', x).attr('x2', x).style('opacity', 1)
        focusDot.attr('cx', x).attr('cy', y).style('opacity', 1)

        const fmt = d3.timeFormat('%b %d, %Y')
        tooltipEl
          .style('display', 'block')
          .style('left', `${MARGIN.left + x}px`)
          .style('top', `${MARGIN.top + y - 36}px`)
          .html(`<span style="font-weight:600;color:#111">$${p.close.toFixed(2)}</span>
                 <span style="color:#999;font-size:9px;margin-left:4px">${fmt(p.date)}</span>`)
      })
      .on('mouseleave', () => {
        focusLine.style('opacity', 0)
        focusDot.style('opacity', 0)
        tooltipEl.style('display', 'none')
      })
  }, [data, height])

  if (!data?.points?.length) return null

  const first = data.points[0]?.close
  const last  = data.points[data.points.length - 1]?.close
  const pct   = first ? ((last - first) / first * 100) : 0
  const up    = pct >= 0

  return (
    <div className="relative w-full">
      {/* % badge */}
      <div className="absolute top-2 right-2 z-10 flex items-center gap-1.5">
        <span
          className="text-[10px] font-mono font-bold px-1.5 py-0.5 border"
          style={{
            color: up ? '#27ae60' : '#e74c3c',
            borderColor: up ? '#27ae60' : '#e74c3c',
            background: up ? 'rgba(39,174,96,0.06)' : 'rgba(231,76,60,0.06)',
          }}
        >
          {up ? '+' : ''}{pct.toFixed(2)}%
        </span>
        <span className="text-[9px] text-[#bbb] font-mono">{data.ticker}</span>
      </div>

      {/* Tooltip */}
      <div
        className="chart-tooltip pointer-events-none absolute z-20 bg-white border border-[#e0e0e0] px-2 py-1 text-[10px] font-mono shadow-sm"
        style={{ display: 'none', transform: 'translateX(-50%)' }}
      />

      <svg ref={svgRef} className="w-full block" style={{ height }} />
    </div>
  )
}
