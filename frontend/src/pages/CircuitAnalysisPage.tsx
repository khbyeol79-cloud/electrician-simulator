import { useEffect, useState } from 'react'
import {
  getCircuitSummary,
  getSocketTypes,
  type CircuitSummary,
  type PublicProblemDetail,
  type SocketType,
} from '../api/client'
import { SocketPreview } from '../components/SocketPreview'
import { PlaceholderPage } from './PlaceholderPage'

export function CircuitAnalysisPage({ problem }: { problem?: PublicProblemDetail }) {
  const [summary, setSummary] = useState<CircuitSummary>()
  const [sockets, setSockets] = useState<SocketType[]>([])
  const [error, setError] = useState<string>()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!problem) {
      setSummary(undefined)
      setSockets([])
      setError(undefined)
      return
    }
    const controller = new AbortController()
    setLoading(true)
    setError(undefined)
    Promise.all([
      getCircuitSummary(problem.problem_id, controller.signal),
      getSocketTypes(controller.signal),
    ])
      .then(([nextSummary, nextSockets]) => {
        setSummary(nextSummary)
        setSockets(nextSockets)
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : '회로 데이터를 불러올 수 없습니다.')
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [problem])

  if (!problem) {
    return <PlaceholderPage stage="1단계" title="회로도 분석" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="⌁" />
  }

  return (
    <section className="workspace-page circuit-diagnostics">
      <header className="workspace-toolbar">
        <div><span>1단계 · 데이터 진단</span><h2>회로도 분석</h2></div>
        <div className="toolbar-buttons"><button type="button" disabled>회로 확대</button></div>
      </header>
      <div className="diagnostic-scroll">
        {error && <div className="diagnostic-error" role="alert"><strong>회로 데이터를 불러오지 못했습니다.</strong><span>{error}</span></div>}
        {loading && <div className="diagnostic-loading">회로 데이터와 소켓 규격을 확인하는 중입니다.</div>}
        {summary && !loading && (
          <>
            <section className="circuit-summary-panel" aria-label="회로 데이터 요약">
              <div className="summary-heading">
                <div><span>선택 문제</span><h3>{summary.problem_title}</h3></div>
                <span className="validation-badge">✓ 참조 무결성 정상</span>
              </div>
              <div className="summary-metrics">
                <div><strong>{summary.device_count}</strong><span>장치</span></div>
                <div><strong>{summary.terminal_count}</strong><span>단자</span></div>
                <div><strong>{summary.contact_count}</strong><span>접점</span></div>
                <div><strong>{summary.coil_count}</strong><span>코일</span></div>
                <div><strong>{summary.warning_count}</strong><span>경고</span></div>
              </div>
              <div className="structure-notice">
                <strong>구조 확인용 샘플</strong>
                <span>현재 샘플은 실제 정답이 아닌 <code>structure_only</code> 데이터입니다. 미검증 정답 경고는 오류가 아닙니다.</span>
              </div>
            </section>
            <section className="socket-catalog-panel" aria-label="소켓 규격 미리보기">
              <div className="panel-heading"><span>공통 카탈로그</span><h3>소켓 규격 미리보기</h3><p>화면 좌표와 전기적 의미를 분리한 물리 핀 배열입니다.</p></div>
              <div className="socket-preview-grid">
                {sockets.map((socket) => <SocketPreview key={socket.socket_type_id} socket={socket} />)}
              </div>
            </section>
          </>
        )}
      </div>
    </section>
  )
}
