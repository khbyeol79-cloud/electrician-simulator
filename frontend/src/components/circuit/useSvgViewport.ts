import { useCallback, useRef, useState } from 'react'

type SvgViewportOptions = {
  minZoom?: number
  maxZoom?: number
  wheelStep?: number
  panSpeed?: number
  fitZoom?: number
  mapClientToViewBox?: boolean
}

export function calculatePanDelta({ dx, dy, zoom, panSpeed, clientWidth, clientHeight, viewBoxWidth, viewBoxHeight, mapClientToViewBox }: {
  dx: number
  dy: number
  zoom: number
  panSpeed: number
  clientWidth: number
  clientHeight: number
  viewBoxWidth: number
  viewBoxHeight: number
  mapClientToViewBox: boolean
}) {
  const scaleX = mapClientToViewBox && clientWidth > 0 && viewBoxWidth > 0 ? viewBoxWidth / clientWidth : 1
  const scaleY = mapClientToViewBox && clientHeight > 0 && viewBoxHeight > 0 ? viewBoxHeight / clientHeight : 1
  return { x: (dx * scaleX / zoom) * panSpeed, y: (dy * scaleY / zoom) * panSpeed }
}

export function useSvgViewport({ minZoom = 0.65, maxZoom = 2.5, wheelStep = 0.1, panSpeed = 1, fitZoom = 0.82, mapClientToViewBox = false }: SvgViewportOptions = {}) {
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const drag = useRef<{ pointerId: number; x: number; y: number; moved: boolean } | undefined>(undefined)
  const lastDragMoved = useRef(false)

  const zoomBy = useCallback((delta: number) => setZoom((value) => Math.min(maxZoom, Math.max(minZoom, value + delta))), [maxZoom, minZoom])
  const reset = useCallback(() => { setZoom(1); setPan({ x: 0, y: 0 }) }, [])
  const fit = useCallback(() => { setZoom(fitZoom); setPan({ x: 140, y: 70 }) }, [fitZoom])

  const pointerDown = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    const target = event.target as EventTarget & { closest?: (selector: string) => Element | null }
    if (target.closest?.('.element-hitbox')) return
    drag.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, moved: false }
    event.currentTarget.setPointerCapture?.(event.pointerId)
  }, [])
  const pointerMove = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    if (!drag.current || drag.current.pointerId !== event.pointerId) return
    const dx = event.clientX - drag.current.x
    const dy = event.clientY - drag.current.y
    if (Math.abs(dx) + Math.abs(dy) > 3) drag.current.moved = true
    const bounds = event.currentTarget.getBoundingClientRect()
    const viewBox = event.currentTarget.viewBox.baseVal
    const delta = calculatePanDelta({
      dx, dy, zoom, panSpeed,
      clientWidth: bounds.width, clientHeight: bounds.height,
      viewBoxWidth: viewBox.width, viewBoxHeight: viewBox.height,
      mapClientToViewBox,
    })
    setPan((value) => ({ x: value.x + delta.x, y: value.y + delta.y }))
    drag.current.x = event.clientX
    drag.current.y = event.clientY
  }, [mapClientToViewBox, panSpeed, zoom])
  const pointerUp = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    const currentDrag = drag.current
    if (currentDrag && currentDrag.pointerId === event.pointerId) {
      lastDragMoved.current = currentDrag.moved
      drag.current = undefined
      event.currentTarget.releasePointerCapture?.(event.pointerId)
    }
  }, [])
  const wheel = useCallback((event: React.WheelEvent<SVGSVGElement>) => {
    event.preventDefault()
    zoomBy(event.deltaY < 0 ? wheelStep : -wheelStep)
  }, [wheelStep, zoomBy])

  const consumeDragClick = useCallback(() => {
    const moved = lastDragMoved.current
    lastDragMoved.current = false
    return moved
  }, [])

  return { zoom, pan, zoomBy, reset, fit, pointerDown, pointerMove, pointerUp, wheel, consumeDragClick }
}
