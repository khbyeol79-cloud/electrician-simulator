import type { AppInfoResponse } from '../api/client'
import type { ServerConnection } from '../features/system/useServerStatus'

type StatusBarProps = {
  info?: AppInfoResponse
  connection: ServerConnection
}

function StatusItem({ label, state, text }: { label: string; state: 'ready' | 'error' | 'waiting'; text: string }) {
  return (
    <div className="status-item">
      <span className={`status-dot ${state}`} aria-hidden="true" />
      <span>{label}</span>
      <strong>{text}</strong>
    </div>
  )
}

export function StatusBar({ info, connection }: StatusBarProps) {
  const connected = connection === 'connected'
  const databaseReady = connected && Boolean(info?.database_ready)
  const problemsReady = connected && Boolean(info?.problems_path_ready)
  return (
    <footer className="status-bar" aria-live="polite">
      <StatusItem label="서버" state={connected ? 'ready' : connection === 'disconnected' ? 'error' : 'waiting'} text={connected ? '연결됨' : connection === 'disconnected' ? '연결 끊김' : '확인 중'} />
      <StatusItem
        label="데이터베이스"
        state={databaseReady ? 'ready' : 'waiting'}
        text={databaseReady ? '준비됨' : '대기 중'}
      />
      <StatusItem
        label="문제 폴더"
        state={problemsReady ? 'ready' : 'waiting'}
        text={problemsReady ? '준비됨' : '대기 중'}
      />
      <div className="status-spacer" />
      <span>버전 <strong>{info?.version ?? '0.13.0'}</strong></span>
    </footer>
  )
}
