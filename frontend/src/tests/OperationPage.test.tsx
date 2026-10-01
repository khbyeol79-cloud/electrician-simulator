import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OperationTestPage, recentOperationEvents } from '../pages/OperationTestPage'
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
  it('opens the layout reference by default for public problems and allows switching back to the board', async () => {
    installApiMock({ operationSetup: readySetup })
    const user = userEvent.setup()
    render(<MemoryRouter><OperationTestPage problem={{ ...trainingDetail, problem_type: 'official' }} /></MemoryRouter>)
    expect(await screen.findByRole('button', { name: '배관·배치도' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.queryByRole('img', { name: '동작시험 준비 제어함' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '제어함 결선' }))
    expect(await screen.findByRole('img', { name: '동작시험 준비 제어함' })).toBeInTheDocument()
  })
  it('shows actual runtime changeover branches when the public problem has no contact definitions', async () => {
    const fetchMock = installApiMock({ operationSetup: readySetup })
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (input, init) => {
      const result = await original(input, init)
      if (String(input).endsWith('/operation-sessions')) {
        const state = await result.json()
        return { ...result, json: async () => ({ ...state,
          contacts: { 'FR-C1': 'closed', 'FLS-C1': 'closed' },
          changeover_positions: { 'FR-C1': 'no', 'FLS-C1': 'nc' },
        }) }
      }
      return result
    })
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)
    expect(await screen.findByText('FR-C1 · NC 열림 / NO 닫힘')).toBeInTheDocument()
    expect(screen.getByText('FLS-C1 · NC 닫힘 / NO 열림')).toBeInTheDocument()
    const left = screen.getByRole('complementary', { name: '기구 상태 패널' })
    expect(within(left).getByText('기구 상태')).toBeInTheDocument()
    expect(within(left).queryByLabelText('동작시험 조작부')).not.toBeInTheDocument()
    expect(screen.getByLabelText('동작시험 조작부').closest('.operation-panel')).toBeInTheDocument()
  })

  it('keeps significant actions visible when a flasher generates repeated transitions', () => {
    const events = [
      '전원을 투입했습니다.',
      'EOCR가 과부하로 트립되었습니다.',
      'FR 출력이 ON 구간으로 전환되었습니다.',
      'FR 출력이 OFF 구간으로 전환되었습니다.',
      'FR 출력이 ON 구간으로 전환되었습니다.',
      'EOCR를 복귀했습니다.',
    ]
    expect(recentOperationEvents(events)).toEqual([
      'EOCR를 복귀했습니다.',
      'FR 출력이 ON 구간으로 전환되었습니다.',
      'EOCR가 과부하로 트립되었습니다.',
      '전원을 투입했습니다.',
    ])
  })

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
    expect(screen.getByLabelText('평상시 닫힘(NC)')).toHaveTextContent('NC')
    expect(screen.getAllByLabelText('평상시 열림(NO)').length).toBeGreaterThanOrEqual(2)

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
    await user.click(screen.getByRole('button', { name: '전체 상태·타이머 초기화' }))
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

  it('reports public behavior satisfaction without a score in practice mode', async () => {
    installApiMock({ operationSetup: {
      ...readySetup,
      behavior_requirements: [
        { requirement_id: 'B_X1_START', label: 'X1 기동', scenario_id: 'PB1_SEQUENCE', scenario_label: 'PB1 계통', next_action: 'PB1을 조작하세요.' },
        { requirement_id: 'C_X2_START', label: 'X2 기동', scenario_id: 'PB2_SEQUENCE', scenario_label: 'PB2 계통', next_action: 'PB2를 조작하세요.' },
        { requirement_id: 'D_STOP_M1', label: 'STOP', scenario_id: 'STOP_SEQUENCE', scenario_label: 'STOP', next_action: 'PB0을 조작하세요.' },
        { requirement_id: 'E_EOCR_TRIP', label: 'EOCR', scenario_id: 'EOCR_SEQUENCE', scenario_label: 'EOCR', next_action: 'EOCR을 조작하세요.' },
        { requirement_id: 'F_POWER_OFF', label: '전원', scenario_id: 'POWER_SEQUENCE', scenario_label: '전원 차단·복귀', next_action: '전원을 조작하세요.' },
      ],
    } })
    const user = userEvent.setup()
    const qnet = { ...trainingDetail, problem_id: 'qnet_electrician_practical_010', capabilities: { ...trainingDetail.capabilities, operation_gradable: false } }
    render(<MemoryRouter><OperationTestPage problem={qnet} /></MemoryRouter>)
    expect(await screen.findAllByText('미확인')).toHaveLength(5)
    expect(screen.queryByText('아직 이 요구사항을 실행하지 않았습니다.')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '5개 요구사항 확인' }))
    expect(await screen.findAllByText('확인 · 충족')).toHaveLength(5)
    expect(screen.queryByText(/정답 비교, 점수 및 합격·불합격 판정은 제공하지 않습니다/)).not.toBeInTheDocument()
    expect(screen.getAllByText(/다음 조작/)).toHaveLength(5)
    expect(screen.queryByText(/\d+점/)).not.toBeInTheDocument()
  })

  it('keeps manual simulation available when public requirements are not defined yet', async () => {
    installApiMock({ operationSetup: { ...readySetup, behavior_requirements: [] } })
    const qnet = {
      ...trainingDetail,
      problem_id: 'qnet_electrician_practical_015',
      circuit: { ...trainingDetail.circuit, coils: [] },
      capabilities: { ...trainingDetail.capabilities, operation_previewable: true, operation_gradable: false },
    }
    render(<MemoryRouter><OperationTestPage problem={qnet} /></MemoryRouter>)
    expect(await screen.findByRole('button', { name: '전원 ON' })).toBeInTheDocument()
    expect(screen.getByText(/전기·기구 동작을 조작부에서 직접 확인/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '0개 요구사항 확인' })).not.toBeInTheDocument()
  })

  it('keeps requirement outcomes distinct while hiding PDF prefixes and unrun observations', async () => {
    const fetchMock = installApiMock({ operationSetup: { ...readySetup, behavior_requirements: [
      { requirement_id: 'MANUAL_1', label: 'PB1 기동', scenario_id: 'MANUAL', scenario_label: 'PDF 8쪽 · 수동 기동' },
    ] } })
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation(async (input, init) => {
      const result = await original(input, init)
      if (String(input).endsWith('/run-requirements')) {
        const summary = await result.json()
        return { ...result, json: async () => ({ ...summary, scenarios: [
          { scenario_id: 'MANUAL', label: 'PDF 8쪽 · 수동 기동', status: 'satisfied', current_observation: '기동 확인', missing_conditions: [], next_action: 'STOP 조작' },
          { scenario_id: 'STOP', label: 'PDF8쪽 · STOP', status: 'unsatisfied', current_observation: '정지되지 않음', missing_conditions: ['정지 경로 확인'], next_action: 'PB0 확인' },
          { scenario_id: 'EOCR', label: 'PDF 8쪽 · EOCR', status: 'unavailable', current_observation: '검사 불가 사유', missing_conditions: [], next_action: '기구 확인' },
          { scenario_id: 'TIMER', label: 'PDF 8쪽 · 타이머', status: 'not_run', current_observation: '아직 이 요구사항을 실행하지 않았습니다.', missing_conditions: [], next_action: '타이머 조작' },
        ] }) }
      }
      return result
    })
    const qnet = { ...trainingDetail, capabilities: { ...trainingDetail.capabilities, operation_gradable: false } }
    const user = userEvent.setup()
    render(<MemoryRouter><OperationTestPage problem={qnet} /></MemoryRouter>)
    expect(await screen.findByText('미확인')).toBeInTheDocument()
    expect(screen.getByText('수동 기동')).toBeInTheDocument()
    expect(screen.queryByText(/PDF\s*8쪽/)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '1개 요구사항 확인' }))
    expect(await screen.findByText('확인 · 충족')).toBeInTheDocument()
    expect(screen.getByText('확인 · 미충족')).toBeInTheDocument()
    expect(screen.getByText('확인 불가')).toBeInTheDocument()
    expect(screen.getByText('미확인')).toBeInTheDocument()
    expect(screen.getByText('정지되지 않음')).toBeInTheDocument()
    expect(screen.getByText('정지 경로 확인')).toBeInTheDocument()
    expect(screen.queryByText(/PDF\s*8쪽/)).not.toBeInTheDocument()
    expect(screen.queryByText('아직 이 요구사항을 실행하지 않았습니다.')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '전체 상태·타이머 초기화' }))
    await waitFor(() => expect(screen.queryByText('확인 · 충족')).not.toBeInTheDocument())
    expect(screen.getByText('미확인')).toBeInTheDocument()
  })
})
