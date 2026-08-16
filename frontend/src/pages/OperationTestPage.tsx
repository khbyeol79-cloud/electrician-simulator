import { useCallback, useEffect, useMemo, useRef, useState, type PointerEventHandler } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  applyOperationAction,
  createOperationSession,
  deleteOperationSession,
  getOperationSetup,
  resetOperationSession,
  runOperationCheck,
  type OperationCheckResult,
  type OperationSessionState,
  type OperationSetup,
  type PublicProblemDetail,
} from '../api/client'
import { OperationBoard } from '../features/operation/components/OperationBoard'
import { PlaceholderPage } from './PlaceholderPage'

const MOTOR_LABELS: Record<string, string> = {
  stopped: '정지', forward: '정회전', reverse: '역회전', phase_loss: '결상',
  simultaneous_fault: '동시 여자 오류', connection_error: '연결 오류',
}

export function OperationTestPage({ problem }: { problem?: PublicProblemDetail }) {
  const navigate = useNavigate()
  const [setup, setSetup] = useState<OperationSetup>()
  const [session, setSession] = useState<OperationSessionState>()
  const [checkResult, setCheckResult] = useState<OperationCheckResult>()
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const sessionRef = useRef<string | undefined>(undefined)
  const tickingRef = useRef(false)
  const actionQueueRef = useRef<Promise<void>>(Promise.resolve())
  const dragRef = useRef<{ pointerId: number; x: number; y: number; panX: number; panY: number } | undefined>(undefined)

  useEffect(() => {
    if (!problem) return
    const controller = new AbortController()
    let createdSession: string | undefined
    setLoading(true); setError(undefined); setSetup(undefined); setSession(undefined); setCheckResult(undefined); setZoom(1); setPan({ x: 0, y: 0 })
    getOperationSetup(problem.problem_id, controller.signal)
      .then(async (value) => {
        if (controller.signal.aborted) return
        setSetup(value)
        if (value.operation_ready && value.wiring_snapshot) {
          const state = await createOperationSession(problem.problem_id, value.problem_version, value.wiring_snapshot.attempt_id)
          createdSession = state.session_id
          sessionRef.current = state.session_id
          if (!controller.signal.aborted) setSession(state)
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '동작시험 정보를 불러올 수 없습니다.')
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => {
      controller.abort()
      if (createdSession) void deleteOperationSession(createdSession).catch(() => undefined)
      if (sessionRef.current === createdSession) sessionRef.current = undefined
    }
  }, [problem])

  const perform = useCallback((action: Record<string, unknown>) => {
    const sessionId = sessionRef.current
    if (!sessionId) return Promise.resolve()
    const task = actionQueueRef.current.then(async () => {
      tickingRef.current = true
      try {
        const state = await applyOperationAction(sessionId, action)
        setSession(state); setError(undefined)
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : '입력기구를 조작할 수 없습니다.')
      } finally {
        tickingRef.current = false
      }
    })
    actionQueueRef.current = task.catch(() => undefined)
    return task
  }, [])

  useEffect(() => {
    if (!session?.powered) return
    const timer = window.setInterval(() => { if (!tickingRef.current) void perform({ action: 'advance_time', milliseconds: 250 }) }, 250)
    return () => window.clearInterval(timer)
  }, [perform, session?.powered])

  const releaseMomentary = useCallback(() => {
    if (!session) return
    Object.entries(session.controls).forEach(([controlId, state]) => {
      if (state.mode === 'momentary' && state.active) void perform({ action: 'release_control', control_id: controlId })
    })
  }, [perform, session])

  useEffect(() => {
    window.addEventListener('blur', releaseMomentary)
    return () => window.removeEventListener('blur', releaseMomentary)
  }, [releaseMomentary])

  const energizedSocketIds = useMemo(() => {
    const activeOwners = new Set(problem?.circuit.coils.filter((coil) => session?.coils[coil.coil_id]).map((coil) => coil.owner_device_id) ?? [])
    return activeOwners
  }, [problem, session?.coils])

  if (!problem) return <PlaceholderPage stage="3단계" title="동작시험" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="▶" />

  const placements = setup?.device_layout?.fixed_placements ?? []
  const connections = setup?.wiring_snapshot?.connections ?? setup?.wiring_draft?.connections ?? []
  const submission = setup?.wiring_submission

  const fit = () => { setZoom(1); setPan({ x: 0, y: 0 }) }
  const handleDragStart: PointerEventHandler<SVGSVGElement> = (event) => {
    dragRef.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, panX: pan.x, panY: pan.y }
    event.currentTarget.setPointerCapture(event.pointerId)
  }
  const handleDragMove: PointerEventHandler<SVGSVGElement> = (event) => {
    const drag = dragRef.current
    if (!drag || drag.pointerId !== event.pointerId) return
    setPan({ x: drag.panX + (event.clientX - drag.x) / zoom, y: drag.panY + (event.clientY - drag.y) / zoom })
  }
  const handleDragEnd: PointerEventHandler<SVGSVGElement> = (event) => {
    if (dragRef.current?.pointerId === event.pointerId) dragRef.current = undefined
  }

  const runCheck = async () => {
    if (!sessionRef.current) return
    setBusy(true)
    try { setCheckResult(await runOperationCheck(sessionRef.current)); setError(undefined); window.dispatchEvent(new CustomEvent('electrician:progress-changed')) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '자동 동작검사를 실행할 수 없습니다.') }
    finally { setBusy(false) }
  }

  const reset = async () => {
    if (!sessionRef.current) return
    setBusy(true)
    try { setSession(await resetOperationSession(sessionRef.current)); setCheckResult(undefined); setError(undefined) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '동작시험을 초기화할 수 없습니다.') }
    finally { setBusy(false) }
  }

  return <section className="workspace-page operation-workspace">
    <header className="workspace-toolbar operation-header">
      <div><span>3단계 · 동작시험</span><h2>동작시험</h2></div>
      <div className="wiring-stats"><span>전원 {session?.power_state === 'on' ? 'ON' : session?.power_state === 'tripped' ? '차단' : 'OFF'}</span><span>결선 제출 #{setup?.wiring_snapshot?.attempt_id ?? '-'}</span></div>
    </header>
    {loading && <div className="circuit-loading">동작 회로와 정상 제출 배선을 준비하는 중입니다.</div>}
    {error && <div className="circuit-load-error compact" role="alert"><strong>동작시험 안내</strong><span>{error}</span></div>}
    {!loading && setup && <div className="operation-layout">
      <div className="wiring-stage operation-stage">
        <div className="wiring-toolbar" aria-label="동작시험 제어함 보기 도구">
          <button aria-label="확대" onClick={() => setZoom((value) => Math.min(1.6, value + .1))}>＋</button>
          <button aria-label="축소" onClick={() => setZoom((value) => Math.max(.65, value - .1))}>－</button>
          <button onClick={fit}>화면 맞춤</button>
          <span className="mounting-readonly-note">배선과 기구는 읽기 전용 · 빈 공간을 드래그해 이동</span>
        </div>
        <OperationBoard board={setup.board} connections={connections} placements={placements} zoom={zoom} pan={pan} energizedSocketIds={energizedSocketIds} onPointerDown={handleDragStart} onPointerMove={handleDragMove} onPointerUp={handleDragEnd} />
      </div>
      <aside className="wiring-panel operation-panel">
        <section className={setup.operation_ready ? 'operation-ready-card' : 'operation-next-warning'}>
          <span className="panel-kicker">동작시험 상태</span>
          <h3>{setup.operation_ready ? '논리 동작시험 준비 완료' : setup.preview_allowed ? '읽기 전용 미리보기' : '결선 확인 필요'}</h3>
          <p>{setup.message}</p>
          <small>배선 기준: {setup.wiring_source === 'accepted_submission' ? '정상 제출 스냅샷' : setup.wiring_source === 'draft_preview' ? '임시저장 미리보기' : '없음'}</small>
        </section>

        {session && <>
          <section className="operation-controls" aria-label="동작시험 조작부">
            <div className="operation-section-title"><strong>조작부</strong><span>{session.power_state === 'tripped' ? '오류 차단' : session.powered ? '전원 투입' : '전원 차단'}</span></div>
            <button className={`power-switch ${session.powered ? 'on' : ''}`} disabled={busy} onClick={() => void perform({ action: 'set_power', value: !session.powered })}>전원 {session.powered ? 'OFF' : 'ON'}</button>
            <div className="control-grid">{Object.entries(session.controls).map(([controlId, state]) => state.mode === 'maintained' ?
              <button key={controlId} className={`control-button maintained ${state.active ? 'active' : ''}`} onClick={() => void perform({ action: 'toggle_control', control_id: controlId })} aria-pressed={state.active}><b>{controlId}</b><span>{state.active ? '작동' : '복귀'}</span></button>
              : <button key={controlId} className={`control-button momentary ${state.active ? 'active' : ''}`}
                onPointerDown={() => void perform({ action: 'press_control', control_id: controlId })}
                onPointerUp={() => void perform({ action: 'release_control', control_id: controlId })}
                onPointerCancel={() => void perform({ action: 'release_control', control_id: controlId })}
                onPointerLeave={() => { if (state.active) void perform({ action: 'release_control', control_id: controlId }) }}
                onKeyDown={(event) => { if (!event.repeat && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); void perform({ action: 'press_control', control_id: controlId }) } }}
                onKeyUp={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); void perform({ action: 'release_control', control_id: controlId }) } }}
                onBlur={() => { if (state.active) void perform({ action: 'release_control', control_id: controlId }) }} aria-pressed={state.active}><b>{controlId}</b><span>{state.contact_type} · {state.active ? '누름' : '복귀'}</span></button>
            )}</div>
          </section>

          <section className="operation-status-panel">
            <div className="operation-section-title"><strong>기구 상태</strong><span>{session.stable ? '안정' : '계산 오류'}</span></div>
            <div className="status-chip-grid">
              {Object.entries(session.coils).map(([id, on]) => <div key={id} className={`status-chip ${on ? 'on' : ''}`}><span>{id}</span><b>{on ? 'ON' : 'OFF'}</b></div>)}
              {Object.entries(session.timers).map(([id, timer]) => <div key={id} className={`status-chip timer ${timer.status}`}><span>{id}</span><b>{timer.status === 'completed' ? '완료' : timer.status === 'timing' ? `계시 ${Math.ceil((timer.delay_ms - timer.elapsed_ms) / 1000)}초` : '정지'}</b></div>)}
              {Object.entries(session.indicators).map(([id, state]) => <div key={id} className={`status-chip lamp ${state}`}><span>{id} 표시등</span><b>{state.toUpperCase()}</b></div>)}
              {Object.entries(session.motors).map(([id, state]) => <div key={id} className={`status-chip motor ${state}`}><span>{id} 모터</span><b>{MOTOR_LABELS[state]}</b></div>)}
            </div>
          </section>

          <section className={session.faults.length ? 'operation-faults active' : 'operation-faults'}>
            <strong>현재 오류</strong>
            {session.faults.length ? session.faults.map((fault) => <p key={fault.code}>{fault.message}</p>) : <p>검출된 오류가 없습니다.</p>}
          </section>

          <section className="operation-log"><strong>최근 동작 기록</strong><ol>{session.events.slice(-7).reverse().map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ol></section>

          <div className="operation-actions"><button disabled={busy} onClick={() => void runCheck()}>자동 동작검사</button><button className="secondary-action" disabled={busy} onClick={() => void reset()}>시험 초기화</button></div>
          {checkResult && <section className={`operation-check-result ${checkResult.gradable ? checkResult.overall_passed ? 'passed' : 'failed' : 'warning'}`} role="status"><strong>{checkResult.overall_passed ? '동작시험 완료' : checkResult.gradable ? '재확인 필요' : '채점 불가'}</strong><p>{checkResult.message}</p><span>{checkResult.passed_count}/{checkResult.total_count} 통과</span></section>}
        </>}

        {!session && <section>
          <span className="panel-kicker">최근 결선 제출</span>
          <dl><div><dt>제출 횟수</dt><dd>{submission?.attempt_count ?? 0}회</dd></div><div><dt>정상 연결</dt><dd>{submission?.last_correct_count ?? 0}/{submission?.required_count ?? 0}</dd></div><div><dt>화면 상태</dt><dd>읽기 전용</dd></div></dl>
        </section>}
        <button className="submit-circuit secondary-action" type="button" onClick={() => navigate('/wiring')}>결선 화면으로 돌아가기</button>
      </aside>
    </div>}
  </section>
}
