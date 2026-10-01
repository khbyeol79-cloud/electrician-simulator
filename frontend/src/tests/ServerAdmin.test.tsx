import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { ServerAdminPage } from '../pages/ServerAdminPage'
import { Header } from '../components/Header'
import { setAuthSession } from '../features/user/authSession'
import type { ServerStatus } from '../api/admin'

afterEach(() => { cleanup(); setAuthSession(undefined); vi.unstubAllGlobals() })
const session = { required: true, is_admin: true, user: { user_id: 'acct_admin', username: 'operator01', nickname: '관리자' }, csrf_token: 'test-csrf', registration_open: true }
const initial: ServerStatus = {
  version: '0.13.0', uptime_seconds: 180, database_ready: true, service_managed: true,
  current_network: { host: '127.0.0.1', port: 8000 }, saved_network: null, restart_required: false,
  lan_addresses: ['192.168.0.14'], registration_open: true, account_count: 2, active_sessions: 2,
  data_directory: 'D:\\program\\user-data', disk_free_bytes: 1024 ** 3 * 10, disk_total_bytes: 1024 ** 3 * 50,
  secure_cookie: false, audit: [],
}
function mockServer(overrides: Partial<ServerStatus> = {}) {
  let status = { ...initial, ...overrides }
  const calls: { path: string; init?: RequestInit }[] = []
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    calls.push({ path, init })
    if (path.endsWith('/reset-password')) return new Response(JSON.stringify({ reset: true, reauthenticate: path.includes('acct_admin/') }))
    if (path.endsWith('/registration')) status = { ...status, registration_open: JSON.parse(init?.body as string).enabled }
    if (path.endsWith('/network')) status = { ...status, saved_network: JSON.parse(init?.body as string), restart_required: true }
    return new Response(JSON.stringify(path.endsWith('/accounts') ? [
      { ...session.user, created_at: 1750000000, is_admin: true, active_sessions: 1, last_seen: 1750000000 },
      { user_id: 'acct_student', username: 'student01', nickname: '학생', created_at: 1750000000, is_admin: false, active_sessions: 1, last_seen: 1750000000 },
    ] : status))
  }))
  setAuthSession(session)
  render(<MemoryRouter><ServerAdminPage /></MemoryRouter>)
  return calls
}

it('hides administrator controls and never loads administrative data for learners', () => {
  setAuthSession({ ...session, is_admin: false })
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
  render(<MemoryRouter><ServerAdminPage /></MemoryRouter>)
  expect(screen.getByRole('heading', { name: '서버 관리자 전용' })).toBeInTheDocument()
  expect(fetch).not.toHaveBeenCalled()
})

it('only shows the server management header link for administrators', () => {
  const props = { onRefresh: vi.fn(), onOpenProblems: vi.fn(), onReset: vi.fn(), userProfile: { userId: 'acct_admin', nickname: '관리자', isLegacy: false }, onOpenUser: vi.fn() }
  setAuthSession({ ...session, is_admin: false })
  const view = render(<MemoryRouter><Header {...props} /></MemoryRouter>)
  expect(screen.queryByRole('link', { name: '서버 관리' })).not.toBeInTheDocument()
  setAuthSession(session)
  view.rerender(<MemoryRouter><Header {...props} /></MemoryRouter>)
  expect(screen.getByRole('link', { name: '서버 관리' })).toHaveAttribute('href', '/admin')
})

it('shows status and saves registration with CSRF and current identity headers', async () => {
  const calls = mockServer()
  await screen.findByText('student01')
  expect(screen.getByText('2명')).toBeInTheDocument()
  expect(screen.getByText('D:\\program\\user-data')).toBeInTheDocument()
  await userEvent.click(screen.getByRole('button', { name: '가입 닫기' }))
  expect(await screen.findByText('신규 회원가입 닫힘')).toBeInTheDocument()
  const call = calls.find(c => c.path.endsWith('/registration'))!
  expect(JSON.parse(call.init?.body as string)).toEqual({ enabled: false })
  const headers = new Headers(call.init?.headers)
  expect(headers.get('X-CSRF-Token')).toBe('test-csrf')
  expect(headers.get('X-Session-User')).toBe('acct_admin')
})

it('clearly marks saved network settings as pending restart without changing live origin', async () => {
  const calls = mockServer()
  const user = userEvent.setup()
  await screen.findByLabelText('수신 IP')
  await user.clear(screen.getByLabelText('수신 IP'))
  await user.type(screen.getByLabelText('수신 IP'), '192.168.0.14')
  await user.clear(screen.getByLabelText('포트'))
  await user.type(screen.getByLabelText('포트'), '8017')
  await user.click(screen.getByRole('button', { name: '다음 실행 설정 저장' }))
  expect(await screen.findByText(/변경한 주소·포트는 아직 적용되지 않았습니다/)).toBeInTheDocument()
  expect(screen.getByText('127.0.0.1:8000')).toBeInTheDocument()
  expect(JSON.parse(calls.find(c => c.path.endsWith('/network'))!.init?.body as string)).toEqual({ host: '192.168.0.14', port: 8017 })
})

