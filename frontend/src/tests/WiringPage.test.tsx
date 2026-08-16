import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import trainingBoardData from '../../../problems/training_socket_demo_001/board.json'
import type { BoardDefinition } from '../api/client'
import { buildTerminalSummary, deviceSummaryColor, summaryLabelY, terminalSlotLabel } from '../features/wiring/components/WiringBoard'
import { pathHasSelfOverlap, routeConnection } from '../features/wiring/engine/orthogonalRouter'
import { WiringPage } from '../pages/WiringPage'
import { installApiMock, trainingDetail, wiringBoard } from './mockApi'

afterEach(() => {
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); window.localStorage.clear()
})

describe('제어함 결선', () => {
  it('shows the stage-one socket-number draft in a read-only zoomable reference diagram', async () => {
    installApiMock()
    window.localStorage.setItem('electrician.circuitDraft.training_socket_demo_001.v1', JSON.stringify({
      'SQ-VR1-C1': { upper: 6, lower: 3 },
    }))
    const user = userEvent.setup()
    render(<WiringPage problem={trainingDetail} />)

    const diagram = await screen.findByRole('img', { name: '회로도 분석 참고창' })
    expect(screen.getByText('1 / 1 입력')).toBeInTheDocument()
    expect(diagram.querySelectorAll('.answer-marker.entered')).toHaveLength(2)
    expect(diagram.querySelector('.answer-marker.entered')?.textContent).toBe('6')
    expect(within(diagram).queryByRole('button', { name: /VR1.*선택/ })).not.toBeInTheDocument()

    const toolbar = screen.getByLabelText('참고 회로도 보기 도구')
    await user.click(within(toolbar).getByRole('button', { name: '확대' }))
    expect(within(toolbar).getByText('130%')).toBeInTheDocument()
    await user.click(within(toolbar).getByRole('button', { name: '화면 맞춤' }))
    expect(within(toolbar).getByText('82%')).toBeInTheDocument()
  })

  it('renders symmetric 8P and 12P bases and connects exact terminals', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<WiringPage problem={trainingDetail} />)
    expect(await screen.findByRole('img', { name: '제어함 결선판' })).toBeInTheDocument()
    expect(screen.getByText('X1')).toBeInTheDocument()
    expect(screen.getByText('MC1')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /단자$/ })).toHaveLength(20)
    await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
    await user.click(screen.getByRole('button', { name: 'MC1-4 단자' }))
    expect(screen.getByRole('button', { name: 'X1-1에서 MC1-4로 연결된 전선' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '요약 모드' }))
    expect(screen.queryByRole('button', { name: 'X1-1에서 MC1-4로 연결된 전선' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'X1-1에서 MC1-4로 연결된 요약 표시' }))
    expect(screen.getByText('연결 단자 1')).toBeInTheDocument()
    expect(screen.getByText('연결 단자 2')).toBeInTheDocument()
  })

  it('connects X1-1 to MC2-5 directly through an empty row gap', () => {
    const board = {
      ...wiringBoard,
      items: wiringBoard.items.map((item) => item.item_id === 'MC1' ? {
        ...item,
        item_id: 'MC2',
        label: 'MC2',
        x: item.x - 388,
        pins: item.pins.map((pin) => ({ ...pin, x: pin.x - 388, terminal_id: pin.terminal_id.replace('MC1-', 'MC2-') })),
      } : item),
    }
    const route = routeConnection(board, { from: 'X1-1', to: 'MC2-5', wire_color: 'yellow', pair_display_color: '#2563eb' })
    expect(route.points.slice(1).every((point, index) => point.x === route.points[index].x || point.y === route.points[index].y)).toBe(true)
    expect(route.points).toEqual([
      { x: 200, y: 340 },
      { x: 200, y: 420 },
      { x: 220, y: 420 },
      { x: 220, y: 500 },
    ])
    expect(route.points.every((point) => point.x !== board.routing_margin)).toBe(true)
  })

  it('keeps the real training board X1-1 to MC2-5 route inside the middle channel', () => {
    const route = routeConnection(trainingBoardData as unknown as BoardDefinition, {
      from: 'X1-1', to: 'MC2-5', wire_color: 'yellow', pair_display_color: '#2563eb',
    })
    expect(route.points).toEqual([
      { x: 812.5, y: 370 },
      { x: 812.5, y: 435 },
      { x: 845, y: 435 },
      { x: 845, y: 500 },
    ])
  })

  it('keeps bundled direct connections within six units of the corridor center', () => {
    const board = trainingBoardData as unknown as BoardDefinition
    const route = routeConnection(board, {
      from: 'X1-1', to: 'MC2-5', wire_color: 'yellow', pair_display_color: '#2563eb',
    }, 4)
    expect(route.points[1].y).toBe(441)
    expect(route.points[2].y).toBe(441)
    const upperBundleRoute = routeConnection(board, {
      from: 'X1-1', to: 'MC2-5', wire_color: 'yellow', pair_display_color: '#2563eb',
    }, 3)
    expect(upperBundleRoute.points[1].y).toBe(429)
  })

  it('connects MCCB-L2 to TB5-13 directly along their shared top corridor', () => {
    const board = trainingBoardData as unknown as BoardDefinition
    const route = routeConnection(board, { from: 'MCCB-L2', to: 'TB5-13', wire_color: 'black', pair_display_color: '#64748b' })
    expect(route.points).toEqual([
      { x: 170, y: 210 },
      { x: 170, y: 157.5 },
      { x: 847.5, y: 157.5 },
      { x: 847.5, y: 115 },
    ])
    expect(pathHasSelfOverlap(route.points)).toBe(false)
  })

  it.each([
    ['EOCR-L3', 'MC1-4'],
    ['MCCB-L1', 'MC2-6'],
    ['F-2', 'T2-2'],
  ])('routes %s to %s through an inset outer lane', (from, to) => {
    const board = trainingBoardData as unknown as BoardDefinition
    const route = routeConnection(board, { from, to, wire_color: 'yellow', pair_display_color: '#64748b' })
    expect(route.points.some((point) => point.x === 63)).toBe(true)
    expect(route.points.every((point) => point.x !== board.routing_margin)).toBe(true)
    expect(pathHasSelfOverlap(route.points)).toBe(false)
  })

  it('creates an orthogonal non-self-overlapping route for every terminal pair on the training board', () => {
    const board = trainingBoardData as unknown as BoardDefinition
    const terminalIds = board.items.flatMap((item) => item.pins.filter((pin) => pin.enabled).map((pin) => pin.terminal_id))
    for (let fromIndex = 0; fromIndex < terminalIds.length; fromIndex += 1) {
      for (let toIndex = fromIndex + 1; toIndex < terminalIds.length; toIndex += 1) {
        const route = routeConnection(board, { from: terminalIds[fromIndex], to: terminalIds[toIndex], wire_color: 'yellow', pair_display_color: '#64748b' }, (fromIndex + toIndex) % 5)
        expect(pathHasSelfOverlap(route.points), `${terminalIds[fromIndex]} → ${terminalIds[toIndex]}`).toBe(false)
      }
    }
  })

  it('uses the opposite device color on each terminal in summary mode', () => {
    const summary = buildTerminalSummary(wiringBoard, [
      { from: 'X1-1', to: 'MC1-4', wire_color: 'yellow', pair_display_color: '#64748b' },
    ])
    expect(summary.get('X1-1')).toEqual({ other: 'MC1-4', slot: '4', color: deviceSummaryColor('MC1'), connectionIndex: 0 })
    expect(summary.get('MC1-4')).toEqual({ other: 'X1-1', slot: '1', color: deviceSummaryColor('X1'), connectionIndex: 0 })
  })

  it('assigns distinct summary colors including T1, TB5 and TB6', () => {
    const ids = ['MCCB', 'EOCR', 'F', 'X1', 'X2', 'T2', 'MC1', 'MC2', 'T1', 'TB5', 'TB6']
    expect(new Set(ids.map(deviceSummaryColor))).toHaveLength(ids.length)
  })

  it('creates every new wire in yellow and lets the user change its color', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<WiringPage problem={trainingDetail} />)
    await screen.findByRole('img', { name: '제어함 결선판' })
    await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
    await user.click(screen.getByRole('button', { name: 'MC1-4 단자' }))
    const wire = screen.getByRole('button', { name: 'X1-1에서 MC1-4로 연결된 전선' })
    expect(wire.querySelector('.wire-visible')).toHaveStyle({ stroke: '#e0a500' })
    await user.click(wire)
    await user.selectOptions(screen.getByLabelText('물리 전선 색상'), 'black')
    expect(wire.querySelector('.wire-visible')).toHaveStyle({ stroke: '#171b22' })
  })

  it('keeps compact summary labels at the original position and shows only slot numbers', () => {
    const board = trainingBoardData as unknown as BoardDefinition
    const mc2 = board.items.find((item) => item.item_id === 'MC2')!
    const topPins = mc2.pins.filter((pin) => pin.side === 'top')
    expect(summaryLabelY(topPins[0])).toBe(482)
    expect(summaryLabelY(topPins[1])).toBe(482)
    const bottomPins = mc2.pins.filter((pin) => pin.side === 'bottom')
    expect(summaryLabelY(bottomPins[0])).toBe(701)
    expect(summaryLabelY(bottomPins[1])).toBe(701)
    expect(terminalSlotLabel('TB5-04')).toBe('4')
    expect(terminalSlotLabel('EOCR-L1')).toBe('L1')
  })

  it('restores draft, submits feedback and prevents duplicate connection', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<WiringPage problem={trainingDetail} />)
    await screen.findByRole('img', { name: '제어함 결선판' })
    await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
    await user.click(screen.getByRole('button', { name: 'MC1-4 단자' }))
    await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
    await user.click(screen.getByRole('button', { name: 'MC1-4 단자' }))
    expect(screen.getByRole('alert')).toHaveTextContent('이미 연결된 단자')
    await user.click(screen.getByRole('button', { name: '결선 제출' }))
    await waitFor(() => expect(screen.getByText('누락 또는 잘못 연결된 단자를 확인해 주세요.')).toBeInTheDocument())
  })
})
