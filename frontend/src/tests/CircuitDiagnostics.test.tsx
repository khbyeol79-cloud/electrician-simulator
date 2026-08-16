import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CircuitAnalysisPage } from '../pages/CircuitAnalysisPage'
import userEvent from '@testing-library/user-event'
import { installApiMock, problemDetail, trainingDetail } from './mockApi'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe('회로 데이터 진단', () => {
  it('shows the unselected state without requesting circuit data', () => {
    const fetchMock = installApiMock()
    render(<CircuitAnalysisPage />)
    expect(screen.getByText('상단에서 연습할 문제를 먼저 선택해 주세요.')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('renders exact 8P and 12P base arrangements', async () => {
    installApiMock()
    render(<CircuitAnalysisPage problem={problemDetail} />)
    expect(await screen.findByRole('region', { name: '회로 데이터 요약' })).toBeInTheDocument()
    expect(screen.getByText('상단 6 5 4 3')).toBeInTheDocument()
    expect(screen.getByText('하단 7 8 1 2')).toBeInTheDocument()
    expect(screen.getByText('상단 1 2 3 4 5 6')).toBeInTheDocument()
    expect(screen.getByText('하단 7 8 9 10 11 12')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '시퀀스 회로도' })).toBeInTheDocument()
  })

  it('shows a recoverable catalog API error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 500, json: async () => ({}) } as Response)))
    render(<CircuitAnalysisPage problem={problemDetail} />)
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('회로도를 표시할 수 없습니다'))
  })

  it('selects a contact, restricts 8P pins, restores draft and grades', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<CircuitAnalysisPage problem={trainingDetail} />)
    await user.click(await screen.findByRole('button', { name: 'VR1 VR1-C1 선택' }))
    expect(screen.getByText('VR1-C1')).toBeInTheDocument()
    const upper = screen.getByLabelText('upper 소켓번호')
    expect(upper.querySelectorAll('option')).toHaveLength(9)
    await user.selectOptions(upper, '6')
    await user.selectOptions(screen.getByLabelText('lower 소켓번호'), '3')
    expect(screen.getByText('VR1-6')).toBeInTheDocument()
    expect(window.localStorage.getItem('electrician.circuitDraft.training_socket_demo_001.v1')).toContain('upper')
    await user.click(screen.getByRole('button', { name: '소켓번호 제출' }))
    expect(await screen.findByText('정답 ✓')).toBeInTheDocument()
  })

  it('supports zoom controls and incomplete submission warning', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<CircuitAnalysisPage problem={trainingDetail} />)
    await screen.findByRole('img', { name: '시퀀스 회로도' })
    await user.click(screen.getByRole('button', { name: '확대' }))
    expect(screen.getByText('115%')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '소켓번호 제출' }))
    expect(screen.getByRole('alert')).toHaveTextContent('아직 입력하지 않은')
  })
})
