import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { installApiMock } from './mockApi'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe('자유회로 실험', () => {
  it('creates a workspace without Q-Net grading and opens the shared wiring board', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/free-circuit']}><App /></MemoryRouter>)

    expect(await screen.findByRole('heading', { name: '자유회로 실험', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('정답 없는 실제 결선 실험')).toBeInTheDocument()
    expect(screen.queryByLabelText('작업공간 ID')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('시작 보드')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '기본보드로 만들기' }))

    expect(await screen.findByRole('heading', { name: '자기유지 자유회로', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('정답 데이터 없음')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '제어함 결선판' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '결선 제출' })).not.toBeInTheDocument()
  })

  it('requires only a non-empty workspace name and uses the server-generated id', async () => {
    const fetchMock = installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/free-circuit']}><App /></MemoryRouter>)
    const name = await screen.findByLabelText('작업공간 이름')
    await user.clear(name)
    await user.click(screen.getByRole('button', { name: '기본보드로 만들기' }))
    expect(screen.getByText('작업공간 이름을 입력해 주세요.')).toBeInTheDocument()
    await user.type(name, '새 모터 실험')
    await user.click(screen.getByRole('button', { name: '기본보드로 만들기' }))
    expect(await screen.findByRole('img', { name: '제어함 결선판' })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/free-circuits/workspaces', expect.objectContaining({ method: 'POST' }))
  })

  it('saves current wiring and enters operation without an answer submission', async () => {
    const fetchMock = installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/free-circuit']}><App /></MemoryRouter>)
    await user.click(await screen.findByRole('button', { name: '기본보드로 만들기' }))
    await user.click(await screen.findByRole('button', { name: '현재 결선으로 동작시험' }))

    expect(await screen.findByText('실제 결선 모드 실행 중')).toBeInTheDocument()
    expect(screen.getByText('정답 채점 없음')).toBeInTheDocument()
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/free-circuits/self_hold_01/sessions', expect.objectContaining({ method: 'POST' })))
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes('wiring-attempts/submit'))).toBe(false)
  })

  it('shows actual-wiring catalog composition without exposing answer grading', async () => {
    installApiMock({ actualOperation: true })
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/free-circuit']}><App /></MemoryRouter>)
    await user.click(await screen.findByRole('button', { name: '기본보드로 만들기' }))
    await user.click(await screen.findByRole('button', { name: '현재 결선으로 동작시험' }))

    expect(await screen.findByText('실제 결선 모드 실행 중')).toBeInTheDocument()
    expect(screen.getByText('공통 기구 카탈로그 적용')).toBeInTheDocument()
    expect(screen.getByText('정답 채점 없음')).toBeInTheDocument()
  })

  it('shows the new basic board as actual wiring immediately after creation', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/free-circuit']}><App /></MemoryRouter>)
    await user.click(await screen.findByRole('button', { name: '기본보드로 만들기' }))
    expect(await screen.findByText('기본보드')).toBeInTheDocument()
    expect(screen.getByText('실제 결선 모드')).toBeInTheDocument()
    expect(screen.queryByText('basic_board_001')).not.toBeInTheDocument()
  })

  it('uses a readable template name in the saved workspace list', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/free-circuit']}><App /></MemoryRouter>)
    await user.click(await screen.findByRole('button', { name: '기본보드로 만들기' }))
    await user.click(await screen.findByRole('button', { name: '다른 작업공간' }))
    expect(await screen.findByText(/전선 0개 · 기본보드/)).toBeInTheDocument()
    expect(screen.queryByText(/basic_board_001/)).not.toBeInTheDocument()
  })
})
