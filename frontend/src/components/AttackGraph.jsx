import { useRef, useEffect, useState, useCallback } from 'react'
import * as d3 from 'd3'
import { motion, AnimatePresence } from 'framer-motion'
import { X, AlertTriangle, RefreshCw, ZoomIn, ZoomOut, Maximize2, Crosshair, ChevronRight, Target } from 'lucide-react'

// Attack-path severity → colour (red-team palette)
const PATH_SEV_COLOR = {
  critical: '#FF2020',
  high:     '#F04343',
  medium:   '#F5C842',
  low:      '#FFAA33',
}

// ── Color & sizing constants (red-team palette) ─────────────────────────────
const TYPE_COLOR = {
  Engagement:    '#CC0000',
  Domain:        '#FFAA33',
  IPAddress:     '#FF5522',
  Port:          '#F5C842',
  Endpoint:      '#F04343',
  Technology:    '#C98A5A',
  Vulnerability: '#FF2020',
}

const VULN_SEVERITY_COLOR = {
  critical: '#FF2020',
  high:     '#FF5522',
  medium:   '#F5C842',
  low:      '#FFAA33',
  info:     '#886868',
}

const EDGE_COLOR = {
  HAS_TARGET:        '#CC000040',
  HAS_SUBDOMAIN:     '#FFAA3350',
  HAS_PORT:          '#F5C84250',
  HAS_ENDPOINT:      '#F0434340',
  HAS_VULNERABILITY: '#FF202060',
  USES:              '#C98A5A50',
  RESOLVES_TO:       '#FF552240',
}

function nodeColor(d) {
  if (d.type === 'Vulnerability') {
    return VULN_SEVERITY_COLOR[d.data?.severity] || VULN_SEVERITY_COLOR.info
  }
  return TYPE_COLOR[d.type] || '#886868'
}

function nodeRadius(d) {
  if (d.type === 'Engagement')  return 26
  if (d.type === 'Domain')      return 18
  if (d.type === 'IPAddress')   return 18
  if (d.type === 'Port')        return 11
  if (d.type === 'Technology')  return 10
  if (d.type === 'Endpoint')    return 13
  if (d.type === 'Vulnerability') {
    return { critical: 22, high: 18, medium: 14, low: 10, info: 8 }[d.data?.severity] || 10
  }
  return 12
}

