import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { AccountGate } from '../components/AccountGate'
import { authHeaders, setAuthSession, studyDraftStorage, clearAccountDrafts } from '../features/user/authSession'
import { saveCircuitAnalysisDraft } from '../api/client'

afterEach(() => { cleanup(); vi.unstubAllGlobals(); setAuthSession(undefined); clearAccountDrafts(); localStorage.clear() })

it.each(['login', 'register'])('shows persistent credential length hints on %s without changing authentication rules', async mode => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ required: true, user: null, registration_open: true }))))
  render(<AccountGate>{() => <div>학습 화면</div>}</AccountGate>)
  await screen.findByRole('heading', { name: '로그인' })
  const user = userEvent.setup()
  if (mode === 'register') await user.click(screen.getByRole('button', { name: '새 계정 만들기' }))
  const username = screen.getByLabelText('아이디')
  const password = screen.getByLabelText('비밀번호')
  expect(username).toHaveAccessibleDescription('4~24자 · 영문, 숫자, 밑줄(_) 사용 가능')
  expect(password).toHaveAccessibleDescription('6자 이상')
  expect(username).toHaveAttribute('pattern', '[A-Za-z0-9_]{4,24}')
  expect(password).toHaveAttribute('minlength', mode === 'register' ? '6' : '1')
  await user.type(username, 'test01')
  await user.type(password, 'abc123')
  expect(screen.getByText('4~24자 · 영문, 숫자, 밑줄(_) 사용 가능')).toBeVisible()
  expect(screen.getByText('6자 이상')).toBeVisible()
})

it('requires server login before mounting study UI and accepts account registration', async () => {
  const calls: { url: string; body: unknown }[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    calls.push({ url, body: init?.body })
    return new Response(JSON.stringify(url.endsWith('/me') ? { required: true, user: null, registration_open: true } : {
      required: true, user: { user_id: 'acct_test', username: 'student01', nickname: '학생' }, csrf_token: 'csrf-secret', registration_open: true,
    }), { status: url.endsWith('/register') ? 201 : 200 })
  }))
  render(<AccountGate>{profile => <div>학습 화면 {profile?.nickname}</div>}</AccountGate>)
  expect(screen.queryByText(/학습 화면/)).not.toBeInTheDocument()
  await screen.findByRole('heading', { name: '로그인' })
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: '새 계정 만들기' }))
  expect(screen.queryByText('기관 LAN 학습 서비스')).not.toBeInTheDocument()
  expect(screen.getByText('개인 계정으로 학습 기록을 저장합니다.')).toBeInTheDocument()
  expect(screen.queryByText(/서버 이전 후에도/)).not.toBeInTheDocument()
  expect(screen.getByText('비밀번호를 잊은 경우 기관 관리자에게 재설정을 요청하세요.')).toBeInTheDocument()
  expect(screen.queryByText(/공용 PC에 비밀번호를 저장하지/)).not.toBeInTheDocument()
  expect(screen.queryByText(/기존 닉네임 자료는/)).not.toBeInTheDocument()
  expect(screen.getByLabelText('아이디')).not.toHaveAttribute('placeholder')
  expect(screen.getByLabelText('비밀번호')).not.toHaveAttribute('placeholder')
  expect(screen.getByLabelText('비밀번호')).toHaveAttribute('minlength', '6')
  await user.type(screen.getByLabelText('아이디'), 'student01')
  await user.type(screen.getByLabelText('비밀번호'), 'abc123')
  await user.type(screen.getByLabelText('닉네임'), '학생')
  expect(screen.queryByLabelText('가입코드')).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '가입하고 시작' }))
  expect(await screen.findByText('학습 화면 학생')).toBeInTheDocument()
  expect(JSON.parse(calls.find(c => c.url.endsWith('/register'))!.body as string)).toEqual({
    username: 'student01', password: 'abc123', nickname: '학생',
  })
  expect(JSON.stringify(localStorage)).not.toContain('csrf-secret')
  expect(JSON.stringify(localStorage)).not.toContain('abc123')
  expect(authHeaders()['X-Session-User']).toBe('acct_test')
})

it('shows an authentication error instead of entering the study tree', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => new Response(JSON.stringify(url.endsWith('/me') ? {
    required: true, user: null, registration_open: false,
  } : { detail: '아이디 또는 비밀번호를 확인하세요.' }), { status: url.endsWith('/me') ? 200 : 401 })))
  render(<AccountGate>{() => <div>학습 화면</div>}</AccountGate>)
  await screen.findByRole('heading', { name: '로그인' })
  expect(screen.queryByRole('button', { name: '새 계정 만들기' })).not.toBeInTheDocument()
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('아이디'), 'student01')
  await user.type(screen.getByLabelText('비밀번호'), 'incorrect')
  await user.click(screen.getByRole('button', { name: '로그인' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('아이디 또는 비밀번호')
  expect(screen.queryByText('학습 화면')).not.toBeInTheDocument()
})

it('keeps authenticated drafts off disk and captures identity/CSRF before queued saves', async () => {
  setAuthSession({ required: true, user: { user_id: 'acct_a', username: 'aaaa', nickname: '학생' }, csrf_token: 'csrf-a', registration_open: false })
  studyDraftStorage().setItem('private-draft', 'private-answer')
  expect(localStorage.getItem('private-draft')).toBeNull()
  const fetch = vi.fn(async () => new Response('{}'))
  vi.stubGlobal('fetch', fetch)
  const saving = saveCircuitAnalysisDraft('q001', { problem_version: 1, memo: 'mine', annotations: {}, selected_device_ids: [], selected_socket_ids: [], selected_terminal_ids: [] })
  setAuthSession({ required: true, user: { user_id: 'acct_b', username: 'bbbb', nickname: '학생' }, csrf_token: 'csrf-b', registration_open: false })
  await saving
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1))
  const options = (fetch.mock.calls[0] as unknown as [string, RequestInit])[1]
  expect(new Headers(options.headers).get('X-Session-User')).toBe('acct_a')
  expect(new Headers(options.headers).get('X-CSRF-Token')).toBe('csrf-a')
  clearAccountDrafts()
  expect(studyDraftStorage().getItem('private-draft')).toBeNull()
})
