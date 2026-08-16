import type { PublicProblemDetail } from '../api/client'

type HeaderProps = {
  mode?: 'desktop' | 'web'
  onRefresh: () => void
  selectedProblem?: PublicProblemDetail
  onOpenProblems: () => void
  onReset: () => void
}

export function Header({ mode, onRefresh, selectedProblem, onOpenProblems, onReset }: HeaderProps) {
  return (
    <header className="app-header">
      <div className="brand-block">
        <div className="brand-mark" aria-hidden="true">⚡</div>
        <div>
          <h1>전기기능사 시퀀스 결선 시뮬레이터</h1>
          <p>실기 시험 대비 학습 시스템</p>
        </div>
      </div>
      <button type="button" className="header-problem" onClick={onOpenProblems}>
        <span>현재 문제</span>
        <strong>{selectedProblem?.title ?? '문제가 선택되지 않았습니다'}</strong>
        <small>{selectedProblem ? `${selectedProblem.problem_id} · 문제 변경` : '문제 선택하기'}</small>
      </button>
      <div className="header-actions">
        <span className="mode-badge">{mode === 'desktop' ? '데스크톱' : '웹'}</span>
        <button type="button" onClick={onRefresh}>새로고침</button>
        <button type="button" onClick={onReset} disabled={!selectedProblem}>초기화</button>
        <button type="button" disabled>설정</button>
        <button type="button" disabled>도움말</button>
      </div>
    </header>
  )
}
