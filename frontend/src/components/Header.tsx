type HeaderProps = {
  mode?: 'desktop' | 'web'
  onRefresh: () => void
}

export function Header({ mode, onRefresh }: HeaderProps) {
  return (
    <header className="app-header">
      <div className="brand-block">
        <div className="brand-mark" aria-hidden="true">⚡</div>
        <div>
          <h1>전기기능사 시퀀스 결선 시뮬레이터</h1>
          <p>실기 시험 대비 학습 시스템</p>
        </div>
      </div>
      <div className="header-problem">
        <span>현재 문제</span>
        <strong>문제가 선택되지 않았습니다</strong>
      </div>
      <div className="header-actions">
        <span className="mode-badge">{mode === 'desktop' ? '데스크톱' : '웹'}</span>
        <button type="button" onClick={onRefresh}>새로고침</button>
        <button type="button" disabled>초기화</button>
        <button type="button" disabled>설정</button>
        <button type="button" disabled>도움말</button>
      </div>
    </header>
  )
}

