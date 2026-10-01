import { useCallback, useEffect, useRef, useState } from 'react'

type Point = { x: number; y: number }

// translate(pan) precedes scale(zoom): pan is in root SVG units, not zoomed units.
// preserveAspectRatio="meet" uses one scale for both axes, including letterboxing.
export function calculatePanDelta({ dx, dy, clientWidth, clientHeight, viewBoxWidth, viewBoxHeight }: {
  dx: number; dy: number; clientWidth: number; clientHeight: number; viewBoxWidth: number; viewBoxHeight: number
}) {
  const scale = clientWidth > 0 && clientHeight > 0 ? Math.max(viewBoxWidth / clientWidth, viewBoxHeight / clientHeight) : 1
  return { x: dx * scale, y: dy * scale }
}

function viewBox(svg: SVGSVGElement) {
  const [x = 0, y = 0, width = 1, height = 1] = (svg.getAttribute('viewBox') ?? '').trim().split(/\s+/).map(Number)
  return { x, y, width, height }
}

function svgPoint(svg: SVGSVGElement, clientX: number, clientY: number): Point {
  const box = viewBox(svg)
  const rect = svg.getBoundingClientRect()
  const scale = rect.width > 0 && rect.height > 0 ? Math.max(box.width / rect.width, box.height / rect.height) : 1
  return {
    x: box.x + box.width / 2 + (clientX - rect.left - rect.width / 2) * scale,
    y: box.y + box.height / 2 + (clientY - rect.top - rect.height / 2) * scale,
  }
}

export function useSvgViewport({ minZoom = .65, maxZoom = 4, wheelStep = .15 } = {}) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [{ zoom, pan }, setView] = useState({ zoom: 1, pan: { x: 0, y: 0 } })
  const [isDragging, setIsDragging] = useState(false)
  const drag = useRef<{ pointerId: number; x: number; y: number; pan: Point; moved: boolean } | null>(null)
  const lastDragMoved = useRef(false)

  const zoomBy = useCallback((delta: number, anchor?: Point) => {
    const box = svgRef.current ? viewBox(svgRef.current) : { x: 0, y: 0, width: 0, height: 0 }
    const pivot = anchor ?? { x: box.x + box.width / 2, y: box.y + box.height / 2 }
    setView(current => {
      const next = Math.min(maxZoom, Math.max(minZoom, current.zoom + delta))
      const ratio = next / current.zoom
      return { zoom: next, pan: { x: pivot.x - (pivot.x - current.pan.x) * ratio, y: pivot.y - (pivot.y - current.pan.y) * ratio } }
    })
  }, [maxZoom, minZoom])
  const reset = useCallback(() => setView({ zoom: 1, pan: { x: 0, y: 0 } }), [])

  // React's delegated wheel listener may be passive: use a local non-passive one
  // so zooming a diagram does not simultaneously scroll its surrounding panel.
  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    const wheel = (event: WheelEvent) => {
      event.preventDefault()
      event.stopPropagation()
      zoomBy(event.deltaY < 0 ? wheelStep : -wheelStep, svgPoint(svg, event.clientX, event.clientY))
    }
    svg.addEventListener('wheel', wheel, { passive: false })
    return () => svg.removeEventListener('wheel', wheel)
  }, [wheelStep, zoomBy])

  const pointerDown = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    if (event.button !== 0) return
    event.preventDefault() // Prevent text selection and the browser's image drag UI.
    lastDragMoved.current = false
    drag.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, pan, moved: false }
    // Do not capture a simple click: it must still reach the contact/annotation.
  }, [pan])
  const pointerMove = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    const current = drag.current
    if (!current || current.pointerId !== event.pointerId) return
    const dx = event.clientX - current.x, dy = event.clientY - current.y
    if (!current.moved && Math.hypot(dx, dy) < 5) return
    event.preventDefault()
    if (!current.moved) {
      current.moved = true
      event.currentTarget.setPointerCapture?.(event.pointerId)
      setIsDragging(true)
    }
    const rect = event.currentTarget.getBoundingClientRect(), box = viewBox(event.currentTarget)
    const delta = calculatePanDelta({ dx, dy, clientWidth: rect.width, clientHeight: rect.height, viewBoxWidth: box.width, viewBoxHeight: box.height })
    setView(value => ({ ...value, pan: { x: current.pan.x + delta.x, y: current.pan.y + delta.y } }))
  }, [])
  const pointerUp = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    const current = drag.current
    if (!current || current.pointerId !== event.pointerId) return
    lastDragMoved.current = current.moved || event.type === 'pointercancel'
    drag.current = null
    setIsDragging(false)
    if (event.currentTarget.hasPointerCapture?.(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  }, [])
  const consumeDragClick = useCallback(() => {
    const moved = lastDragMoved.current
    lastDragMoved.current = false
    return moved
  }, [])
  return { svgRef, zoom, pan, isDragging, zoomBy, reset, fit: reset, pointerDown, pointerMove, pointerUp, consumeDragClick }
}
