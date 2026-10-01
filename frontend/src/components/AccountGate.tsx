import { useEffect, useState, type ReactNode } from 'react'
import { clearAccountDrafts, setAuthSession, type AuthSession } from '../features/user/authSession'
import type { UserProfile } from '../features/user/userProfile'

async function accountRequest(path: string, payload?: unknown, csrf?: string) {
  const response = await fetch(`/api/auth/${path}`, {
    method: path === 'me' ? 'GET' : 'POST', credentials: 'same-origin', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'ElectricianSimulator', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : '로그인 서버에 연결할 수 없습니다.')
  }
  return response.status === 204 ? undefined : await response.json() as AuthSession
}

export function AccountGate({ children }: { children: (profile?: UserProfile, openAccount?: () => void) => ReactNode }) {
  const [session, setSession] = useState<AuthSession>()
  const [error, setError] = useState<string>()
  const [register, setRegister] = useState(false)
  const [accountOpen, setAccountOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const apply = (next: AuthSession) => { setAuthSession(next); setSession(next) }
  useEffect(() => {
    let cancelled = false
    void accountRequest('me').then(next => { if (!cancelled && next) apply(next) }).catch(reason => { if (!cancelled) setError(String(reason.message)) })
    const changed = (event: StorageEvent) => {
      if (event.key === 'electrician.accountChanged') window.location.reload()
    }
    const expired = () => { window.location.reload() }
    window.addEventListener('storage', changed)
    window.addEventListener('electrician:auth-expired', expired)
    return () => { cancelled = true; window.removeEventListener('storage', changed); window.removeEventListener('electrician:auth-expired', expired) }
  }, [])
  const notifyTabs = () => window.localStorage.setItem('electrician.accountChanged', `${Date.now()}-${Math.random()}`)
  if (!session) return <main className="account-screen"><section className="account-card"><h1>학습 서버 연결</h1><p role="status">{error ?? '로그인 상태를 확인하고 있습니다.'}</p>{error && <button onClick={() => window.location.reload()}>다시 연결</button>}</section></main>
  if (!session.required) return <>{children()}</>
  if (session.user) {
    const profile = { userId: session.user.user_id, nickname: session.user.nickname, isLegacy: false }
    return <>{children(profile, () => setAccountOpen(true))}{accountOpen && <div className="problem-dialog-backdrop"><section className="account-card" role="dialog" aria-modal="true" aria-label="내 계정">
      <h2>{session.user.nickname}</h2><p>아이디: {session.user.username}</p>
      <p>공용 PC에서는 사용 후 로그아웃하세요. 결선 화면의 ‘저장됨’을 확인한 뒤 종료하세요.</p>
      {error && <p role="alert">{error}</p>}
      <button disabled={busy} onClick={async () => {
        setBusy(true); setError(undefined)
        try { await accountRequest('logout', undefined, session.csrf_token ?? undefined); clearAccountDrafts(); notifyTabs(); window.location.reload() }
        catch (reason) { setError(reason instanceof Error ? reason.message : '로그아웃하지 못했습니다.'); setBusy(false) }
      }}>로그아웃</button><button disabled={busy} onClick={() => setAccountOpen(false)}>닫기</button>
    </section></div>}</>
  }
  return <main className="account-screen"><section className="account-card">
    <h1>전기기능사 시퀀스 결선 시뮬레이터</h1>
    <h2>{register ? '회원가입' : '로그인'}</h2>
    <p>개인 계정으로 학습 기록을 저장합니다.</p>
    <form onSubmit={async event => {
      event.preventDefault(); setBusy(true); setError(undefined)
      try {
        const next = await accountRequest(register ? 'register' : 'login', { username, password, ...(register ? { nickname } : {}) })
        if (next) { clearAccountDrafts(); apply(next); notifyTabs(); setPassword('') }
      } catch (reason) { setError(reason instanceof Error ? reason.message : '로그인 실패') }
      finally { setBusy(false) }
    }}>
      <div className="account-field"><label>아이디<input required value={username} onChange={e => setUsername(e.target.value)} pattern="[A-Za-z0-9_]{4,24}" maxLength={24} autoComplete="username" aria-describedby="account-username-hint" /></label><small id="account-username-hint">4~24자 · 영문, 숫자, 밑줄(_) 사용 가능</small></div>
      <div className="account-field"><label>비밀번호<input required type="password" value={password} onChange={e => setPassword(e.target.value)} minLength={register ? 6 : 1} maxLength={128} autoComplete={register ? 'new-password' : 'current-password'} aria-describedby="account-password-hint" /></label><small id="account-password-hint">6자 이상</small></div>
      {register && <label>닉네임<input required value={nickname} onChange={e => setNickname(e.target.value)} minLength={2} maxLength={20} autoComplete="off" /></label>}
      {error && <p role="alert">{error}</p>}
      <button type="submit" disabled={busy}>{busy ? '확인 중…' : register ? '가입하고 시작' : '로그인'}</button>
    </form>
    {session.registration_open && <button disabled={busy} onClick={() => { setRegister(!register); setError(undefined); setPassword('') }}>{register ? '로그인으로 돌아가기' : '새 계정 만들기'}</button>}
    <p className="account-help">비밀번호를 잊은 경우 기관 관리자에게 재설정을 요청하세요.</p>
  </section></main>
}
