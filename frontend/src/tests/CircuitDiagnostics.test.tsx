import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CircuitAnalysisPage } from '../pages/CircuitAnalysisPage'
import { installApiMock, problemDetail } from './mockApi'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
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
    expect(screen.getByLabelText('상단 6 5 4 3')).toBeInTheDocument()
    expect(screen.getByLabelText('하단 7 8 1 2')).toBeInTheDocument()
    expect(screen.getByLabelText('상단 1 2 3 4 5 6')).toBeInTheDocument()
    expect(screen.getByLabelText('하단 7 8 9 10 11 12')).toBeInTheDocument()
    expect(screen.getAllByText('장치 명칭 영역')).toHaveLength(2)
    expect(screen.getByText(/실제 정답이 아닌/)).toBeInTheDocument()
  })

  it('shows a recoverable catalog API error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 500, json: async () => ({}) } as Response)))
    render(<CircuitAnalysisPage problem={problemDetail} />)
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('회로 데이터를 불러오지 못했습니다'))
  })
})
