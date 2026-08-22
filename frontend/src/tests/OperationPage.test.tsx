import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OperationTestPage } from '../pages/OperationTestPage'
import { installApiMock, trainingDetail } from './mockApi'
import forwardBoardData from '../../../problems/forward_reverse_interlock_demo_001/board.json'
import forwardAnswerData from '../../../docs/test-answer-forward-reverse-0.9.3.json'
import type { BoardDefinition, WiringConnection } from '../api/client'
import { boardItemLabelArea } from '../features/wiring/components/WiringBoard'

afterEach(() => {
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); window.localStorage.clear()
})

const connection = { from: 'X1-1', to: 'MC1-4', wire_color: 'yellow' as const, pair_display_color: '#64748b' }
const readySetup = {
  operation_ready: true, preview_allowed: false, wiring_source: 'accepted_submission' as const,
  wiring_snapshot: { attempt_id: 7, problem_version: 1, connections: [connection] },
  message: '정상 결선 제출 스냅샷으로 동작시험을 시작할 수 있습니다.',
}

describe('동작시험', () => {
  it('renders the forward-reverse problem preview before any wiring exists', async () => {
    installApiMock({ board: forwardBoardData as unknown as BoardDefinition, operationSetup: { board: forwardBoardData as unknown as BoardDefinition, wiring_snapshot: null, wiring_draft: null, wiring_source: 'none', operation_ready: false, preview_allowed: true } })
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)

    const board = await screen.findByRole('img', { name: '동작시험 준비 제어함' })
    expect(board.querySelectorAll('.board-wire.readonly')).toHaveLength(0)
    expect(screen.getByRole('heading', { name: '읽기 전용 미리보기' })).toBeInTheDocument()
  })

  it('renders the accepted forward-reverse snapshot with external leads outside TB5 and TB6', async () => {
    const connections = forwardAnswerData.connections.map((item) => ({ ...item, pair_display_color: '#64748b' })) as WiringConnection[]
    installApiMock({ board: forwardBoardData as unknown as BoardDefinition, operationSetup: { board: forwardBoardData as unknown as BoardDefinition, wiring_snapshot: { attempt_id: 19, problem_version: 1, connections }, wiring_source: 'accepted_submission', operation_ready: true, preview_allowed: false } })
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)

    const board = await screen.findByRole('img', { name: '동작시험 준비 제어함' })
    expect(board.querySelectorAll('.board-wire.readonly')).toHaveLength(44)
    expect(board.querySelectorAll('.board-wire.external')).toHaveLength(18)
    expect(within(board).getByText('PWR-L1')).toBeInTheDocument()
    expect(within(board).getByText('RL-2')).toBeInTheDocument()
    expect(within(board).getByText('M1-W')).toBeInTheDocument()
    const rlWire = within(board).getByText('RL-2').parentElement?.querySelector('.wire-visible')?.getAttribute('points')
    const glWire = within(board).getByText('GL-2').parentElement?.querySelector('.wire-visible')?.getAttribute('points')
    expect(rlWire).toBeTruthy()
    expect(glWire).toBeTruthy()
    expect(rlWire).not.toBe(glWire)
    const tb5 = (forwardBoardData as unknown as BoardDefinition).items.find((item) => item.item_id === 'TB5')!
    const tb6 = (forwardBoardData as unknown as BoardDefinition).items.find((item) => item.item_id === 'TB6')!
    const tb5Label = within(board).getByText(tb5.label).parentElement!
    const tb6Label = within(board).getByText(tb6.label).parentElement!
    expect(tb5Label.querySelector('rect')).toHaveAttribute('y', String(boardItemLabelArea(tb5).y))
    expect(tb6Label.querySelector('rect')).toHaveAttribute('y', String(boardItemLabelArea(tb6).y))
  })

  it('renders accepted wiring and fixed devices as read-only', async () => {
    installApiMock({ operationSetup: readySetup })
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)

    const board = await screen.findByRole('img', { name: '동작시험 준비 제어함' })
    expect(board.querySelectorAll('.board-wire.readonly')).toHaveLength(1)
    expect(within(board).getByLabelText('X1 보조릴레이 자동 삽입')).toBeInTheDocument()
    expect(screen.getByText(/정상 제출 스냅샷/)).toBeInTheDocument()
    expect(screen.getByText(/배선과 기구는 읽기 전용/)).toBeInTheDocument()
    expect(screen.queryByText('기구 보관함')).not.toBeInTheDocument()
  })

  it('blocks power in preview mode and keeps the board visible', async () => {
    installApiMock()
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '동작시험 준비 제어함' })
    expect(screen.getByRole('heading', { name: '읽기 전용 미리보기' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /전원 ON/ })).not.toBeInTheDocument()
    expect(screen.getByText(/실제 동작 데이터가 없어/)).toBeInTheDocument()
  })

  it('supports power, pointer pushbutton, maintained switch and keyboard release', async () => {
    const fetchMock = installApiMock({ operationSetup: readySetup })
    const user = userEvent.setup()
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)
    await user.click(await screen.findByRole('button', { name: '전원 ON' }))
    expect(await screen.findByRole('button', { name: '전원 OFF' })).toBeInTheDocument()

    const pb1 = screen.getByRole('button', { name: /PB1/ })
    fireEvent.pointerDown(pb1)
    await waitFor(() => expect(screen.getByText('M1 모터').parentElement).toHaveTextContent('정회전'))
    fireEvent.pointerUp(pb1)
    fireEvent.keyDown(pb1, { key: 'Enter' })
    fireEvent.keyUp(pb1, { key: 'Enter' })
    await user.click(screen.getByRole('button', { name: /LS1/ }))

    const bodies = fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST').map(([, init]) => String(init?.body))
    expect(bodies.some((body) => body.includes('press_control'))).toBe(true)
    expect(bodies.some((body) => body.includes('release_control'))).toBe(true)
    expect(bodies.some((body) => body.includes('toggle_control'))).toBe(true)
  })

  it('shows automatic operation check and can reset without changing wiring', async () => {
    installApiMock({ operationSetup: readySetup })
    const user = userEvent.setup()
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)
    await user.click(await screen.findByRole('button', { name: '자동 동작검사' }))
    expect(await screen.findByText('동작시험 완료')).toBeInTheDocument()
    expect(screen.getByText('2/2 통과')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '시험 초기화' }))
    expect(await screen.findByText('동작시험 초기화')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '동작시험 준비 제어함' }).querySelectorAll('.board-wire.readonly')).toHaveLength(1)
  })

  it('shows EOCR trip and reset controls as an educational simulation', async () => {
    installApiMock({ operationSetup: readySetup })
    const user = userEvent.setup()
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)
    await screen.findByRole('button', { name: 'EOCR 과부하 발생' })
    expect(screen.getByText(/실제 전류 측정이 아닌 교육용/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'EOCR 과부하 발생' }))
    expect(await screen.findByText('복귀 필요')).toBeInTheDocument()
    expect(screen.getByText('M1 모터').parentElement).toHaveTextContent('보호 정지')
    await user.click(screen.getByRole('button', { name: 'EOCR 복귀' }))
    await waitFor(() => expect(screen.getByText('M1 모터').parentElement).toHaveTextContent('정지'))
  })

  it('releases a momentary control on window pointer up', async () => {
    const fetchMock = installApiMock({ operationSetup: readySetup })
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)
    const pb1 = await screen.findByRole('button', { name: /PB1/ })
    fireEvent.pointerDown(pb1, { pointerId: 3 })
    fireEvent.pointerUp(window, { pointerId: 3 })
    await waitFor(() => {
      const bodies = fetchMock.mock.calls.filter(([, init]) => init?.method === 'POST').map(([, init]) => String(init?.body))
      expect(bodies.some((body) => body.includes('release_control'))).toBe(true)
    })
  })

  it('uses automatic board fit without zoom buttons and returns to the editable wiring stage', async () => {
    installApiMock({ operationSetup: readySetup })
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/operation']}><Routes><Route path="/operation" element={<OperationTestPage problem={trainingDetail} />} /><Route path="/wiring" element={<h2>제어함 결선 돌아옴</h2>} /></Routes></MemoryRouter>)
    await screen.findByRole('img', { name: '동작시험 준비 제어함' })
    expect(screen.queryByRole('button', { name: '확대' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '화면 맞춤' })).not.toBeInTheDocument()
    expect(screen.getByText(/화면 자동 맞춤/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '선택 전선 삭제' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '결선 화면으로 돌아가기' }))
    expect(screen.getByRole('heading', { name: '제어함 결선 돌아옴' })).toBeInTheDocument()
  })
})
