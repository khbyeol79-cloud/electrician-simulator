import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'
import { getProblems } from '../api/client'
import { installApiMock, problemDetail, problemSummary } from './mockApi'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe('App', () => {
  it('separates study records through a nickname entry', async () => {
    const fetchMock = installApiMock({ problems: [{ ...problemSummary, problem_type: 'official', source_type: 'official' }, { ...problemSummary, problem_id: 'hidden-demo', title: '숨긴 기능검증 회로' }] })
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)
    const dialog = screen.getByRole('dialog', { name: '닉네임으로 입장' })
    await user.type(within(dialog).getByLabelText('닉네임'), '학생 01')
    await user.click(within(dialog).getByRole('button', { name: '이 닉네임으로 입장' }))
    expect(window.localStorage.getItem('electrician.userNickname')).toBe('학생 01')
    expect(window.localStorage.getItem('electrician.webUserId')).toMatch(/^user_[a-z0-9]+$/)
    const userId = window.localStorage.getItem('electrician.webUserId')
    await getProblems()
    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => new Headers(init?.headers).get('X-User-Id') === userId)).toBe(true))
  })

  it('renders Korean shell and server status', async () => {
    installApiMock({ problems: [{ ...problemSummary, problem_type: 'official', source_type: 'official' }, { ...problemSummary, problem_id: 'hidden-demo', title: '숨긴 기능검증 회로' }] })
    render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: '전기기능사 시퀀스 결선 시뮬레이터' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '회로도 분석', level: 2 })).toBeInTheDocument()
    await waitFor(() => expect(screen.getAllByText('준비됨')).toHaveLength(2))
    expect(screen.queryByText('웹')).not.toBeInTheDocument()
    expect(screen.queryByText(/실행 모드:/)).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: '자유회로 실험' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '새로고침' })).toBeInTheDocument()
  })

  it('selects a problem, keeps the header, and omits the old sidebar problem card', async () => {
    installApiMock({ problems: [{ ...problemSummary, problem_type: 'official', source_type: 'official', difficulty: 'advanced', estimated_minutes: 270, tags: ['Q-Net', '공개문제-001', 'PDF대조중'] }, { ...problemSummary, problem_id: 'hidden-demo', title: '숨긴 기능검증 회로' }] })
    const user = userEvent.setup()
    render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)

    await user.click(screen.getByRole('button', { name: /현재 문제/ }))
    const dialog = await screen.findByRole('dialog', { name: '문제 선택' })
    expect(dialog).toBeInTheDocument()
    expect(within(dialog).getByRole('region', { name: 'Q-Net 공개문제 학습' })).toHaveTextContent('1 / 18')
    expect(within(dialog).queryByRole('region', { name: '자체제작 기능검증 회로' })).not.toBeInTheDocument()
    expect(within(dialog).queryByText('숨긴 기능검증 회로')).not.toBeInTheDocument()
    for (const text of ['작성 중', '경고 1', '고급', '예상 270분', 'official', '#PDF대조중']) {
      expect(within(dialog).queryByText(text)).not.toBeInTheDocument()
    }
    expect(within(dialog).queryByText(/· v1/)).not.toBeInTheDocument()
    expect(within(dialog).getByText(problemSummary.problem_id)).toBeInTheDocument()
    expect(within(dialog).getByText('공식')).toBeInTheDocument()
    expect(within(dialog).getByText('#Q-Net')).toBeInTheDocument()
    expect(within(dialog).getByText('#공개문제-001')).toBeInTheDocument()

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

  it('returns to circuit analysis when changing problems from a workspace URL', async () => {
    installApiMock({ problems: [{ ...problemSummary, problem_type: 'official', source_type: 'official' }, { ...problemSummary, problem_id: 'hidden-demo', title: '숨긴 기능검증 회로' }] })
    const user = userEvent.setup()
    const LocationProbe = () => <output aria-label="현재 경로">{useLocation().pathname}{useLocation().search}</output>
    render(<MemoryRouter initialEntries={['/operation?workspace=old-problem']}><App /><LocationProbe /></MemoryRouter>)

    await user.click(screen.getByRole('button', { name: /현재 문제/ }))
    await user.click(await screen.findByRole('button', { name: /기본 자기유지 회로 구조 연습/ }))

    expect(await screen.findByRole('heading', { name: '회로도 분석', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('status', { name: '현재 경로' })).toHaveTextContent('/circuit')
    expect(screen.getByRole('status', { name: '현재 경로' })).not.toHaveTextContent('workspace=')
  })

  it('restores the last selected problem', async () => {
    window.localStorage.setItem('electrician.selectedProblemId', problemDetail.problem_id)
    installApiMock({ problems: [{ ...problemSummary, problem_type: 'official', source_type: 'official' }, { ...problemSummary, problem_id: 'hidden-demo', title: '숨긴 기능검증 회로' }] })
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
