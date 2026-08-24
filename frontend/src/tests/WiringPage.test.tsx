import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import trainingBoardData from '../../../problems/training_socket_demo_001/board.json'
import type { BoardDefinition } from '../api/client'
import { BoardItemBody, boardItemLabelArea, buildExternalWireLayouts, buildTerminalSummary, deviceSummaryColor, isDualFuseBoardItem, summaryLabelY, terminalSlotLabel } from '../features/wiring/components/WiringBoard'
import { calculatePanDelta } from '../components/circuit/useSvgViewport'
import { buildConnectionEndpointOffsets, pathHasSelfOverlap, routeConnection, routeConnections } from '../features/wiring/engine/orthogonalRouter'
import { terminalBlockBank, terminalBlockUsage } from '../features/wiring/engine/terminalCapacity'
import { WiringPage } from '../pages/WiringPage'
import { installApiMock, trainingDetail, wiringBoard } from './mockApi'

afterEach(() => {
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); window.localStorage.clear()
})

describe('제어함 결선', () => {
  it('renders the four-terminal dual fuse from source with two visible cartridges', () => {
    const fuse = {
      item_id: 'F', label: 'F', item_type: 'component' as const, socket_type_id: null, row: 1,
      x: 100, y: 100, width: 120, height: 150,
      label_area: { x: 145, y: 160, width: 30, height: 22 },
      pins: [
        { terminal_id: 'F-1', label: '1', number: 1, side: 'top' as const, x: 135, y: 100, max_connections: 2, enabled: true, terminal_role: 'functional' as const },
        { terminal_id: 'F-3', label: '3', number: 3, side: 'top' as const, x: 185, y: 100, max_connections: 2, enabled: true, terminal_role: 'functional' as const },
        { terminal_id: 'F-2', label: '2', number: 2, side: 'bottom' as const, x: 135, y: 250, max_connections: 2, enabled: true, terminal_role: 'functional' as const },
        { terminal_id: 'F-4', label: '4', number: 4, side: 'bottom' as const, x: 185, y: 250, max_connections: 2, enabled: true, terminal_role: 'functional' as const },
      ],
    }
    expect(isDualFuseBoardItem(fuse)).toBe(true)
    const { container } = render(<svg><BoardItemBody item={fuse} /></svg>)
    expect(container.querySelector('.dual-fuse-holder')).toBeInTheDocument()
    expect(container.querySelectorAll('.dual-fuse-cartridge')).toHaveLength(2)
    expect(container.querySelectorAll('.dual-fuse-channel')).toHaveLength(2)
  })

  it('shows the stage-one socket-number draft in a read-only reference without toolbar buttons', async () => {
    installApiMock()
    window.localStorage.setItem('electrician.circuitDraft.training_socket_demo_001.v1', JSON.stringify({
      'SQ-VR1-C1': { upper: 6, lower: 3 },
    }))
    const user = userEvent.setup()
    render(<MemoryRouter><WiringPage problem={trainingDetail} /></MemoryRouter>)

    const diagram = await screen.findByRole('img', { name: '회로도 분석 참고창' })
    expect(screen.getByText('1 / 1 입력')).toBeInTheDocument()
    expect(diagram.querySelectorAll('.answer-marker.entered')).toHaveLength(2)
    expect(diagram.querySelector('.answer-marker.entered')?.textContent).toBe('6')
    expect(within(diagram).queryByRole('button', { name: /VR1.*선택/ })).not.toBeInTheDocument()

    expect(screen.queryByLabelText('참고 회로도 보기 도구')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '확대' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '화면 맞춤' })).not.toBeInTheDocument()
  })

  it('renders symmetric 8P and 12P bases and connects exact terminals', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter><WiringPage problem={trainingDetail} /></MemoryRouter>)
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
    expect(screen.getByText('1번째 연결')).toBeInTheDocument()
    expect(screen.getByLabelText('X1-1 상대 단자 목록')).toHaveTextContent('MC1-4')
  })

  it('connects an external device lead to a freely selected TB terminal', async () => {
    const tbPin = { terminal_id: 'TB5-01', label: '1', number: 1, side: 'bottom' as const, x: 80, y: 100, max_connections: 2, enabled: true, terminal_role: 'free_junction' as const }
    const board: BoardDefinition = {
      ...wiringBoard,
      items: [{ item_id: 'TB5', label: 'TB5', item_type: 'terminal_block', socket_type_id: null, row: 0, x: 55, y: 40, width: 50, height: 60, pins: [tbPin], label_area: { x: 60, y: 55, width: 40, height: 22 } }, ...wiringBoard.items],
    }
    const detail = {
      ...trainingDetail,
      wiring_semantics: { schema_version: '1.0' as const, extra_jumper_policy: 'warning' as const, external_devices: [{ device_id: 'PB0', label: 'PB0 정지', placement: 'top' as const, terminals: [{ terminal_id: 'PB0-1', label: '1', terminal_role: 'external' as const, operation_terminal_id: 'TB5-05', max_connections: 1 as const, wire_color: 'yellow' as const }] }] },
    }
    installApiMock({ board })
    const user = userEvent.setup()
    render(<MemoryRouter><WiringPage problem={detail} /></MemoryRouter>)
    const externalTray = await screen.findByRole('region', { name: '외부 기구선' })
    expect(externalTray.parentElement).toHaveClass('has-external-wiring')
    await user.click(screen.getByRole('button', { name: /PB0-1 외부 기구선/ }))
    await user.click(screen.getByRole('button', { name: 'TB5-01 단자' }))
    expect(screen.getByRole('button', { name: 'PB0-1에서 TB5-01로 연결된 전선' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /PB0-1 외부 기구선/ })).toHaveTextContent('TB5-01')
  })

  it('shows metadata-driven NO/NC badges without hiding terminal numbers or blocking clicks', async () => {
    const externalDevice = (device_id: string, label: string, contact_type?: 'NO' | 'NC') => ({
      device_id, label, placement: 'top' as const, contact_type,
      terminals: [1, 2].map((number) => ({ terminal_id: `${device_id}-${number}`, label: String(number), terminal_role: 'external' as const, operation_terminal_id: null, max_connections: 1 as const, wire_color: 'yellow' as const })),
    })
    const detail = {
      ...trainingDetail,
      wiring_semantics: { schema_version: '1.0' as const, extra_jumper_policy: 'warning' as const, external_devices: [
        externalDevice('PB0', 'PB0 정지', 'NC'), externalDevice('PB1', 'PB1 기동', 'NO'), externalDevice('PB2', 'PB2 기동', 'NO'), externalDevice('UNMARKED', '메타데이터 없음'),
      ] },
    }
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter><WiringPage problem={detail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '제어함 결선판' })

    expect(screen.getByRole('article', { name: 'PB0 정지, 평상시 닫힘(NC)' })).toHaveTextContent('NC')
    expect(screen.getByRole('article', { name: 'PB1 기동, 평상시 열림(NO)' })).toHaveTextContent('NO')
    expect(screen.getByRole('article', { name: 'PB2 기동, 평상시 열림(NO)' })).toHaveTextContent('NO')
    expect(screen.getByRole('article', { name: '메타데이터 없음' }).querySelector('.contact-type-badge')).toBeNull()
    const pb0Terminal = screen.getByRole('button', { name: /PB0-1 외부 기구선/ })
    expect(pb0Terminal).toHaveTextContent('PB0-1')
    expect(screen.getByRole('button', { name: /PB0-2 외부 기구선/ })).toHaveTextContent('PB0-2')
    await user.click(pb0Terminal)
    expect(pb0Terminal).toHaveClass('selected')
  })

  it('separates two external TB leads and recenters the remaining lead after deletion', async () => {
    const tbPin = { terminal_id: 'TB5-01', label: '1', number: 1, side: 'bottom' as const, x: 80, y: 100, max_connections: 2, enabled: true, terminal_role: 'free_junction' as const }
    const board: BoardDefinition = {
      ...wiringBoard,
      items: [{ item_id: 'TB5', label: 'TB5', item_type: 'terminal_block', socket_type_id: null, row: 0, x: 55, y: 40, width: 50, height: 60, pins: [tbPin], label_area: { x: 60, y: 55, width: 40, height: 22 } }, ...wiringBoard.items],
    }
    const detail = {
      ...trainingDetail,
      wiring_semantics: { schema_version: '1.0' as const, extra_jumper_policy: 'warning' as const, external_devices: [
        { device_id: 'PB0', label: 'PB0 정지', placement: 'top' as const, terminals: [{ terminal_id: 'PB0-1', label: '1', terminal_role: 'external' as const, operation_terminal_id: null, max_connections: 1 as const, wire_color: 'yellow' as const }] },
        { device_id: 'PB1', label: 'PB1 기동', placement: 'top' as const, terminals: [{ terminal_id: 'PB1-1', label: '1', terminal_role: 'external' as const, operation_terminal_id: null, max_connections: 1 as const, wire_color: 'yellow' as const }] },
      ] },
    }
    installApiMock({ board })
    const user = userEvent.setup()
    render(<MemoryRouter><WiringPage problem={detail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '제어함 결선판' })
    for (const externalId of ['PB0-1', 'PB1-1']) {
      await user.click(screen.getByRole('button', { name: new RegExp(`${externalId} 외부 기구선`) }))
      await user.click(screen.getByRole('button', { name: 'TB5-01 단자' }))
    }

    const first = screen.getByRole('button', { name: 'PB0-1에서 TB5-01로 연결된 전선' })
    const second = screen.getByRole('button', { name: 'PB1-1에서 TB5-01로 연결된 전선' })
    expect(first.querySelector('.wire-visible')?.getAttribute('points')).not.toBe(second.querySelector('.wire-visible')?.getAttribute('points'))
    await user.click(first)
    expect(first).toHaveClass('selected')
    await user.click(screen.getByRole('button', { name: '선택 전선 삭제' }))
    expect(screen.queryByRole('button', { name: 'PB0-1에서 TB5-01로 연결된 전선' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'PB1-1에서 TB5-01로 연결된 전선' }).querySelector('.wire-visible')).toHaveAttribute('points', '80,40 80,10')
  })

  it('uses stable left-right external ports for TB5 and TB6', () => {
    const board = trainingBoardData as unknown as BoardDefinition
    const connections = [
      { from: 'PB0-1', to: 'TB5-01', wire_color: 'yellow' as const, pair_display_color: '#64748b' },
      { from: 'PB1-1', to: 'TB5-01', wire_color: 'yellow' as const, pair_display_color: '#64748b' },
      { from: 'GL-1', to: 'TB6-01', wire_color: 'yellow' as const, pair_display_color: '#64748b' },
      { from: 'RL-1', to: 'TB6-01', wire_color: 'yellow' as const, pair_display_color: '#64748b' },
    ]
    const layouts = buildExternalWireLayouts(board, connections, new Set(['PB0-1', 'PB1-1', 'GL-1', 'RL-1']))
    const tb5 = layouts.filter((wire) => wire.boardTerminalId === 'TB5-01')
    const tb6 = layouts.filter((wire) => wire.boardTerminalId === 'TB6-01')
    expect(tb5).toHaveLength(2)
    expect(tb6).toHaveLength(2)
    expect(tb5[0].points).not.toBe(tb5[1].points)
    expect(tb6[0].points).not.toBe(tb6[1].points)
    expect(tb5.every((wire) => Number(wire.points.split(/[ ,]/)[1]) < Number(wire.points.split(/[ ,]/)[3]))).toBe(false)
    expect(tb6.every((wire) => Number(wire.points.split(/[ ,]/)[1]) < Number(wire.points.split(/[ ,]/)[3]))).toBe(true)
    const single = buildExternalWireLayouts(board, connections.slice(1, 2), new Set(['PB1-1']))[0]
    const tb5Pin = board.items.find((item) => item.item_id === 'TB5')!.pins.find((pin) => pin.terminal_id === 'TB5-01')!
    expect(single.points.startsWith(`${tb5Pin.x},`)).toBe(true)
  })

  it('maps compact diagram pointer motion to viewBox units without changing the main default', () => {
    const compact = calculatePanDelta({ dx: 20, dy: 10, zoom: 2, panSpeed: 2.4, clientWidth: 300, clientHeight: 200, viewBoxWidth: 1200, viewBoxHeight: 800, mapClientToViewBox: true })
    const previous = calculatePanDelta({ dx: 20, dy: 10, zoom: 2, panSpeed: 2.4, clientWidth: 300, clientHeight: 200, viewBoxWidth: 1200, viewBoxHeight: 800, mapClientToViewBox: false })
    expect(compact.x).toBe(previous.x * 4)
    expect(compact.y).toBe(previous.y * 4)
    const main = calculatePanDelta({ dx: 20, dy: 10, zoom: 2, panSpeed: 1, clientWidth: 300, clientHeight: 200, viewBoxWidth: 1200, viewBoxHeight: 800, mapClientToViewBox: false })
    expect(main).toEqual({ x: 10, y: 5 })
  })

  it('counts two external and two internal TB wires in separate physical banks', () => {
    const externalIds = new Set(['PB0-1', 'PB1-1'])
    const connections = [
      { from: 'PB0-1', to: 'TB5-01' },
      { from: 'PB1-1', to: 'TB5-01' },
      { from: 'TB5-01', to: 'MC1-4' },
      { from: 'TB5-01', to: 'MC2-4' },
    ]
    expect(terminalBlockUsage(connections, 'TB5-01', externalIds)).toEqual({ external: 2, internal: 2 })
    expect(terminalBlockBank({ from: 'PB0-1', to: 'TB5-01' }, 'TB5-01', externalIds)).toBe('external')
    expect(terminalBlockBank({ from: 'TB5-01', to: 'MC1-4' }, 'TB5-01', externalIds)).toBe('internal')
  })

  it('keeps terminal-block labels away from upper and lower slot numbers', () => {
    const board = trainingBoardData as unknown as BoardDefinition
    const tb5 = board.items.find((item) => item.item_id === 'TB5')!
    const tb6 = board.items.find((item) => item.item_id === 'TB6')!
    const tb5Label = boardItemLabelArea(tb5)
    const tb6Label = boardItemLabelArea(tb6)

    expect(tb5Label.y).toBeLessThan(tb5.label_area.y)
    expect(tb5Label.y + tb5Label.height).toBeLessThan(Math.min(...tb5.pins.map((pin) => pin.y)) - 16)
    expect(tb6Label.y).toBeGreaterThan(tb6.label_area.y)
    expect(tb6Label.y).toBeGreaterThan(Math.max(...tb6.pins.map((pin) => pin.y)) + 25)
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

  it('lets an installed empty-board device wire leave its legacy padded endpoint area', () => {
    const board: BoardDefinition = {
      ...wiringBoard,
      forbidden_areas: wiringBoard.items.map((item) => ({
        area_id: `DEVICE-${item.item_id}`,
        x: item.x - 12,
        y: item.y - 12,
        width: item.width + 24,
        height: item.height + 24,
      })),
    }
    const route = routeConnection(board, {
      from: 'X1-1', to: 'MC1-4', wire_color: 'yellow', pair_display_color: '#64748b',
    })
    expect(route.points.length).toBeGreaterThanOrEqual(4)
    expect(route.points[0]).toEqual({ x: 200, y: 340 })
    expect(route.points.at(-1)).toEqual({ x: 576, y: 500 })
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

  it('skips non-board external endpoints in the internal orthogonal router', () => {
    const routed = routeConnections(trainingBoardData as unknown as BoardDefinition, [
      { from: 'PWR-L1', to: 'TB5-01', wire_color: 'brown', pair_display_color: '#64748b' },
      { from: 'TB5-01', to: 'MCCB-L1', wire_color: 'brown', pair_display_color: '#64748b' },
    ])
    expect(routed).toHaveLength(1)
    expect(routed[0].from).toBe('TB5-01')
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
    expect(summary.get('X1-1')).toEqual([{ other: 'MC1-4', slot: '4', color: deviceSummaryColor('MC1'), connectionIndex: 0 }])
    expect(summary.get('MC1-4')).toEqual([{ other: 'X1-1', slot: '1', color: deviceSummaryColor('X1'), connectionIndex: 0 }])
  })

  it('shows only slot labels for MCCB, fuse and terminal-block connections', () => {
    const baseItem = wiringBoard.items[0]
    const basePin = baseItem.pins[0]
    const board = {
      ...wiringBoard,
      items: [
        { ...baseItem, item_id: 'MCCB', pins: [{ ...basePin, terminal_id: 'MCCB-L1', label: 'L1', number: null }] },
        { ...baseItem, item_id: 'FUSE', pins: [{ ...basePin, terminal_id: 'FUSE-L1', label: 'L1', number: null }] },
        { ...baseItem, item_id: 'TB5', pins: [{ ...basePin, terminal_id: 'TB5-01', label: '1', number: 1 }] },
      ],
    } as BoardDefinition
    const summary = buildTerminalSummary(board, [
      { from: 'MCCB-L1', to: 'FUSE-L1', wire_color: 'brown', pair_display_color: '#000' },
      { from: 'FUSE-L1', to: 'TB5-01', wire_color: 'yellow', pair_display_color: '#000' },
    ])
    expect(summary.get('MCCB-L1')?.[0].slot).toBe('L1')
    expect(summary.get('FUSE-L1')?.[0].slot).toBe('L1')
    expect(summary.get('FUSE-L1')?.[1].slot).toBe('1')
    expect(JSON.stringify([...summary.values()])).not.toContain('"slot":"MCCB-L1"')
    expect(JSON.stringify([...summary.values()])).not.toContain('"slot":"TB5-01"')
  })

  it('keeps external device lead ids in terminal-block summaries', () => {
    const summary = buildTerminalSummary(wiringBoard, [
      { from: 'PB0-1', to: 'X1-1', wire_color: 'yellow', pair_display_color: '#000' },
    ])
    expect(summary.get('X1-1')?.[0].slot).toBe('PB0-1')
  })

  it('separates the first and second wire to the left and right of a shared pin', () => {
    const board = trainingBoardData as unknown as BoardDefinition
    const connections = [
      { from: 'X1-1', to: 'MC1-4', wire_color: 'yellow' as const, pair_display_color: '#64748b' },
      { from: 'X1-1', to: 'MC2-5', wire_color: 'yellow' as const, pair_display_color: '#64748b' },
    ]
    const offsets = buildConnectionEndpointOffsets(connections)
    expect(offsets).toEqual([{ from: -5, to: 0 }, { from: 5, to: 0 }])
    const routes = routeConnections(board, connections)
    expect(routes[0].points[0]).toEqual({ x: 807.5, y: 370 })
    expect(routes[1].points[0]).toEqual({ x: 817.5, y: 370 })
  })

  it('shows +1 for two wires on one summary slot and lists both relative terminals', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter><WiringPage problem={trainingDetail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '제어함 결선판' })
    await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
    await user.click(screen.getByRole('button', { name: 'MC1-4 단자' }))
    await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
    await user.click(screen.getByRole('button', { name: 'MC1-5 단자' }))
    await user.click(screen.getByRole('button', { name: '요약 모드' }))
    expect(screen.getByText('+1')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'X1-1에서 MC1-4, MC1-5로 연결된 요약 표시' }))
    const list = screen.getByLabelText('X1-1 상대 단자 목록')
    expect(within(list).getByText('MC1-4')).toBeInTheDocument()
    expect(within(list).getByText('MC1-5')).toBeInTheDocument()
  })

  it('blocks a third wire immediately when a socket terminal already has two', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter><WiringPage problem={trainingDetail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '제어함 결선판' })
    for (const target of ['MC1-4', 'MC1-5']) {
      await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
      await user.click(screen.getByRole('button', { name: `${target} 단자` }))
    }
    await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
    await user.click(screen.getByRole('button', { name: 'MC1-6 단자' }))
    expect(screen.getByRole('alert')).toHaveTextContent('X1-1 단자에는 전선을 최대 2개까지 연결할 수 있습니다.')
    expect(screen.queryByRole('button', { name: 'X1-1에서 MC1-6로 연결된 전선' })).not.toBeInTheDocument()
  })

  it('assigns distinct summary colors including T1, TB5 and TB6', () => {
    const ids = ['MCCB', 'EOCR', 'F', 'X1', 'X2', 'T2', 'MC1', 'MC2', 'T1', 'TB5', 'TB6']
    expect(new Set(ids.map(deviceSummaryColor))).toHaveLength(ids.length)
  })

  it('creates every new wire in yellow and lets the user change its color', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter><WiringPage problem={trainingDetail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '제어함 결선판' })
    await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
    await user.click(screen.getByRole('button', { name: 'MC1-4 단자' }))
    const wire = screen.getByRole('button', { name: 'X1-1에서 MC1-4로 연결된 전선' })
    expect(wire.querySelector('.wire-visible')).toHaveStyle({ stroke: '#e0a500' })
    await user.click(wire)
    expect(wire).toHaveClass('selected')
    expect(wire.querySelector('.wire-depth')).not.toBeInTheDocument()
    expect(wire.querySelector('.wire-selection-halo')).toBeInTheDocument()
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
    render(<MemoryRouter><WiringPage problem={trainingDetail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '제어함 결선판' })
    await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
    await user.click(screen.getByRole('button', { name: 'MC1-4 단자' }))
    await user.click(screen.getByRole('button', { name: 'X1-1 단자' }))
    await user.click(screen.getByRole('button', { name: 'MC1-4 단자' }))
    expect(screen.getByRole('alert')).toHaveTextContent('이미 연결된 단자')
    await user.click(screen.getByRole('button', { name: '결선 제출' }))
    await waitFor(() => expect(screen.getByText('누락 또는 잘못 연결된 단자를 확인해 주세요.')).toBeInTheDocument())
  })

  it('moves to operation only after a correct gradable submission', async () => {
    installApiMock({ wiringResult: { attempt_id: 1, gradable: true, overall_correct: true, required_count: 0, correct_count: 0, missing_connections: [], extra_connections: [], forbidden_connections: [], message: '모든 결선이 정확합니다.' } })
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/wiring']}><Routes><Route path="/wiring" element={<WiringPage problem={trainingDetail} />} /><Route path="/operation" element={<h2>동작시험 이동 완료</h2>} /></Routes></MemoryRouter>)
    await screen.findByRole('img', { name: '제어함 결선판' })
    await user.click(screen.getByRole('button', { name: '결선 제출' }))
    expect(await screen.findByRole('heading', { name: '동작시험 이동 완료' })).toBeInTheDocument()
  })

  it('offers a preview instead of automatic success for an ungradable problem', async () => {
    installApiMock({ wiringResult: { attempt_id: 1, gradable: false, overall_correct: null, required_count: 0, correct_count: 0, missing_connections: [], extra_connections: [], forbidden_connections: [], message: '이 문제의 배선 정답은 아직 검증되지 않아 채점할 수 없습니다.' } })
    const user = userEvent.setup()
    render(<MemoryRouter><WiringPage problem={trainingDetail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '제어함 결선판' })
    await user.click(screen.getByRole('button', { name: '결선 제출' }))
    expect(await screen.findByRole('button', { name: '동작시험 화면 미리보기' })).toBeInTheDocument()
    expect(screen.getByText('이 문제의 배선 정답은 아직 검증되지 않아 채점할 수 없습니다.')).toBeInTheDocument()
  })
})
