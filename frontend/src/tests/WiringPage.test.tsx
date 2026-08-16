import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import trainingBoardData from '../../../problems/training_socket_demo_001/board.json'
import type { BoardDefinition } from '../api/client'
import { buildTerminalSummary, deviceSummaryColor, summaryLabelY } from '../features/wiring/components/WiringBoard'
import { routeConnection } from '../features/wiring/engine/orthogonalRouter'
import { WiringPage } from '../pages/WiringPage'
import { installApiMock, trainingDetail, wiringBoard } from './mockApi'

afterEach(() => {
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); window.localStorage.clear()
})

describe('제어함 결선', () => {
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
    expect(screen.getAllByText(/MC1-4|X1-1/).length).toBeGreaterThan(1)
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

  it('does not push a later direct connection below the center of the socket gap', () => {
    const route = routeConnection(trainingBoardData as unknown as BoardDefinition, {
      from: 'X1-1', to: 'MC2-5', wire_color: 'yellow', pair_display_color: '#2563eb',
    }, 4)
    expect(route.points[1].y).toBe(435)
    expect(route.points[2].y).toBe(435)
  })

  it('uses an outer route only when a device blocks the direct row gap', () => {
    const blockedBoard = {
      ...wiringBoard,
      forbidden_areas: [{ area_id: 'middle_blocker', x: 330, y: 360, width: 80, height: 90 }],
    }
    const route = routeConnection(blockedBoard, { from: 'X1-1', to: 'MC1-4', wire_color: 'yellow', pair_display_color: '#2563eb' })
    expect(route.points.some((point) => point.x > blockedBoard.routing_margin && point.x < 100)).toBe(true)
    expect(route.points.slice(1).every((point, index) => point.x === route.points[index].x || point.y === route.points[index].y)).toBe(true)
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
  })

  it('uses the opposite device color on each terminal in summary mode', () => {
    const summary = buildTerminalSummary(wiringBoard, [
      { from: 'X1-1', to: 'MC1-4', wire_color: 'yellow', pair_display_color: '#64748b' },
    ])
    expect(summary.get('X1-1')).toEqual({ other: 'MC1-4', color: deviceSummaryColor('MC1') })
    expect(summary.get('MC1-4')).toEqual({ other: 'X1-1', color: deviceSummaryColor('X1') })
  })

  it('assigns distinct summary colors to the nine control devices', () => {
    const ids = ['MCCB', 'EOCR', 'F', 'X1', 'X2', 'T2', 'MC1', 'MC2', 'T1']
    expect(new Set(ids.map(deviceSummaryColor))).toHaveLength(ids.length)
  })

  it('alternates adjacent summary labels between two vertical tiers', () => {
    const board = trainingBoardData as unknown as BoardDefinition
    const mc2 = board.items.find((item) => item.item_id === 'MC2')!
    const topPins = mc2.pins.filter((pin) => pin.side === 'top')
    expect(summaryLabelY(topPins[0], 0)).toBe(482)
    expect(summaryLabelY(topPins[1], 1)).toBe(455)
    expect(summaryLabelY(topPins[2], 2)).toBe(482)
    const bottomPins = mc2.pins.filter((pin) => pin.side === 'bottom')
    expect(summaryLabelY(bottomPins[0], 0)).toBe(701)
    expect(summaryLabelY(bottomPins[1], 1)).toBe(728)
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
