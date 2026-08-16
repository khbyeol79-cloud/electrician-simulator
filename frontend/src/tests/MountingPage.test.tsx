import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DeviceMountingPage } from '../pages/DeviceMountingPage'
import { installApiMock, trainingDetail } from './mockApi'

afterEach(() => {
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); window.localStorage.clear()
})

describe('기구 장착', () => {
  it('shows the saved wiring as read-only and renders the problem device shelf', async () => {
    installApiMock({ wiringDraft: [{ from: 'X1-1', to: 'MC1-4', wire_color: 'yellow', pair_display_color: '#64748b' }] })
    render(<DeviceMountingPage problem={trainingDetail} />)

    const board = await screen.findByRole('img', { name: '기구 장착 제어함' })
    expect(screen.getByText('X1 보조릴레이')).toBeInTheDocument()
    expect(screen.getByText('T1 타이머')).toBeInTheDocument()
    expect(screen.getByText('MC1 12P 릴레이')).toBeInTheDocument()
    expect(board.querySelectorAll('.board-wire.readonly')).toHaveLength(1)
    expect(screen.queryByRole('button', { name: /연결된 전선/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /단자$/ })).not.toBeInTheDocument()
  })

  it('mounts by click, moves by selecting another socket and supports undo and detach', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<DeviceMountingPage problem={trainingDetail} />)
    await screen.findByRole('img', { name: '기구 장착 제어함' })

    await user.click(screen.getByRole('button', { name: /X1 보조릴레이/ }))
    await user.click(screen.getByRole('button', { name: 'X1 빈 장착 소켓' }))
    expect(screen.getByRole('button', { name: 'X1 소켓에 장착된 X1 보조릴레이' })).toBeInTheDocument()
    expect(screen.getByText('X1 장착')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '선택 기구 분리' }))
    expect(screen.getByRole('button', { name: 'X1 빈 장착 소켓' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '실행 취소' }))
    expect(screen.getByRole('button', { name: 'X1 소켓에 장착된 X1 보조릴레이' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '다시 실행' }))
    expect(screen.getByRole('button', { name: 'X1 빈 장착 소켓' })).toBeInTheDocument()
  })

  it('mounts a device with drag and drop', async () => {
    installApiMock()
    render(<DeviceMountingPage problem={trainingDetail} />)
    await screen.findByRole('img', { name: '기구 장착 제어함' })
    const card = screen.getByRole('button', { name: /MC1 12P 릴레이/ })
    const target = screen.getByRole('button', { name: 'MC1 빈 장착 소켓' })
    const values = new Map<string, string>()
    const dataTransfer = {
      effectAllowed: 'none',
      setData: (type: string, value: string) => values.set(type, value),
      getData: (type: string) => values.get(type) ?? '',
    }
    fireEvent.dragStart(card, { dataTransfer })
    fireEvent.dragOver(target, { dataTransfer })
    fireEvent.drop(target, { dataTransfer })
    expect(screen.getByRole('button', { name: 'MC1 소켓에 장착된 MC1 12P 릴레이' })).toBeInTheDocument()
  })

  it('supports keyboard selection and mounting', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<DeviceMountingPage problem={trainingDetail} />)
    await screen.findByRole('img', { name: '기구 장착 제어함' })
    const card = screen.getByRole('button', { name: /X1 보조릴레이/ })
    card.focus()
    await user.keyboard('{Enter}')
    const target = screen.getByRole('button', { name: 'X1 빈 장착 소켓' })
    target.focus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('button', { name: 'X1 소켓에 장착된 X1 보조릴레이' })).toBeInTheDocument()
  })

  it('rejects incompatible socket sizes and same-size disallowed device types', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<DeviceMountingPage problem={trainingDetail} />)
    await screen.findByRole('img', { name: '기구 장착 제어함' })

    await user.click(screen.getByRole('button', { name: /T1 타이머/ }))
    await user.click(screen.getByRole('button', { name: 'MC1 빈 장착 소켓' }))
    expect(screen.getByRole('alert')).toHaveTextContent('8P 소켓용 기구는 12P 소켓에 장착할 수 없습니다.')
    await user.click(screen.getByRole('button', { name: 'X1 빈 장착 소켓' }))
    expect(screen.getByRole('alert')).toHaveTextContent('X1 위치에는 T1 타이머 기구를 장착할 수 없습니다.')
  })

  it('restores only a matching-version draft and submits grading feedback', async () => {
    installApiMock({ mountingDraft: [{ mount_device_id: 'DEVICE-X1', socket_id: 'X1' }] })
    const user = userEvent.setup()
    render(<DeviceMountingPage problem={trainingDetail} />)
    expect(await screen.findByRole('button', { name: 'X1 소켓에 장착된 X1 보조릴레이' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /MC1 12P 릴레이/ }))
    await user.click(screen.getByRole('button', { name: 'MC1 빈 장착 소켓' }))
    await user.click(screen.getByRole('button', { name: '기구 장착 제출' }))
    await waitFor(() => expect(screen.getByText('모든 기구의 장착 위치가 정확합니다.')).toBeInTheDocument())
    expect(screen.getByText('정상 2/2')).toBeInTheDocument()
  })

  it('ignores an old-version mounting draft', async () => {
    installApiMock({ mountingDraft: [{ mount_device_id: 'DEVICE-X1', socket_id: 'X1' }], mountingDraftVersion: 2 })
    render(<DeviceMountingPage problem={trainingDetail} />)
    await screen.findByRole('img', { name: '기구 장착 제어함' })
    expect(screen.getByRole('button', { name: 'X1 빈 장착 소켓' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('이전 문제 버전의 장착 임시저장은 적용하지 않았습니다.')
  })
})