it('disables bind edits when the service was not started by the managed launcher', async () => {
  mockServer({ service_managed: false })
  await screen.findByText(/지금은 직접 실행 모드입니다/)
  expect(screen.getByLabelText('수신 IP')).toBeDisabled()
  expect(screen.getByRole('button', { name: '다음 실행 설정 저장' })).toBeDisabled()
})

it('requires an explicit confirmation before revoking another account sessions', async () => {
  const calls = mockServer()
  await screen.findByText('student01')
  const buttons = screen.getAllByRole('button', { name: '전체 기기 로그아웃' })
  expect(buttons[0]).toBeDisabled()
  await userEvent.click(buttons[1])
  expect(screen.getByRole('dialog')).toHaveTextContent('student01')
  expect(calls.some(c => c.path.endsWith('/logout'))).toBe(false)
  await userEvent.click(screen.getByRole('button', { name: '취소' }))
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  await userEvent.click(buttons[1])
  await userEvent.click(screen.getByRole('button', { name: '로그아웃 진행' }))
  await waitFor(() => expect(calls.some(c => c.path === '/api/admin/accounts/acct_student/logout')).toBe(true))
})

it('reports forbidden or failed requests instead of claiming that settings were saved', async () => {
  mockServer()
  await screen.findByText('student01')
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: '권한이 없습니다.' }), { status: 403 })))
  await userEvent.click(screen.getByRole('button', { name: '가입 닫기' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('권한이 없습니다.')
  expect(screen.queryByText('신규 회원가입을 닫았습니다.')).not.toBeInTheDocument()
})

it('resets a selected account only after password confirmation and clears secrets on cancel', async () => {
  const calls = mockServer()
  await screen.findByText('student01')
  const user = userEvent.setup()
  const open = () => user.click(screen.getAllByRole('button', { name: '비밀번호 재설정' })[1])
  await open()
  expect(screen.getByRole('dialog')).toHaveTextContent('student01')
  expect(screen.getByRole('dialog').parentElement).toHaveClass('problem-dialog-backdrop')
  await user.type(screen.getByLabelText('관리자 현재 비밀번호'), 'admin-secret')
  await user.click(screen.getByRole('button', { name: '취소' }))
  await open()
  expect(screen.getByLabelText('관리자 현재 비밀번호')).toHaveValue('')
  await user.type(screen.getByLabelText('관리자 현재 비밀번호'), 'admin-secret')
  await user.type(screen.getByLabelText('새 비밀번호', { exact: true }), 'new123')
  await user.type(screen.getByLabelText('새 비밀번호 확인'), 'other123')
  await user.click(screen.getByRole('button', { name: '비밀번호 재설정 확정' }))
  expect(screen.getByRole('alert')).toHaveTextContent('일치하지')
  expect(calls.some(c => c.path.endsWith('/reset-password'))).toBe(false)
  await user.clear(screen.getByLabelText('새 비밀번호 확인'))
  await user.type(screen.getByLabelText('새 비밀번호 확인'), 'new123')
  await user.click(screen.getByRole('button', { name: '비밀번호 재설정 확정' }))
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  const request = calls.find(c => c.path.endsWith('/reset-password'))!
  expect(request.path).toBe('/api/admin/accounts/acct_student/reset-password')
  expect(JSON.parse(request.init?.body as string)).toEqual({ admin_password: 'admin-secret', new_password: 'new123', confirmation: 'new123' })
  expect(new Headers(request.init?.headers).get('X-CSRF-Token')).toBe('test-csrf')
})

it('requires login again after resetting the administrator own password', async () => {
  mockServer()
  await screen.findByText('student01')
  const expired = vi.fn()
  window.addEventListener('electrician:auth-expired', expired)
  try {
    await userEvent.click(screen.getAllByRole('button', { name: '비밀번호 재설정' })[0])
    for (const label of ['관리자 현재 비밀번호', '새 비밀번호', '새 비밀번호 확인']) {
      await userEvent.type(screen.getByLabelText(label, { exact: true }), 'new123')
    }
    await userEvent.click(screen.getByRole('button', { name: '비밀번호 재설정 확정' }))
    await waitFor(() => expect(expired).toHaveBeenCalledOnce())
  } finally { window.removeEventListener('electrician:auth-expired', expired) }
})

it('clears entered secrets and keeps the form open when reauthentication fails', async () => {
  mockServer()
  await screen.findByText('student01')
  await userEvent.click(screen.getAllByRole('button', { name: '비밀번호 재설정' })[1])
  for (const label of ['관리자 현재 비밀번호', '새 비밀번호', '새 비밀번호 확인']) {
    await userEvent.type(screen.getByLabelText(label, { exact: true }), 'new123')
  }
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: '관리자 비밀번호를 확인하세요.' }), { status: 403 })))
  await userEvent.click(screen.getByRole('button', { name: '비밀번호 재설정 확정' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('관리자 비밀번호를 확인하세요.')
  for (const label of ['관리자 현재 비밀번호', '새 비밀번호', '새 비밀번호 확인']) {
    expect(screen.getByLabelText(label, { exact: true })).toHaveValue('')
  }
  expect(screen.getByRole('dialog')).toBeInTheDocument()
})
