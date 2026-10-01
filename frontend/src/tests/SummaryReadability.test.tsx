/// <reference types="vite/client" />
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { WiringBoard, deviceSummaryColor, buildTerminalSummary } from '../features/wiring/components/WiringBoard'
import { SlotNumberExample } from '../components/SlotNumberExample'
import type { BoardDefinition, WiringConnection } from '../api/client'

afterEach(cleanup)

it('assigns distinct Q001 device colors consistently to connection summaries', () => {
  const boards = import.meta.glob('../../../problems/qnet_electrician_practical_001/board.json', { eager: true, import: 'default' })
  const board = Object.values(boards)[0] as BoardDefinition
  const ids = board.items.map(item => item.item_id)
  expect(new Set(ids.map(deviceSummaryColor)).size).toBe(ids.length)
  for (const id of ['X', 'FR', 'T', 'FLS']) {
    expect(deviceSummaryColor(id)).not.toBe('#64748b')
    const target = board.items.find(item => item.item_id === id)!.pins[0].terminal_id
    const summary = buildTerminalSummary(board, [{from:'TB5-01',to:target,wire_color:'yellow',pair_display_color:'#64748b'}])
    expect(summary.get('TB5-01')![0].color).toBe(deviceSummaryColor(id))
  }
})

it('preserves original summary geometry across all 18 public boards without mutating board data', () => {
  const boards = import.meta.glob('../../../problems/qnet_electrician_practical_*/board.json', { eager: true, import: 'default' })
  expect(Object.keys(boards)).toHaveLength(18)
  for (const raw of Object.values(boards)) {
    const board = raw as BoardDefinition
    const deviceColors = board.items.map(item => deviceSummaryColor(item.item_id))
    expect(deviceColors).not.toContain('#64748b')
    expect(new Set(deviceColors).size, board.board_id).toBe(board.items.length)
    const before = JSON.stringify(board)
    const pins = board.items.flatMap(item => item.pins)
    const connections: WiringConnection[] = pins.map((pin, i) => ({ from: pin.terminal_id, to: pins[(i + 7) % pins.length].terminal_id, wire_color: 'yellow', pair_display_color: '#64748b' }))
    for (const item of board.items.filter(item => item.item_type === 'terminal_block')) for (const pin of item.pins) connections.unshift({ from: pin.terminal_id, to: 'FLS-PE', wire_color: 'yellow', pair_display_color: '#64748b' })
    const noop = () => undefined
    const props = {board, connections, selectedPin:null, selectedWire:null, selectedSummaryTerminal:null, zoom:1, onPinClick:noop, onPinPointerDown:noop, onPinPointerUp:noop, onExternalDrop:noop, onWireSelect:noop, onSummarySelect:noop, onClearSelection:noop}
    const { container, unmount, rerender } = render(<WiringBoard {...props} mode="summary" />)
    expect(container.querySelector('svg')).toHaveAttribute('viewBox', `0 0 ${board.width} ${board.height}`)
    expect(container.querySelector('.summary-board-scroll')).toBeNull()
    for (const badge of container.querySelectorAll('.pin-summary-count text')) expect(badge.textContent).toBe('+')
    for (const badge of container.querySelectorAll('.pin-summary-count rect')) {
      const label = badge.closest('.pin-summary')!.querySelector('rect')!
      expect(Number(badge.getAttribute('x')) + Number(badge.getAttribute('width')))
        .toBeLessThanOrEqual(Number(label.getAttribute('width')) / 2 + 4)
    }
    expect(container.querySelector('.board-label-layer')?.textContent).not.toContain('10P+10P')
    for (const item of board.items.filter(item => ['TB5','TB6'].includes(item.item_id))) {
      for (const pin of item.pins) {
        const group = container.querySelector(`[aria-label="${pin.terminal_id} 단자"]`)!
        const capacity = group.querySelector('.terminal-bank-capacity')!
        const [x,y] = capacity.getAttribute('transform')!.match(/-?\d+(?:\.\d+)?/g)!.map(Number)
        expect(x + 17).toBe(pin.x)
        if (item.item_id === 'TB5') expect(y + 19).toBeLessThan(item.y + 8)
        else expect(y - 10).toBeGreaterThan(item.y + item.height - 8)
      }
    }
    expect(JSON.stringify(board)).toBe(before)
    expect(container.querySelectorAll('.pin-capacity:not(.terminal-bank-capacity)')).toHaveLength(0)
    rerender(<WiringBoard {...props} connections={[]} mode="graphic" selectedPin={pins[0].terminal_id} />)
    expect(container.querySelectorAll('.pin-capacity')).toHaveLength(0)
    unmount()
  }
})

it('provides an accessible diagram showing both slot-number orientations', () => {
  render(<SlotNumberExample />)
  expect(screen.getByRole('img', { name: /가로 접점은 좌우.*세로 접점은 위아래/ })).toBeInTheDocument()
})
it('inspects every direct wire in either direction without starting a new connection', () => {
  const boards = import.meta.glob('../../../problems/qnet_electrician_practical_001/board.json', { eager: true, import: 'default' })
  const board = Object.values(boards)[0] as BoardDefinition
  const [a,b,c,d] = board.items.flatMap(item => item.pins).map(pin => pin.terminal_id)
  const connections: WiringConnection[] = [[a,b],[c,a],[b,d]].map(([from,to]) => ({from,to,wire_color:'yellow',pair_display_color:'#64748b'}))
  const onSummarySelect = vi.fn(), onPinClick = vi.fn(), onPinPointerDown = vi.fn(), onPinPointerUp = vi.fn()
  const props = {board, connections, mode:'summary' as const, selectedPin:null, selectedWire:null, selectedSummaryTerminal:null as string | null, zoom:1,onPinClick,onPinPointerDown,onPinPointerUp,onExternalDrop:vi.fn(),onWireSelect:vi.fn(),onSummarySelect,onClearSelection:vi.fn()}
  const {container,rerender} = render(<WiringBoard {...props} />)
  expect(container.querySelectorAll('.board-wire')).toHaveLength(0)
  const pin = screen.getByRole('button',{name:a+' 단자'})
  fireEvent.pointerDown(pin); fireEvent.pointerUp(pin); fireEvent.click(pin)
  expect(onSummarySelect).toHaveBeenCalledWith(a,[0,1])
  expect(onPinClick).not.toHaveBeenCalled()
  expect(onPinPointerDown).not.toHaveBeenCalled()
  expect(onPinPointerUp).not.toHaveBeenCalled()
  rerender(<WiringBoard {...props} selectedSummaryTerminal={a} />)
  expect(container.querySelectorAll('.board-wire')).toHaveLength(2)
  expect(screen.queryByRole('button',{name:b+'에서 '+d+'로 연결된 전선'})).not.toBeInTheDocument()
  rerender(<WiringBoard {...props} />)
  expect(container.querySelectorAll('.board-wire')).toHaveLength(0)
})