// ── Node detail panel ────────────────────────────────────────────────────────
function NodePanel({ node, onClose }) {
  if (!node) return null
  const col = nodeColor(node)

  const skip = new Set(['id', 'vid'])
  const entries = Object.entries(node.data || {})
    .filter(([k, v]) => !skip.has(k) && v !== null && v !== '' && v !== 0)

  return (
    <motion.div
      initial={{ opacity: 0, x: 16, y: 0 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 16 }}
      transition={{ type: 'spring', stiffness: 260, damping: 24 }}
      className="absolute top-12 right-3 w-72 hud-card z-20"
      style={{ borderColor: `${col}50` }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <span
            className="text-[9px] font-display tracking-widest block"
            style={{ color: col }}
          >
            ─ {node.type.toUpperCase()}
          </span>
          {node.data?.severity && (
            <span
              className="text-[9px] font-mono px-1.5 py-0.5 mt-1 inline-block"
              style={{
                background: `${VULN_SEVERITY_COLOR[node.data.severity]}20`,
                color: VULN_SEVERITY_COLOR[node.data.severity],
                border: `1px solid ${VULN_SEVERITY_COLOR[node.data.severity]}40`,
                clipPath: 'polygon(4px 0%,100% 0%,calc(100% - 4px) 100%,0% 100%)',
              }}
            >
              {node.data.severity.toUpperCase()}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-fg-dim hover:text-fg transition-colors"
          aria-label="close"
        >
          <X size={13} />
        </button>
      </div>

      {/* Label */}
      <p className="font-mono text-xs text-fg mb-3 break-all leading-relaxed"
         style={{ color: col }}>
        {node.label}
      </p>

      {/* Properties */}
      <div className="space-y-0.5 max-h-52 overflow-y-auto pr-1">
        {entries.map(([k, v]) => (
          <div
            key={k}
            className="flex justify-between text-[10px] font-mono py-1.5 border-b border-border"
          >
            <span className="text-fg-muted capitalize flex-shrink-0 mr-2">
              {k.replace(/_/g, ' ')}
            </span>
            <span
              className="text-fg text-right truncate max-w-[155px]"
              title={String(v)}
            >
              {typeof v === 'boolean' ? (v ? 'yes' : 'no') : String(v)}
            </span>
          </div>
        ))}
        {entries.length === 0 && (
          <p className="text-[10px] text-fg-dim font-mono">No properties.</p>
        )}
      </div>
    </motion.div>
  )
}

// ── Legend ───────────────────────────────────────────────────────────────────
function Legend({ stats }) {
  const types = Object.entries(TYPE_COLOR)
  return (
    <div
      className="absolute bottom-4 left-3 hud-card text-[10px] font-mono z-10"
      style={{ minWidth: 152 }}
    >
      <div className="text-[9px] font-display tracking-widest text-fg-muted mb-2.5">
        ─ NODE TYPES
      </div>
      {types.map(([type, col]) => (
        <div key={type} className="flex items-center gap-2 py-0.5">
          <div
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: col, boxShadow: `0 0 4px ${col}` }}
          />
          <span className="text-fg-muted flex-1">{type}</span>
          {stats[type] != null && (
            <span className="text-fg">{stats[type]}</span>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Attack-paths panel ────────────────────────────────────────────────────────
function AttackPathsPanel({ paths, activePath, onSelect }) {
  if (!paths || paths.length === 0) return null
  return (
    <div
      className="absolute top-12 left-3 w-64 hud-card z-10 p-0 overflow-hidden"
      style={{ borderColor: 'rgba(255,32,32,0.25)' }}
    >
      <div className="flex items-center gap-1.5 px-3 py-2 border-b border-border">
        <Crosshair size={12} className="neon-red" />
        <span className="text-[9px] font-display tracking-widest neon-red">
          ATTACK PATHS
        </span>
        <span className="text-[9px] font-mono text-fg-dim ml-auto">{paths.length}</span>
      </div>

      <div className="max-h-[280px] overflow-y-auto">
        {paths.map(p => {
          const col = PATH_SEV_COLOR[p.severity] || '#FFAA33'
          const active = activePath?.id === p.id
          return (
            <button
              key={p.id}
              onClick={() => onSelect(active ? null : p)}
              className="w-full text-left px-3 py-2 border-b border-border last:border-0 transition-colors"
              style={{ background: active ? 'rgba(255,32,32,0.08)' : 'transparent' }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="text-[10px] font-display font-black px-1.5 py-0.5 flex-shrink-0"
                  style={{
                    color: col, border: `1px solid ${col}55`, background: `${col}12`,
                    clipPath: 'polygon(4px 0%,100% 0%,calc(100% - 4px) 100%,0% 100%)',
                  }}
                >
                  {p.score}
                </span>
                <span className="text-[10px] font-mono text-fg truncate flex-1">
                  {p.target.label}
                </span>
                {active
                  ? <X size={11} className="text-fg-muted flex-shrink-0" />
                  : <ChevronRight size={11} className="text-fg-dim flex-shrink-0" />}
              </div>
              <div className="flex items-center gap-1 mt-1 text-[9px] font-mono text-fg-muted">
                <Target size={9} style={{ color: col }} />
                <span className="truncate">{p.target.reason}</span>
              </div>
            </button>
          )
        })}
      </div>

      {activePath && (
        <div className="px-3 py-2 border-t border-border">
          <div className="text-[9px] font-mono text-fg-dim leading-relaxed break-words">
            {activePath.rationale}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Toolbar ──────────────────────────────────────────────────────────────────
function Toolbar({ onZoomIn, onZoomOut, onFit, onRefresh, loading }) {
  const btn = 'p-1.5 rounded text-fg-muted hover:text-fg hover:bg-card-hover transition-colors'
  return (
    <div
      className="absolute top-3 right-3 z-10 flex items-center gap-1 hud-card py-1.5 px-2"
      style={{ borderColor: '#261414' }}
    >
      <button className={btn} onClick={onZoomIn}  title="Zoom in">  <ZoomIn  size={13} /></button>
      <button className={btn} onClick={onZoomOut} title="Zoom out"> <ZoomOut size={13} /></button>
      <button className={btn} onClick={onFit}     title="Fit view"> <Maximize2 size={13} /></button>
      <div className="w-px h-4 bg-border mx-1" />
      <button
        className={btn + (loading ? ' animate-spin' : '')}
        onClick={onRefresh}
        title="Rebuild graph"
      >
        <RefreshCw size={13} />
      </button>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function AttackGraph({ engagementId }) {
  const svgRef  = useRef(null)
  const simRef  = useRef(null)
  const zoomRef = useRef(null)
  const gRef    = useRef(null)
  const nodeSelRef = useRef(null)
  const linkSelRef = useRef(null)

  const [selected,  setSelected]  = useState(null)
  const [stats,     setStats]     = useState({})
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [nodeCount, setNodeCount] = useState(0)
  const [riskScore, setRiskScore] = useState(null)
  const [paths,     setPaths]     = useState([])
  const [activePath, setActivePath] = useState(null)

  // ── Graph initialisation ───────────────────────────────────────
  const initGraph = useCallback((rawNodes, rawLinks) => {
    if (!svgRef.current) return
    const svg = d3.select(svgRef.current)
    const W   = svgRef.current.clientWidth  || 900
    const H   = svgRef.current.clientHeight || 560

    svg.selectAll('*').remove()

    // Arrow markers
    const defs = svg.append('defs')
    ;[
      { id: 'arr',      col: '#5A3A3A' },
      { id: 'arr-vuln', col: '#FF202080' },
      { id: 'arr-port', col: '#F5C84260' },
    ].forEach(({ id, col }) => {
      defs.append('marker')
        .attr('id', id)
        .attr('viewBox', '0 -4 8 8')
        .attr('refX', 22).attr('refY', 0)
        .attr('markerWidth', 5).attr('markerHeight', 5)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-4L8,0L0,4')
        .attr('fill', col)
    })

    // Zoom behaviour
    const zoom = d3.zoom()
      .scaleExtent([0.08, 5])
      .on('zoom', e => g.attr('transform', e.transform))
    zoomRef.current = zoom
    svg.call(zoom).on('dblclick.zoom', null)

    const g = svg.append('g')
    gRef.current = g

    // Click away to deselect
    svg.on('click', () => setSelected(null))

    // ── Force simulation ──────────────────────────────────────────
    const nodes = rawNodes.map(n => ({ ...n }))
    const idSet = new Set(nodes.map(n => n.id))
    const links = rawLinks
      .filter(l => idSet.has(l.source) && idSet.has(l.target))
      .map(l => ({ ...l }))

    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id)
        .distance(d => {
          const t = d.target.type || ''
          if (t === 'Vulnerability') return 75
          if (t === 'Technology')   return 65
          if (t === 'Port')         return 60
          return 110
        })
        .strength(0.55)
      )
      .force('charge', d3.forceManyBody()
        .strength(d => {
          if (d.type === 'Engagement')  return -900
          if (d.type === 'Domain')      return -350
          if (d.type === 'IPAddress')   return -350
          return -220
        })
      )
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 14))
      .alphaDecay(0.025)

    simRef.current = sim

    // ── Edge lines ────────────────────────────────────────────────
    const edgeG = g.append('g').attr('class', 'edges')
    const linkSel = edgeG.selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', d => EDGE_COLOR[d.type] || '#33222290')
      .attr('stroke-width', d => d.type === 'HAS_VULNERABILITY' ? 1.2 : 0.8)
      .attr('stroke-dasharray', d => d.type === 'HAS_VULNERABILITY' ? '4,3' : 'none')
      .attr('marker-end', d =>
        d.type === 'HAS_VULNERABILITY' ? 'url(#arr-vuln)'
        : d.type === 'HAS_PORT'        ? 'url(#arr-port)'
        : 'url(#arr)'
      )

    // ── Node groups ───────────────────────────────────────────────
    const nodeG = g.append('g').attr('class', 'nodes')
    const nodeSel = nodeG.selectAll('g.node')
      .data(nodes)
      .join('g')
      .attr('class', 'node')
      .attr('cursor', 'pointer')
      .call(
        d3.drag()
          .on('start', (e, d) => {
            if (!e.active) sim.alphaTarget(0.25).restart()
            d.fx = d.x; d.fy = d.y
          })
          .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y })
          .on('end', (e, d) => {
            if (!e.active) sim.alphaTarget(0)
            d.fx = null; d.fy = null
          })
      )
      .on('click', (e, d) => { e.stopPropagation(); setSelected(d) })

    // Outer glow ring
    nodeSel.append('circle')
      .attr('r', d => nodeRadius(d) + 7)
      .attr('fill', 'none')
      .attr('stroke', d => nodeColor(d))
      .attr('stroke-width', 0.8)
      .attr('stroke-opacity', d =>
        d.type === 'Vulnerability' && ['critical','high'].includes(d.data?.severity)
          ? 0.5 : 0.12
      )

    // Main circle
    nodeSel.append('circle')
      .attr('r', d => nodeRadius(d))
      .attr('fill', d => `${nodeColor(d)}1A`)
      .attr('stroke', d => nodeColor(d))
      .attr('stroke-width', d => d.type === 'Engagement' ? 2.5 : 1.5)
      .style('filter', d => `drop-shadow(0 0 ${Math.round(nodeRadius(d) * 0.6)}px ${nodeColor(d)})`)

    // Inner dot
    nodeSel.append('circle')
      .attr('r', d => nodeRadius(d) * 0.32)
      .attr('fill', d => nodeColor(d))
      .attr('fill-opacity', 0.75)

    // Labels below node
    nodeSel.append('text')
      .attr('dy', d => nodeRadius(d) + 13)
      .attr('text-anchor', 'middle')
      .attr('font-size', '8.5')
      .attr('font-family', 'JetBrains Mono, monospace')
      .attr('fill', '#886868')
      .attr('pointer-events', 'none')
      .text(d => {
        const l = d.label
        return l.length > 24 ? l.slice(0, 21) + '…' : l
      })

    // Expose selections for attack-path highlighting
    nodeSelRef.current = nodeSel
    linkSelRef.current = linkSel

    // ── Tick ──────────────────────────────────────────────────────
    sim.on('tick', () => {
      linkSel
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
      nodeSel.attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`)
    })

    // Auto-fit after layout stabilises
    sim.on('end', () => fitView(svg, g, zoom, W, H))
  }, [])

  function fitView(svg, g, zoom, W, H) {
    if (!g?.node()) return
    try {
      const b = g.node().getBBox()
      if (!b.width || !b.height) return
      const pad   = 60
      const scale = Math.min((W - pad) / b.width, (H - pad) / b.height, 1.2)
      const tx    = (W - b.width * scale) / 2 - b.x * scale
      const ty    = (H - b.height * scale) / 2 - b.y * scale
      svg.transition().duration(600).call(
        zoom.transform,
        d3.zoomIdentity.translate(tx, ty).scale(scale)
      )
    } catch (_) { /* no-op */ }
  }

  // ── Data fetch ─────────────────────────────────────────────────
  const token = () => localStorage.getItem('argus_token')
  const authHeaders = () => {
    const t = token()
    return t ? { Authorization: `Bearer ${t}` } : {}
  }

  const fetchPaths = useCallback(() => {
    if (!engagementId) return
    fetch(`/api/graph/${engagementId}/attack-paths`, { headers: authHeaders() })
      .then(r => (r.ok ? r.json() : null))
      .then(data => { if (data) setPaths(data.paths || []) })
      .catch(() => { /* non-fatal */ })
  }, [engagementId])

  const fetchGraph = useCallback(() => {
    if (!engagementId) return
    setLoading(true)
    setError(null)
    setActivePath(null)
    setPaths([])

    fetch(`/api/graph/${engagementId}`, { headers: authHeaders() })
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(({ nodes, links, correlation }) => {
        setNodeCount(nodes.length)
        setRiskScore(correlation?.risk_score ?? null)
        const s = {}
        nodes.forEach(n => { s[n.type] = (s[n.type] || 0) + 1 })
        setStats(s)
        initGraph(nodes, links)
        setLoading(false)
        fetchPaths()
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [engagementId, initGraph, fetchPaths])

  useEffect(() => {
    fetchGraph()
    return () => { simRef.current?.stop() }
  }, [fetchGraph])

  // ── Attack-path highlighting ───────────────────────────────────
  useEffect(() => {
    const nodeSel = nodeSelRef.current
    const linkSel = linkSelRef.current
    if (!nodeSel || !linkSel) return

    if (!activePath) {
      nodeSel.transition().duration(250).style('opacity', 1)
      nodeSel.selectAll('circle.path-ring').remove()
      linkSel.transition().duration(250)
        .style('opacity', 1)
        .attr('stroke-width', d => (d.type === 'HAS_VULNERABILITY' ? 1.2 : 0.8))
      return
    }

    const nodeIds = new Set(activePath.node_ids)
    const edgeKeys = new Set((activePath.link_keys || []).map(([a, b]) => `${a}|${b}`))

    nodeSel.transition().duration(250)
      .style('opacity', d => (nodeIds.has(d.id) ? 1 : 0.12))
    // emphasis ring on path nodes
    nodeSel.selectAll('circle.path-ring').remove()
    nodeSel.filter(d => nodeIds.has(d.id))
      .append('circle')
      .attr('class', 'path-ring')
      .attr('r', d => nodeRadius(d) + 4)
      .attr('fill', 'none')
      .attr('stroke', '#FF2020')
      .attr('stroke-width', 1.6)
      .attr('stroke-opacity', 0.9)
      .style('filter', 'drop-shadow(0 0 6px #FF2020)')

    linkSel.transition().duration(250)
      .style('opacity', d => (edgeKeys.has(`${d.source.id}|${d.target.id}`) ? 1 : 0.06))
      .attr('stroke', d => (edgeKeys.has(`${d.source.id}|${d.target.id}`) ? '#FF2020' : (EDGE_COLOR[d.type] || '#33222290')))
      .attr('stroke-width', d => (edgeKeys.has(`${d.source.id}|${d.target.id}`) ? 2.4 : 0.8))
  }, [activePath])

  // ── Toolbar callbacks ──────────────────────────────────────────
  const handleZoomIn  = () => {
    const svg = d3.select(svgRef.current)
    svg.transition().duration(250).call(zoomRef.current.scaleBy, 1.4)
  }
  const handleZoomOut = () => {
    const svg = d3.select(svgRef.current)
    svg.transition().duration(250).call(zoomRef.current.scaleBy, 0.7)
  }
  const handleFit = () => {
    const svg = d3.select(svgRef.current)
    const W   = svgRef.current.clientWidth  || 900
    const H   = svgRef.current.clientHeight || 560
    fitView(svg, gRef.current, zoomRef.current, W, H)
  }

  // ── Render ─────────────────────────────────────────────────────
  if (loading) return (
    <div className="flex items-center justify-center h-96">
      <div className="text-center space-y-4">
        <div className="relative w-16 h-16 mx-auto">
          <div className="absolute inset-0 rounded-full border-2 border-neon-green border-t-transparent animate-spin" />
          <div className="absolute inset-2 rounded-full border border-neon-cyan border-b-transparent animate-spin"
               style={{ animationDirection: 'reverse', animationDuration: '0.8s' }} />
        </div>
        <p className="text-xs font-display tracking-widest neon-green animate-neon-pulse">
          BUILDING ATTACK GRAPH…
        </p>
      </div>
    </div>
  )

  if (error) return (
    <div className="flex items-center justify-center h-96">
      <div className="text-center space-y-3">
        <AlertTriangle size={32} className="mx-auto neon-red" />
        <p className="text-xs font-mono neon-red">Graph unavailable</p>
        <p className="text-[10px] font-mono text-fg-muted max-w-xs">{error}</p>
        <p className="text-[10px] text-fg-dim font-mono">
          Ensure Neo4j is running and at least one scan has completed.
        </p>
        <button
          onClick={fetchGraph}
          className="text-[10px] font-display tracking-widest neon-cyan border border-neon-cyan px-3 py-1.5 hover:bg-neon-cyan hover:text-void transition-colors"
        >
          RETRY
        </button>
      </div>
    </div>
  )

  return (
    <div
      className="relative rounded-lg overflow-hidden"
      style={{
        height: 560,
        background: 'rgba(9,8,10,0.95)',
        border: '1px solid rgba(204,0,0,0.14)',
      }}
    >
      {/* Top stats bar */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-3 pointer-events-none">
        <span className="text-[9px] font-display tracking-widest text-fg-muted">
          ─ ATTACK SURFACE MAP
        </span>
        <span className="text-[9px] font-mono neon-cyan">{nodeCount} NODES</span>
        {riskScore !== null && (
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-[9px] font-display px-2 py-0.5"
            style={{
              background: riskScore >= 60 ? 'rgba(255,32,32,0.15)'
                : riskScore >= 30 ? 'rgba(245,200,66,0.12)'
                : 'rgba(255,170,51,0.1)',
              color: riskScore >= 60 ? '#FF2020'
                   : riskScore >= 30 ? '#F5C842'
                   : '#FFAA33',
              border: `1px solid ${riskScore >= 60 ? '#FF202040' : riskScore >= 30 ? '#F5C84240' : '#FFAA3340'}`,
              clipPath: 'polygon(6px 0%,100% 0%,calc(100% - 6px) 100%,0% 100%)',
            }}
          >
            RISK SCORE {riskScore}
          </motion.span>
        )}
      </div>

      {/* Toolbar */}
      <Toolbar
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onFit={handleFit}
        onRefresh={fetchGraph}
        loading={loading}
      />

      {/* SVG canvas */}
      <svg
        ref={svgRef}
        className="w-full h-full"
        style={{ background: 'transparent' }}
      />

      {/* HUD corners */}
      <div className="corner-tl absolute top-0 left-0 pointer-events-none" />
      <div className="corner-tr absolute top-0 right-0 pointer-events-none" />
      <div className="corner-bl absolute bottom-0 left-0 pointer-events-none" />
      <div className="corner-br absolute bottom-0 right-0 pointer-events-none" />

      {/* Attack paths panel */}
      <AttackPathsPanel
        paths={paths}
        activePath={activePath}
        onSelect={setActivePath}
      />

      {/* Node detail panel */}
      <AnimatePresence>
        {selected && (
          <NodePanel
            key={selected.id}
            node={selected}
            onClose={() => setSelected(null)}
          />
        )}
      </AnimatePresence>

      {/* Legend */}
      <Legend stats={stats} />
    </div>
  )
}
