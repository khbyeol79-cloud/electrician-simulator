import type { AppInfoResponse } from '../api/client'

type StatusBarProps = {
  info?: AppInfoResponse
  error?: string
}

function StatusItem({ label, ready, text }: { label: string; ready: boolean; text: string }) {
  return (
    <div className="status-item">
      <span className={`status-dot ${ready ? 'ready' : 'error'}`} aria-hidden="true" />
      <span>{label}</span>
      <strong>{text}</strong>
    </div>
  )
}

export function StatusBar({ info, error }: StatusBarProps) {
  return (
    <footer className="status-bar" aria-live="polite">
      <StatusItem label="서버" ready={!error} text={error ? '연결 오류' : '연결됨'} />
      <StatusItem
        label="데이터베이스"
        ready={Boolean(info?.database_ready)}
        text={info?.database_ready ? '준비됨' : '확인 중'}
      />
      <StatusItem
        label="문제 폴더"
        ready={Boolean(info?.problems_path_ready)}
        text={info?.problems_path_ready ? '준비됨' : '확인 중'}
      />
      <div className="status-spacer" />
      <span>실행 모드: <strong>{info?.mode === 'desktop' ? '데스크톱' : '웹'}</strong></span>
      <span>버전 <strong>{info?.version ?? '0.5.6'}</strong></span>
    </footer>
  )
}
