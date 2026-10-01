import type { PublicProblemDetail } from '../api/client'
import { NavLink } from 'react-router-dom'
import type { UserProfile } from '../features/user/userProfile'
import { StageNavigation } from './StageNavigation'
import { currentAuthSession } from '../features/user/authSession'
import { useState } from 'react'
import { UsageHelp } from './UsageHelp'

type HeaderProps = {
  onRefresh: () => void
  selectedProblem?: PublicProblemDetail
  onOpenProblems: () => void
  onReset: () => void
  userProfile: UserProfile
  onOpenUser: () => void
}

export function Header({ onRefresh, selectedProblem, onOpenProblems, onReset, userProfile, onOpenUser }: HeaderProps) {
  const [helpOpen, setHelpOpen] = useState(false)
  return (
    <><header className="app-header">
      <div className="brand-block">
        <div className="brand-mark" aria-hidden="true">⚡</div>
        <div>
          <h1>전기기능사 시퀀스 결선 시뮬레이터</h1>
          <p>실기 시험 대비 학습 시스템</p>
        </div>
      </div>
      <p className="header-purpose">해당 프로그램은 동작 여부만 판별합니다</p>
      <button type="button" className="header-problem" onClick={onOpenProblems}>
        <span>현재 문제</span>
        <strong>{selectedProblem?.title ?? '문제가 선택되지 않았습니다'}</strong>
        <small>{selectedProblem ? `${selectedProblem.problem_id} · 문제 변경` : '문제 선택하기'}</small>
      </button>
      <div className="header-actions">
        {currentAuthSession()?.is_admin && <NavLink to="/admin" className="free-circuit-link">서버 관리</NavLink>}
        <span id="workspace-menu-slot" />
        <button type="button" className="header-user" onClick={onOpenUser} title="사용자 전환"><span>사용자</span><strong>{userProfile.nickname}</strong></button>
        <StageNavigation />
        <NavLink className={({ isActive }) => `free-circuit-link${isActive ? ' active' : ''}`} to="/free-circuit">자유회로 실험</NavLink>
        <button type="button" onClick={onRefresh}>새로고침</button>
        <button type="button" onClick={onReset} disabled={!selectedProblem}>초기화</button>
        <button type="button" onClick={() => setHelpOpen(true)}>사용법</button>
      </div>
    </header>{helpOpen && <UsageHelp onClose={() => setHelpOpen(false)} />}</>
  )
}
