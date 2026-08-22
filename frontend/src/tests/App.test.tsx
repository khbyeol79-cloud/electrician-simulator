import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { installApiMock, problemDetail } from './mockApi'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe('App', () => {
  it('renders Korean shell and server status', async () => {
    installApiMock()
    render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: '전기기능사 시퀀스 결선 시뮬레이터' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '회로도 분석', level: 2 })).toBeInTheDocument()
    await waitFor(() => expect(screen.getAllByText('준비됨')).toHaveLength(2))
  })

  it('selects a problem, keeps the header, and omits the old sidebar problem card', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)

    await user.click(screen.getByRole('button', { name: /현재 문제/ }))
    const dialog = await screen.findByRole('dialog', { name: '문제 선택' })
    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getByRole('region', { name: 'Q-Net 공개문제 학습' })).toHaveTextContent('0 / 18')
    expect(within(dialog).getByRole('region', { name: '자체제작 기능검증 회로' })).toHaveTextContent('Q-Net 시험문제가 아닙니다')
    expect(screen.getByText('작성 중')).toBeInTheDocument()
    expect(screen.getByText('경고 1')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /기본 자기유지 회로 구조 연습/ }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /현재 문제.*기본 자기유지 회로 구조 연습/ })).toBeInTheDocument()
    })
    expect(screen.queryByText('문제 정보')).not.toBeInTheDocument()
    expect(screen.queryByText('3P3W_AC_220V')).not.toBeInTheDocument()
    expect(await screen.findByRole('img', { name: '시퀀스 회로도' })).toBeInTheDocument()
    expect(screen.getByText('상단 6 5 4 3')).toBeInTheDocument()
    expect(screen.getByText('하단 7 8 1 2')).toBeInTheDocument()
    expect(window.localStorage.getItem('electrician.selectedProblemId')).toBe('practice_001')
  })

  it('restores the last selected problem', async () => {
    window.localStorage.setItem('electrician.selectedProblemId', problemDetail.problem_id)
    installApiMock()
    render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)

    expect(await screen.findByRole('button', { name: /현재 문제.*기본 자기유지 회로 구조 연습/ })).toBeInTheDocument()
  })

  it('shows an empty problem list state', async () => {
    installApiMock({ problems: [] })
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)
    await user.click(screen.getByRole('button', { name: /현재 문제/ }))
    expect(await screen.findByText('사용할 수 있는 문제가 없습니다.')).toBeInTheDocument()
  })

  it('shows a recoverable API error', async () => {
    installApiMock({ failProblems: true })
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)
    await user.click(screen.getByRole('button', { name: /현재 문제/ }))
    const dialog = await screen.findByRole('dialog', { name: '문제 선택' })
    expect(within(dialog).getByRole('alert')).toHaveTextContent('문제 목록을 불러올 수 없습니다')
    expect(within(dialog).queryByRole('button', { name: '새로고침' })).not.toBeInTheDocument()
    expect(within(dialog).getByRole('region', { name: 'Q-Net 공개문제 학습' })).toHaveTextContent('0 / 18')
  })
})
