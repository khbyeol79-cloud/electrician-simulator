import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { OperationTestPage } from '../pages/OperationTestPage'
import { installApiMock, trainingDetail } from './mockApi'

afterEach(() => {
  cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); window.localStorage.clear()
})

describe('동작시험 준비', () => {
  it('renders saved wiring and fixed devices as read-only', async () => {
    installApiMock({ wiringDraft: [{ from: 'X1-1', to: 'MC1-4', wire_color: 'yellow', pair_display_color: '#64748b' }] })
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)

    const board = await screen.findByRole('img', { name: '동작시험 준비 제어함' })
    expect(board.querySelectorAll('.board-wire.readonly')).toHaveLength(1)
    expect(within(board).getByLabelText('X1 보조릴레이 자동 삽입')).toBeInTheDocument()
    expect(within(board).getByLabelText('MC1 12P 릴레이 자동 삽입')).toBeInTheDocument()
    expect(screen.getByText('2개 기구가 문제지에 지정된 소켓 위치에 자동으로 삽입되었습니다.')).toBeInTheDocument()
    expect(screen.queryByText('기구 보관함')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /단자$/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /연결된 전선/ })).not.toBeInTheDocument()
  })

  it('supports read-only zoom controls and explains the next stage limitation', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '동작시험 준비 제어함' })
    await user.click(screen.getByRole('button', { name: '확대' }))
    expect(screen.getByText('배선과 기구는 읽기 전용입니다.')).toBeInTheDocument()
    expect(screen.getByText('동작시험 기능은 다음 개발 단계에서 구현됩니다.')).toBeInTheDocument()
    expect(screen.getByText(/동작 결과를 계산하지 않습니다/)).toBeInTheDocument()
  })

  it('shows a recoverable Korean notice when fixed placement data is absent', async () => {
    installApiMock({ operationSetup: { device_layout: null, operation_ready: false, preview_allowed: false, message: '이 문제의 기구 배치 정보가 준비되지 않았습니다.' } })
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '동작시험 준비 제어함' })
    expect(screen.getByText('기구 배치 없음')).toBeInTheDocument()
    expect(screen.getAllByText('이 문제의 기구 배치 정보가 준비되지 않았습니다.')).toHaveLength(2)
  })

  it('returns to the editable wiring stage without exposing editing controls here', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/operation']}><Routes><Route path="/operation" element={<OperationTestPage problem={trainingDetail} />} /><Route path="/wiring" element={<h2>제어함 결선 돌아옴</h2>} /></Routes></MemoryRouter>)
    await screen.findByRole('img', { name: '동작시험 준비 제어함' })
    expect(screen.queryByRole('button', { name: '선택 전선 삭제' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '기구 장착 제출' })).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '결선 화면으로 돌아가기' }))
    expect(screen.getByRole('heading', { name: '제어함 결선 돌아옴' })).toBeInTheDocument()
  })

  it('labels an ungradable setup as preview instead of success', async () => {
    installApiMock({ operationSetup: { operation_ready: false, preview_allowed: true, message: '가상 학습 문제이므로 동작시험 준비 화면만 미리 볼 수 있습니다.', wiring_submission: { problem_id: 'training_socket_demo_001', attempt_count: 1, last_submitted_at: '2026-08-16T00:00:00', last_overall_correct: null, last_gradable: false, last_correct_count: 0, required_count: 0 } } })
    render(<MemoryRouter><OperationTestPage problem={trainingDetail} /></MemoryRouter>)
    await screen.findByRole('img', { name: '동작시험 준비 제어함' })
    expect(screen.getByRole('heading', { name: '가상 문제 미리보기' })).toBeInTheDocument()
    expect(screen.getByText('채점 불가')).toBeInTheDocument()
  })
})
