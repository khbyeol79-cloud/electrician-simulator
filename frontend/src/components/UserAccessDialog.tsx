import { useState } from 'react'
import type { UserProfile } from '../features/user/userProfile'

export function UserAccessDialog({ open, current, canClose, onClose, onNickname, onLegacy }: {
  open: boolean; current: UserProfile; canClose: boolean
  onClose: () => void; onNickname: (nickname: string) => string | undefined; onLegacy: () => void
}) {
  const [nickname, setNickname] = useState(current.isLegacy ? '' : current.nickname)
  const [error, setError] = useState<string>()
  if (!open) return null
  return <div className="problem-dialog-backdrop user-access-backdrop" role="presentation">
    <section className="user-access-dialog" role="dialog" aria-modal="true" aria-labelledby="user-access-title">
      <header><div><span>사용자별 학습 기록</span><h2 id="user-access-title">닉네임으로 입장</h2></div>{canClose && <button type="button" onClick={onClose} aria-label="사용자 창 닫기">×</button>}</header>
      <div className="user-access-body">
        <p>같은 닉네임은 같은 학습 공간을 사용합니다. 회로 분석, 결선, 작업공간과 동작 기록은 다른 닉네임과 분리됩니다.</p>
        <form onSubmit={(event) => { event.preventDefault(); setError(onNickname(nickname)) }}>
          <label htmlFor="user-nickname">닉네임</label>
          <input id="user-nickname" value={nickname} maxLength={20} autoFocus placeholder="예: 홍길동01" onChange={(event) => { setNickname(event.target.value); setError(undefined) }} />
          {error && <span className="user-access-error" role="alert">{error}</span>}
          <button type="submit">이 닉네임으로 입장</button>
        </form>
        <div className="user-access-note"><strong>알아두세요</strong><span>현재 기능은 학습 기록을 나누는 닉네임 방식이며 비밀번호 보안 로그인은 아닙니다. 인터넷에 공개 운영할 때는 별도 인증 서버가 필요합니다.</span></div>
        <button type="button" className="legacy-user-button" onClick={onLegacy}>기존 로컬 자료로 계속</button>
      </div>
    </section>
  </div>
}
