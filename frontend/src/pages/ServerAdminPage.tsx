import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminRequest, type ManagedAccount, type NetworkOptions, type ServerStatus } from '../api/admin'
import { currentAuthSession } from '../features/user/authSession'
import '../styles/server-admin.css'

const date = (seconds: number | null) => seconds === null ? '활성 세션 없음' : new Date(seconds * 1000).toLocaleString('ko-KR', { hour12: false })
const gib = (bytes: number) => `${(bytes / 1024 ** 3).toFixed(1)} GB`
const auditLabels: Record<string, string> = {
  'grant-admin': '관리자 지정', 'revoke-admin': '관리자 해제', 'update-network': '다음 실행 주소 변경',
  'update-registration_open': '가입 허용 변경', 'logout-account': '계정 전체 로그아웃',
  'clear-network': '저장된 주소 설정 해제',
  'reset-password': '비밀번호 재설정',
}

export function ServerAdminPage() {
  const authorized = currentAuthSession()?.is_admin === true
  const [status, setStatus] = useState<ServerStatus>()
  const [accounts, setAccounts] = useState<ManagedAccount[]>([])
  const [network, setNetwork] = useState<NetworkOptions>({ host: '127.0.0.1', port: 8000 })
  const [error, setError] = useState<string>()
  const [message, setMessage] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState<ManagedAccount>()
  const [resetTarget, setResetTarget] = useState<ManagedAccount>()
  const [adminPassword, setAdminPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [resetError, setResetError] = useState<string>()
  const clearReset = () => { setResetTarget(undefined); setAdminPassword(''); setNewPassword(''); setPasswordConfirmation(''); setResetError(undefined) }
  const [checkedAt, setCheckedAt] = useState<string>()
  const load = useCallback(async () => {
    const [next, people] = await Promise.all([
      adminRequest<ServerStatus>('status'), adminRequest<ManagedAccount[]>('accounts'),
    ])
    setStatus(next); setAccounts(people)
    setNetwork(next.saved_network ?? next.current_network ?? { host: '127.0.0.1', port: 8000 })
    setCheckedAt(new Date().toLocaleTimeString('ko-KR', { hour12: false }))
  }, [])
  useEffect(() => { if (authorized) void load().catch(reason => setError(reason.message)) }, [authorized, load])
  const perform = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true); setError(undefined); setMessage(undefined)
    try { await action(); await load(); setMessage(success) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '관리 요청을 처리하지 못했습니다.') }
    finally { setBusy(false) }
  }
  if (!authorized) return <section className="server-admin"><h2>서버 관리자 전용</h2><p>서버 PC에서 지정된 관리자 계정으로 로그인해야 합니다.</p><Link to="/circuit">학습 화면으로</Link></section>

  return <section className="server-admin">
    <div className="admin-title"><div><p className="admin-eyebrow">학습 서비스 운영</p><h2>서버 관리</h2><p>같은 네트워크의 학습 서비스를 한곳에서 관리합니다.</p></div>
      <div><small>{checkedAt && `${checkedAt} 기준`}</small><button disabled={busy} onClick={() => void perform(async () => {}, '최신 상태를 확인했습니다.')}>상태 새로고침</button><Link to="/circuit">학습 화면</Link></div></div>
    {error && <p className="admin-error" role="alert">{error}</p>}
    {message && <p className="admin-success" role="status">{message}</p>}
    {!status && !error && <p role="status">서버 상태를 불러오는 중입니다.</p>}
    {status && <>
      <div className="admin-stats">
        <article><span>서비스 상태</span><strong>{status.database_ready ? '정상' : 'DB 확인 필요'}</strong><small>v{status.version} · 가동 {Math.floor(status.uptime_seconds / 60)}분</small></article>
        <article><span>가입 계정</span><strong>{status.account_count}명</strong><small>관리자 포함</small></article>
        <article><span>유효 로그인 세션</span><strong>{status.active_sessions}개</strong><small>실시간 접속 PC 수와는 다릅니다</small></article>
        <article><span>저장장치 여유 공간</span><strong>{gib(status.disk_free_bytes)}</strong><small>전체 {gib(status.disk_total_bytes)}</small></article>
      </div>
      <div className="admin-grid">
        <article className="admin-panel"><h3>접속 주소 · 포트</h3>
          <p>현재 접속 주소 <code>{window.location.origin}</code></p>
          <p>{status.service_managed ? '현재 수신 설정' : '현재 요청의 서버 주소'}: <code>{status.current_network ? `${status.current_network.host}:${status.current_network.port}` : '확인 불가'}</code></p>
          <p>서버 PC의 LAN IP 후보: {status.lan_addresses.length ? status.lan_addresses.join(', ') : '자동 확인 불가 — 서버 PC에서 확인하세요.'}</p>
          {!status.service_managed && <p className="admin-notice">지금은 직접 실행 모드입니다. 주소·포트 관리는 서버 PC에서 <code>scripts/run_service.py</code>로 실행한 뒤 사용할 수 있습니다.</p>}
          {status.restart_required && <p className="admin-notice">변경한 주소·포트는 아직 적용되지 않았습니다. 서버 재시작이 필요합니다.</p>}
          <form onSubmit={event => { event.preventDefault(); void perform(() => adminRequest('network', 'PUT', network), '다음 실행 설정을 저장했습니다. 학습자에게 알린 뒤 서버를 재시작하세요.') }}>
            <fieldset disabled={busy || !status.service_managed}>
              <label>수신 IP<input required list="admin-ip-options" value={network.host} onChange={e => setNetwork({ ...network, host: e.target.value })} /></label>
              <datalist id="admin-ip-options"><option value="127.0.0.1">이 PC에서만</option><option value="0.0.0.0">모든 IPv4 인터페이스</option>{status.lan_addresses.map(ip => <option key={ip} value={ip} />)}</datalist>
              <label>포트<input required type="number" min={1024} max={65535} step={1} value={network.port || ''} onChange={e => setNetwork({ ...network, port: Number(e.target.value) })} /></label>
              <button type="submit">다음 실행 설정 저장</button>
            </fieldset>
          </form>
          <p className="admin-help">127.0.0.1은 서버 PC 전용입니다. 휴대폰은 서버의 LAN IP로 접속하세요. 0.0.0.0은 수신 설정이며 접속 주소가 아닙니다. 이 설정은 PC 자체의 IP를 변경하지 않습니다.</p>
          <details><summary>같은 네트워크에서만 사용할 때</summary><p>사설 IP로 수신해도 접근 범위를 보장하지는 않습니다. 방화벽의 허용 원격 주소를 실제 LAN 대역으로 제한하고 공유기 포트 전달은 열지 마세요. 방화벽·공유기는 이 페이지에서 변경하지 않습니다.</p><p>주소·포트 변경 후 사용 중인 실행 명령으로 서버를 재시작하세요. 포트 충돌이나 존재하지 않는 IP로 시작이 실패하면 아래 운영 안내의 설정 복구 절차를 사용하세요.</p></details>
        </article>
        <article className="admin-panel"><h3>회원가입 · 계정 정책</h3>
          <div className="admin-switch"><div><strong>신규 회원가입 {status.registration_open ? '열림' : '닫힘'}</strong><p>닫아도 기존 계정은 로그인할 수 있습니다.</p></div>
            <button disabled={busy} onClick={() => void perform(() => adminRequest('registration', 'PUT', { enabled: !status.registration_open }), status.registration_open ? '신규 회원가입을 닫았습니다.' : '신규 회원가입을 열었습니다.')}>{status.registration_open ? '가입 닫기' : '가입 열기'}</button></div>
          <p className="admin-help">즉시 적용되고 서버 재시작 후에도 유지됩니다. 가입코드는 사용하지 않습니다.</p>
          <hr /><h3>데이터 · USB 백업</h3><p>계정과 학습 기록이 저장되는 서버 폴더</p><code className="admin-path">{status.data_directory}</code>
          <p>계정 DB <code>accounts.db</code>와 <code>users/</code>를 함께 보관합니다. 관리자 권한과 여기서 저장한 설정도 계정 DB에 포함됩니다.</p>
          <ol><li>학습자에게 저장 완료 후 로그아웃을 안내합니다.</li><li>서버 PC에서 <strong>서버_종료_백업.bat</strong>을 실행합니다.</li><li>‘백업 완료’를 확인하고 열린 폴더의 날짜·시간 ZIP을 USB로 복사합니다.</li><li>이전할 PC에서는 백업을 새 데이터 폴더로 복원합니다.</li></ol>
          <p>시작은 <strong>서버_시작.bat</strong>을 더블클릭하세요. 백업은 프로그램의 <code>user-data-backups/</code>에 보관하며 이전 백업을 자동 삭제하지 않습니다.</p>
          <p className="admin-help">일관된 백업을 위해 실행 중 웹 다운로드·덮어쓰기 복원은 제공하지 않습니다. 백업에는 개인 기록과 비밀번호 해시가 포함되므로 보관에 주의하세요.</p>
          <details><summary>서버 PC용 운영 명령</summary><p>프로그램 폴더에서 실행합니다. 아래 경로는 기본 예시이며 위의 실제 데이터 폴더와 일치시켜야 합니다.</p>
            <pre>{'.\\.venv\\Scripts\\python.exe scripts/run_service.py --env-file service-config/service.env'}</pre>
            <p>중지 후 백업(새 파일명 사용):</p><pre>{'.\\.venv\\Scripts\\python.exe scripts/service_data.py backup user-data backup-YYYYMMDD.zip --server-stopped'}</pre>
            <p>주소 설정으로 시작이 안 될 때, 중지 후 저장한 네트워크 설정만 해제:</p><pre>{'.\\.venv\\Scripts\\python.exe scripts/manage_admin.py user-data --clear-network --server-stopped'}</pre>
            <p>Linux/Pi에서는 <code>.venv/bin/python</code>을 사용합니다. 외부 인터넷 공개나 자동 방화벽 변경은 하지 않습니다.</p></details>
          {!status.secure_cookie && <p className="admin-notice">현재 보안 쿠키가 꺼져 있습니다. HTTP 접속에서는 비밀번호가 암호화되지 않으므로 실제 계정 운영에는 HTTPS를 권장합니다.</p>}
        </article>
      </div>
      <article className="admin-panel"><h3>계정 · 로그인 세션</h3><p>개인 결선이나 비밀번호는 표시하지 않습니다. 전체 로그아웃은 해당 계정의 다음 서버 요청부터 적용되며 저장 기록은 삭제하지 않습니다.</p>
        <div className="admin-table-scroll"><table><thead><tr><th>아이디 / 닉네임</th><th>권한</th><th>가입일</th><th>유효 세션 / 최근 활동</th><th>관리</th></tr></thead><tbody>
          {accounts.map(account => <tr key={account.user_id}><td><strong>{account.username}</strong><br />{account.nickname}</td><td>{account.is_admin ? '관리자' : '학습자'}</td><td>{date(account.created_at)}</td><td>{account.active_sessions}개<br /><small>{date(account.last_seen)}</small></td><td><div className="admin-account-actions"><button disabled={busy || account.active_sessions === 0 || account.user_id === currentAuthSession()?.user?.user_id} onClick={() => setConfirm(account)}>전체 기기 로그아웃</button><button disabled={busy} onClick={() => { clearReset(); setResetTarget(account) }}>비밀번호 재설정</button></div></td></tr>)}
        </tbody></table></div>
      </article>
      <article className="admin-panel"><details><summary>최근 관리 기록 ({status.audit.length}건)</summary><ul className="admin-audit">{status.audit.map((event, index) => <li key={index}><time>{date(event.created_at)}</time> · {event.actor} · {auditLabels[event.action] ?? event.action} · <code>{event.target}</code></li>)}</ul></details></article>
    </>}
    {confirm && <div className="problem-dialog-backdrop"><section className="account-card" role="dialog" aria-modal="true" aria-labelledby="admin-logout-title">
      <h2 id="admin-logout-title">모든 기기에서 로그아웃할까요?</h2><p>{confirm.username} ({confirm.nickname}) 계정의 로그인 세션을 종료합니다. 저장된 기록은 유지되지만 저장하지 않은 작업이 있을 수 있습니다.</p>
      <button disabled={busy} onClick={() => { const user = confirm; setConfirm(undefined); void perform(() => adminRequest(`accounts/${encodeURIComponent(user.user_id)}/logout`, 'POST'), '해당 계정의 로그인 세션을 종료했습니다.') }}>로그아웃 진행</button><button onClick={() => setConfirm(undefined)}>취소</button>
    </section></div>}
    {resetTarget && <div className="problem-dialog-backdrop"><section className="account-card admin-password-dialog" role="dialog" aria-modal="true" aria-labelledby="admin-password-title">
      <h2 id="admin-password-title">비밀번호 재설정</h2><p>대상: <strong>{resetTarget.username}</strong> ({resetTarget.nickname})</p>
      <p>기존 로그인은 모두 종료되고 저장된 학습 기록은 유지됩니다. 대상 사용자에게 새 비밀번호를 별도로 알려주세요. 본인 계정을 재설정하면 다시 로그인해야 합니다.</p>
      <form onSubmit={async event => {
        event.preventDefault(); setResetError(undefined)
        if (newPassword !== passwordConfirmation) { setResetError('새 비밀번호 확인이 일치하지 않습니다.'); return }
        setBusy(true); setError(undefined); setMessage(undefined)
        try {
          const result = await adminRequest<{ reauthenticate: boolean }>(`accounts/${encodeURIComponent(resetTarget.user_id)}/reset-password`, 'POST', { admin_password: adminPassword, new_password: newPassword, confirmation: passwordConfirmation })
          clearReset()
          if (result.reauthenticate) window.dispatchEvent(new Event('electrician:auth-expired'))
          else { setMessage('비밀번호를 재설정했습니다. 대상 사용자는 새 비밀번호로 로그인해야 합니다.'); await load().catch(() => setError('재설정은 완료됐으나 계정 목록을 갱신하지 못했습니다. 새로고침하세요.')) }
        } catch (reason) { setResetError(reason instanceof Error ? reason.message : '재설정하지 못했습니다.'); setAdminPassword(''); setNewPassword(''); setPasswordConfirmation('') }
        finally { setBusy(false) }
      }}>
        <label>관리자 현재 비밀번호<input autoFocus required type="password" autoComplete="off" maxLength={128} value={adminPassword} onChange={event => setAdminPassword(event.target.value)} /></label>
        <label>새 비밀번호<input required type="password" autoComplete="new-password" minLength={6} maxLength={128} value={newPassword} onChange={event => setNewPassword(event.target.value)} /></label>
        <label>새 비밀번호 확인<input required type="password" autoComplete="new-password" minLength={6} maxLength={128} value={passwordConfirmation} onChange={event => setPasswordConfirmation(event.target.value)} /></label>
        {resetError && <p role="alert">{resetError}</p>}
        <div className="admin-account-actions"><button type="submit" disabled={busy}>{busy ? '재설정 중…' : '비밀번호 재설정 확정'}</button><button type="button" disabled={busy} onClick={clearReset}>취소</button></div>
      </form>
    </section></div>}
  </section>
}
