import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
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

  it('uses an orthogonal outer route between rows', () => {
    const route = routeConnection(wiringBoard, { from: 'X1-1', to: 'MC1-4', wire_color: 'yellow', pair_display_color: '#2563eb' })
    expect(route.points.slice(1).every((point, index) => point.x === route.points[index].x || point.y === route.points[index].y)).toBe(true)
    expect(route.points.some((point) => point.x === wiringBoard.routing_margin)).toBe(true)
    expect(route.points[0]).toEqual({ x: 200, y: 340 })
    expect(route.points.at(-1)).toEqual({ x: 576, y: 500 })
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
