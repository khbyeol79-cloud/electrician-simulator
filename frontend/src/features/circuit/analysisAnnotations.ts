import geometry from './contactHotspots.json'
import deviceOrder from './contactDeviceOrder.json'
import type { SchematicDiagram } from '../../api/client'

export const layoutReferenceDiagram: SchematicDiagram = {
  schema_version: '1.0', view_box: { x: 0, y: 0, width: 1200, height: 1700 },
  sections: [], elements: [], conductors: [],
}

export type ContactTarget = { id: string; x: number; y: number; orientation: 'horizontal' | 'vertical'; kind?: 'body'; deviceId?: string }
export type DiagramAnnotationMarker = { id: string; x: number; y: number; label: string; orientation?: 'horizontal' | 'vertical'; second?: string; offsetX?: number; offsetY?: number; kind?: 'body'; deviceId?: string }

export function contactTargets(problemId: string): ContactTarget[] {
  const targets = (geometry as Record<string, ContactTarget[]>)[problemId] ?? []
  // Audited against the original page-7 symbols, not user answers or engine nets.
  const owners = (deviceOrder as Record<string, string>)[problemId.slice(-3)]?.split(' ') ?? []
  return targets.map((target, index) => ({ ...target, deviceId: owners.length === targets.length ? owners[index] : undefined }))
}

// Both old single-position annotations and new two-terminal annotations survive upgrades.
export function parseAnnotations(values: Record<string, string>): DiagramAnnotationMarker[] {
  return Object.entries(values).flatMap(([id, value]) => {
    if (!id.startsWith('marker:') && !id.startsWith('contact:')) return []
    try {
      const p = JSON.parse(value)
      if (!Number.isFinite(p.x) || !Number.isFinite(p.y)) return []
      const orientation = p.orientation === 'vertical' || p.orientation === 'horizontal' ? p.orientation : undefined
      return [{ id, x: p.x, y: p.y, label: typeof p.label === 'string' ? p.label : '', orientation, second: typeof p.second === 'string' ? p.second : '', offsetX: Number.isFinite(p.offsetX) ? p.offsetX : 0, offsetY: Number.isFinite(p.offsetY) ? p.offsetY : 0, kind: p.kind === 'body' ? 'body' as const : undefined, deviceId: typeof p.deviceId === 'string' ? p.deviceId : undefined }]
    } catch { return [] }
  })
}
