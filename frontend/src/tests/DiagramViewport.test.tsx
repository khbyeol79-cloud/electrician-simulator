import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CircuitDiagram } from '../components/circuit/CircuitDiagram'
import { layoutReferenceDiagram, parseAnnotations } from '../features/circuit/analysisAnnotations'

class TestPointerEvent extends MouseEvent {
  pointerId: number
  constructor(type: string, options: PointerEventInit = {}) {
    super(type, options)
    this.pointerId = options.pointerId ?? 1
  }
}
beforeEach(() => vi.stubGlobal('PointerEvent', TestPointerEvent))
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

function setup(readOnly = false) {
  const select = vi.fn()
  render(<CircuitDiagram diagram={layoutReferenceDiagram} questions={[]} draft={{}} selectedQuestionId={null}
    backgroundHref="/layout.png" readOnly={readOnly} onSelect={() => undefined} onClear={() => undefined}
    annotationMarkers={[{ id: 'contact:1', x: 300, y: 400, label: '10', second: '4', orientation: 'horizontal' }]}
    onAnnotationSelect={select} />)
  const svg = screen.getByRole('img')
  vi.spyOn(svg, 'getBoundingClientRect').mockReturnValue({ x: 0, y: 0, left: 0, top: 0, right: 600, bottom: 850, width: 600, height: 850, toJSON: () => ({}) })
  return { svg, group: svg.firstElementChild!, marker: svg.querySelector('.paired-annotation')!, select }
}

describe('diagram gesture isolation', () => {
  it('pans from annotation text without opening the editor, then allows an ordinary click', () => {
    const { svg, group, marker, select } = setup()
    fireEvent.pointerDown(marker.querySelector('text')!, { clientX: 100, clientY: 100, button: 0 })
    fireEvent.pointerMove(svg, { clientX: 130, clientY: 120 })
    fireEvent.pointerUp(svg, { clientX: 130, clientY: 120 })
    fireEvent.click(marker)
    expect(group).toHaveAttribute('transform', 'translate(60 40) scale(1)')
    expect(select).not.toHaveBeenCalled()
    fireEvent.pointerDown(marker, { clientX: 130, clientY: 120, button: 0 })
    fireEvent.pointerMove(svg, { clientX: 132, clientY: 121 })
    fireEvent.pointerUp(svg, { clientX: 132, clientY: 121 })
    fireEvent.click(marker)
    expect(select).toHaveBeenCalledOnce()
  })

  it('pans read-only images and prevents native image dragging', () => {
    const { svg, group } = setup(true)
    expect(fireEvent.dragStart(svg.querySelector('image')!)).toBe(false)
    fireEvent.pointerDown(svg, { clientX: 200, clientY: 200, button: 0 })
    fireEvent.pointerMove(svg, { clientX: 240, clientY: 230 })
    fireEvent.pointerUp(svg, { clientX: 240, clientY: 230 })
    expect(group).toHaveAttribute('transform', 'translate(80 60) scale(1)')
    fireEvent.click(screen.getByRole('button', { name: '화면 맞춤' }))
    expect(group).toHaveAttribute('transform', 'translate(0 0) scale(1)')
  })

  it('cancels browser wheel scrolling while zooming at the pointer', () => {
    const { svg, group } = setup()
    expect(fireEvent.wheel(svg, { clientX: 0, clientY: 0, deltaY: -100 })).toBe(false)
    expect(group).toHaveAttribute('transform', 'translate(0 0) scale(1.15)')
  })

  it('restores manual label offsets and remains compatible with old saved annotations', () => {
    const markers = parseAnnotations({
      'contact:1': JSON.stringify({ x: 1, y: 2, label: '10', second: '4', orientation: 'horizontal', offsetX: -8, offsetY: 16 }),
      'marker:2': JSON.stringify({ x: 3, y: 4, label: 'A1' }),
    })
    expect(markers[0]).toMatchObject({ offsetX: -8, offsetY: 16 })
    expect(markers[1]).toMatchObject({ label: 'A1', offsetX: 0, offsetY: 0 })
  })
})
