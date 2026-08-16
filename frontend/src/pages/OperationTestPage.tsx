import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getOperationSetup, type OperationSetup, type PublicProblemDetail } from '../api/client'
import { OperationBoard } from '../features/operation/components/OperationBoard'
import { PlaceholderPage } from './PlaceholderPage'

export function OperationTestPage({ problem }: { problem?: PublicProblemDetail }) {
  const navigate = useNavigate()
  const [setup, setSetup] = useState<OperationSetup>()
  const [zoom, setZoom] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>()

  useEffect(() => {
    if (!problem) return
    const controller = new AbortController()
    setLoading(true); setError(undefined); setSetup(undefined); setZoom(1)
    getOperationSetup(problem.problem_id, controller.signal)
      .then(setSetup)
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '동작시험 준비 정보를 불러올 수 없습니다.')
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [problem])

  if (!problem) return <PlaceholderPage stage="3단계" title="동작시험" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="▶" />

  const placements = setup?.device_layout?.fixed_placements ?? []
  const connections = setup?.wiring_draft?.connections ?? []
  const submission = setup?.wiring_submission

  return <section className="workspace-page operation-workspace">
    <header className="workspace-toolbar operation-header">
      <div><span>3단계 · 동작시험</span><h2>동작시험</h2></div>
      <div className="wiring-stats"><span>결선 {connections.length}</span><span>기구 {placements.length}</span></div>
    </header>
    {loading && <div className="circuit-loading">완성된 제어함과 고정 기구 배치를 준비하는 중입니다.</div>}
    {error && <div className="circuit-load-error" role="alert"><strong>동작시험 화면을 표시할 수 없습니다.</strong><span>{error}</span></div>}
    {!loading && !error && setup && <div className="operation-layout">
      <div className="wiring-stage operation-stage">
        <div className="wiring-toolbar" aria-label="동작시험 제어함 보기 도구">
          <button aria-label="확대" onClick={() => setZoom((value) => Math.min(1.4, value + .1))}>＋</button>
          <button aria-label="축소" onClick={() => setZoom((value) => Math.max(.7, value - .1))}>－</button>
          <button onClick={() => setZoom(1)}>화면 맞춤</button>
          <span className="mounting-readonly-note">배선과 기구는 읽기 전용입니다.</span>
        </div>
        <OperationBoard board={setup.board} connections={connections} placements={placements} zoom={zoom} />
      </div>
      <aside className="wiring-panel operation-panel">
        <section>
          <span className="panel-kicker">동작시험 준비</span>
          <h3>{setup.operation_ready ? '결선 확인 완료' : setup.preview_allowed ? '가상 문제 미리보기' : '결선 확인 필요'}</h3>
          <p>{setup.message}</p>
        </section>
        <section className={setup.device_layout ? 'operation-ready-card' : 'mounting-wiring-warning'}>
          <strong>{setup.device_layout ? '기구 자동 삽입' : '기구 배치 없음'}</strong>
          <p>{setup.device_layout ? `${placements.length}개 기구가 문제지에 지정된 소켓 위치에 자동으로 삽입되었습니다.` : '이 문제의 기구 배치 정보가 준비되지 않았습니다.'}</p>
        </section>
        <section>
          <span className="panel-kicker">최근 결선 제출</span>
          <dl>
            <div><dt>제출 횟수</dt><dd>{submission?.attempt_count ?? 0}회</dd></div>
            <div><dt>정상 연결</dt><dd>{submission?.last_correct_count ?? 0}/{submission?.required_count ?? 0}</dd></div>
            <div><dt>결선 상태</dt><dd>{setup.operation_ready ? '확인 완료' : setup.preview_allowed ? '채점 불가' : '확인 필요'}</dd></div>
            <div><dt>화면 상태</dt><dd>읽기 전용</dd></div>
          </dl>
        </section>
        <section className="operation-next-warning">
          <strong>동작시험 기능은 다음 개발 단계에서 구현됩니다.</strong>
          <p>현재 버전에서는 전원을 투입하거나 릴레이·타이머·램프·모터의 동작 결과를 계산하지 않습니다.</p>
        </section>
        <button className="submit-circuit secondary-action" type="button" onClick={() => navigate('/wiring')}>결선 화면으로 돌아가기</button>
      </aside>
    </div>}
  </section>
}
