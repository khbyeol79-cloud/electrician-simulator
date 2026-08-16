import { useCallback, useRef, useState } from 'react'

export function useSvgViewport() {
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const drag = useRef<{ pointerId: number; x: number; y: number; moved: boolean } | undefined>(undefined)
  const lastDragMoved = useRef(false)

  const clamp = (value: number) => Math.min(2.5, Math.max(0.65, value))
  const zoomBy = useCallback((delta: number) => setZoom((value) => clamp(value + delta)), [])
  const reset = useCallback(() => { setZoom(1); setPan({ x: 0, y: 0 }) }, [])
  const fit = useCallback(() => { setZoom(0.82); setPan({ x: 140, y: 70 }) }, [])

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
    setPan((value) => ({ x: value.x + dx / zoom, y: value.y + dy / zoom }))
    drag.current.x = event.clientX
    drag.current.y = event.clientY
  }, [zoom])
  const pointerUp = useCallback((event: React.PointerEvent<SVGSVGElement>) => {
    const currentDrag = drag.current
    if (currentDrag && currentDrag.pointerId === event.pointerId) {
      lastDragMoved.current = currentDrag.moved
      drag.current = undefined
    }
  }, [])
  const wheel = useCallback((event: React.WheelEvent<SVGSVGElement>) => {
    event.preventDefault()
    zoomBy(event.deltaY < 0 ? 0.1 : -0.1)
  }, [zoomBy])

  const consumeDragClick = useCallback(() => {
    const moved = lastDragMoved.current
    lastDragMoved.current = false
    return moved
  }, [])

  return { zoom, pan, zoomBy, reset, fit, pointerDown, pointerMove, pointerUp, wheel, consumeDragClick }
}
