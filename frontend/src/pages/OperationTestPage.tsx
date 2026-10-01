import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  applyOperationAction,
  createOperationSession,
  createPracticeOperationSession,
  deleteOperationSession,
  getOperationSetup,
  resetOperationSession,
  runOperationCheck,
  runOperationRequirements,
  type BehaviorRequirementSummary,
  type BehaviorScenarioResult,
  type OperationCheckResult,
  type OperationSessionState,
  type OperationSetup,
  type PublicProblemDetail,
} from '../api/client'
import { OperationBoard } from '../features/operation/components/OperationBoard'
import { PlaceholderPage } from './PlaceholderPage'
import { ContactTypeBadge } from '../components/ContactTypeBadge'
import { OperationReference } from '../features/operation/components/OperationReference'

const MOTOR_LABELS: Record<string, string> = {
  stopped: '정지', forward: '정회전', reverse: '역회전', phase_loss: '결상',
  phase_sequence_error: '상순서 오류', simultaneous_fault: '동시 여자 오류',
  connection_error: '연결 오류', power_off: '전원 차단', protection_trip: '보호 정지', undetermined: '판정 불가',
}

export function recentOperationEvents(events: string[], limit = 7) {
  let flasherTransitionIncluded = false
  return [...events].reverse().filter((event) => {
    const isFlasherTransition = /출력이 (?:ON|OFF) 구간으로 전환되었습니다\.$/.test(event)
    if (!isFlasherTransition) return true
    if (flasherTransitionIncluded) return false
    flasherTransitionIncluded = true
    return true
  }).slice(0, limit)
}

export function OperationTestPage({ problem }: { problem?: PublicProblemDetail }) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const workspaceId = searchParams.get('workspace') || 'main'
  const practiceMode = Boolean(problem?.capabilities.operation_previewable && !problem.capabilities.operation_gradable)
  const unavailable = Boolean(problem && !problem.capabilities.operation_previewable && !problem.capabilities.operation_gradable)
  const [setup, setSetup] = useState<OperationSetup>()
  const [boardView, setBoardView] = useState<'board' | 'schematic' | 'layout'>('layout')
  const [session, setSession] = useState<OperationSessionState>()
  const [checkResult, setCheckResult] = useState<OperationCheckResult>()
  const [requirementResult, setRequirementResult] = useState<BehaviorRequirementSummary>()
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string>()
  const sessionRef = useRef<string | undefined>(undefined)
  const tickingRef = useRef(false)
  const actionQueueRef = useRef<Promise<void>>(Promise.resolve())
  const activeMomentaryRef = useRef(new Set<string>())

  useEffect(() => {
    if (!problem || unavailable) return
    const controller = new AbortController()
    let createdSession: string | undefined
    setLoading(true); setError(undefined); setSetup(undefined); setSession(undefined); setCheckResult(undefined); setRequirementResult(undefined)
    getOperationSetup(problem.problem_id, controller.signal, workspaceId)
      .then(async (value) => {
        if (controller.signal.aborted) return
        setSetup(value)
        if (value.operation_ready && (value.wiring_snapshot || practiceMode)) {
          const state = practiceMode
            ? await createPracticeOperationSession(problem.problem_id, value.problem_version, workspaceId)
            : await createOperationSession(problem.problem_id, value.problem_version, value.wiring_snapshot?.attempt_id)
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
  }, [practiceMode, problem, unavailable, workspaceId])

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

  const pressMomentary = useCallback((controlId: string) => {
    if (activeMomentaryRef.current.has(controlId)) return
    activeMomentaryRef.current.add(controlId)
    void perform({ action: 'press_control', control_id: controlId })
  }, [perform])

  const releaseMomentaryId = useCallback((controlId: string) => {
    if (!activeMomentaryRef.current.delete(controlId)) return
    void perform({ action: 'release_control', control_id: controlId })
  }, [perform])

  const releaseMomentary = useCallback(() => {
    const active = [...activeMomentaryRef.current]
    activeMomentaryRef.current.clear()
    active.forEach((controlId) => void perform({ action: 'release_control', control_id: controlId }))
  }, [perform])

  useEffect(() => {
    window.addEventListener('blur', releaseMomentary)
    window.addEventListener('pointerup', releaseMomentary)
    window.addEventListener('pointercancel', releaseMomentary)
    const visibility = () => { if (document.hidden) releaseMomentary() }
    document.addEventListener('visibilitychange', visibility)
    return () => {
      window.removeEventListener('blur', releaseMomentary)
      window.removeEventListener('pointerup', releaseMomentary)
      window.removeEventListener('pointercancel', releaseMomentary)
      document.removeEventListener('visibilitychange', visibility)
      activeMomentaryRef.current.clear()
    }
  }, [releaseMomentary])

  const energizedSocketIds = useMemo(() => {
    const coilOwners = new Map(problem?.circuit.coils.map((coil) => [coil.coil_id, coil.owner_device_id]) ?? [])
    const activeOwners = new Set<string>()
    for (const [coilId, energized] of Object.entries(session?.coils ?? {})) {
      if (!energized) continue
      activeOwners.add(coilOwners.get(coilId) ?? coilId.replace(/-COIL$/, ''))
    }
    return activeOwners
  }, [problem, session?.coils])
  const contactDefinitions = useMemo(
    () => new Map(problem?.circuit.contacts.map((item) => [item.contact_id, item]) ?? []),
    [problem],
  )
  const scenarioResults = useMemo<BehaviorScenarioResult[]>(() => {
    if (requirementResult?.scenarios?.length) return requirementResult.scenarios
    const unique = new Map<string, BehaviorScenarioResult>()
    for (const item of setup?.behavior_requirements ?? []) {
      if (!item.scenario_id) continue
      const scenarioId = item.scenario_id
      if (unique.has(scenarioId)) continue
      unique.set(scenarioId, {
        scenario_id: scenarioId,
        label: item.scenario_label ?? item.label,
        status: 'not_run',
        current_observation: '',
        missing_conditions: [],
        next_action: item.next_action ?? '조작부에서 요구 동작을 실행한 뒤 확인하세요.',
      })
    }
    return [...unique.values()]
  }, [requirementResult?.scenarios, setup?.behavior_requirements])
  const requirementCount = scenarioResults.length
  const recentEvents = useMemo(() => recentOperationEvents(session?.events ?? []), [session?.events])

  if (!problem) return <PlaceholderPage stage="3단계" title="동작시험" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="▶" />
  if (unavailable) return <PlaceholderPage stage="3단계 · 검증 대기" title="공식 동작 정의 교차검증 중" description="정답 네트워크와 문제별 동작 조건이 검증된 뒤 승인 결선 기반 동작시험이 열립니다." icon="▶" />

  const placements = setup?.device_layout?.fixed_placements ?? []
  const connections = setup?.wiring_snapshot?.connections ?? setup?.wiring_draft?.connections ?? []
  const submission = setup?.wiring_submission

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
    try { setSession(await resetOperationSession(sessionRef.current)); setCheckResult(undefined); setRequirementResult(undefined); setError(undefined) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '동작시험을 초기화할 수 없습니다.') }
    finally { setBusy(false) }
  }

  const runRequirements = async () => {
    if (!sessionRef.current) return
    setBusy(true)
    try { setRequirementResult(await runOperationRequirements(sessionRef.current)); setError(undefined) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '요구 동작을 확인할 수 없습니다.') }
    finally { setBusy(false) }
  }

  return <section className="workspace-page operation-workspace">
    <header className="workspace-toolbar operation-header">
      <div><span>3단계 · 동작시험</span><h2>동작시험</h2></div>
      <div className="wiring-stats"><span>전원 {session?.power_state === 'on' ? 'ON' : session?.power_state === 'tripped' ? '차단' : 'OFF'}</span><span>결선 제출 #{setup?.wiring_snapshot?.attempt_id ?? '-'}</span></div>
    </header>
    {loading && <div className="circuit-loading">동작 회로와 정상 제출 배선을 준비하는 중입니다.</div>}
    {error && <div className="circuit-load-error compact" role="alert"><strong>동작시험 안내</strong><span>{error}</span></div>}
    {!loading && setup && <div className="operation-layout with-left-sidebar">
      <aside className="wiring-panel work-left-sidebar operation-status-sidebar" aria-label="기구 상태 패널">{session ? <>          <section className="operation-status-panel">
            <div className="operation-section-title"><strong>기구 상태</strong><span>{session.stable ? '안정' : '계산 오류'}</span></div>
            <div className="status-chip-grid">
              {Object.entries(session.coils).map(([id, on]) => <div key={id} className={`status-chip ${on ? 'on' : ''}`}><span>{id}</span><b>{on ? 'ON' : 'OFF'}</b></div>)}
              {Object.entries(session.timers).map(([id, timer]) => <div key={id} className={`status-chip timer ${timer.status}`}><span>{id}</span><b>{timer.status === 'completed' ? `완료 ${timer.elapsed_ms}/${timer.delay_ms}ms` : timer.status === 'timing' ? `계시 ${timer.elapsed_ms}/${timer.delay_ms}ms` : `정지 0/${timer.delay_ms}ms`}</b></div>)}
              {Object.entries(session.flashers ?? {}).map(([id, flasher]) => <div key={id} className={`status-chip flasher ${flasher.status}`}><span>{flasher.label} 플리커</span><b>{flasher.status === 'stopped' ? '정지' : `${flasher.status.toUpperCase()} · ${flasher.elapsed_ms}/${flasher.interval_ms}ms`}</b></div>)}
              {Object.entries(session.level_relays ?? {}).map(([id, level]) => <div key={id} className={`status-chip level ${level.detected ? 'on' : ''}`}><span>{level.label} 수위</span><b>{!level.powered ? '무전원' : !level.wiring_ready ? '전극 결선 확인' : level.detected ? '감지' : '대기'}</b></div>)}
              {Object.entries(session.indicators).map(([id, state]) => <div key={id} className={`status-chip lamp ${state}`}><span>{id} 표시등</span><b>{state.toUpperCase()}</b></div>)}
              {Object.entries(session.audible_outputs ?? {}).map(([id, state]) => <div key={id} className={`status-chip audible ${state}`}><span>{id} 부저</span><b>{state === 'on' ? '울림' : '정지'}</b></div>)}
              {Object.entries(session.motors).map(([id, state]) => <div key={id} className={`status-chip motor ${state}`}><span>{id} 모터</span><b><i aria-hidden="true">{state === 'forward' ? '↻' : state === 'reverse' ? '↺' : '■'}</i>{MOTOR_LABELS[state] ?? state}</b></div>)}
              {Object.entries(session.protections).map(([id, state]) => <div key={id} className={`status-chip protection ${state.status}`}><span>{id} 보호</span><b>{state.status === 'normal' ? '정상' : state.status === 'reset_required' ? '복귀 필요' : '트립'}</b></div>)}
            </div>
            <div className="contact-state-list"><strong>접점 상태</strong>{Object.entries(session.contacts).map(([id, state]) => {
              const definition = contactDefinitions.get(id)
              const position = session.changeover_positions?.[id]
              if (position) return <span key={id} className="changeover">{id} · NC {position === 'no' ? '열림' : '닫힘'} / NO {position === 'no' ? '닫힘' : '열림'}</span>
              if (definition?.contact_type !== 'CHANGEOVER') return <span key={id} className={state}>{id} · {state === 'closed' ? '닫힘' : '열림'}</span>
              const active = definition.controller_type === 'coil'
                ? Boolean(definition.controller_id && session.coils[definition.controller_id])
                : definition.controller_type === 'timer'
                  ? Boolean(definition.controller_id && session.timers[definition.controller_id]?.status === 'completed')
                  : definition.controller_type === 'protection'
                    ? Boolean(definition.controller_id && session.protections[definition.controller_id]?.status !== 'normal')
                    : false
              return <span key={id} className="changeover">{id} · NC {active ? '열림' : '닫힘'} / NO {active ? '닫힘' : '열림'}</span>
            })}</div>
          </section></> : <p>동작시험을 준비하면 기구 상태가 표시됩니다.</p>}</aside>
      <div className="wiring-stage operation-stage">
        <div className="wiring-toolbar operation-view-tabs" aria-label="동작시험 제어함 안내">
          {problem.problem_type === 'official' && <div className="analysis-source-tabs" role="group" aria-label="동작시험 보기 선택">{([{ value: 'board', label: '제어함 결선' }, { value: 'schematic', label: '시퀀스 회로도' }, { value: 'layout', label: '배관·배치도' }] as const).map(item => <button key={item.value} type="button" className={boardView === item.value ? 'active' : ''} aria-pressed={boardView === item.value} onClick={() => setBoardView(item.value)}>{item.label}</button>)}</div>}
          <span className="mounting-readonly-note">배선과 기구는 읽기 전용 · 화면 자동 맞춤</span>
        </div>
        {boardView === 'board' || problem.problem_type !== 'official' ? <OperationBoard board={setup.board} connections={connections} placements={placements} zoom={1} energizedSocketIds={energizedSocketIds} /> : <OperationReference problemId={problem.problem_id} view={boardView} session={session} />}
      </div>
      <aside className="wiring-panel operation-panel">
        <section className={setup.operation_ready ? 'operation-ready-card' : 'operation-next-warning'}>
          <span className="panel-kicker">동작시험 상태</span>
          <h3>{setup.operation_ready ? '논리 동작시험 준비 완료' : setup.preview_allowed ? '읽기 전용 미리보기' : '결선 확인 필요'}</h3>
          <p>{setup.message}</p>
          <small>배선 기준: {setup.wiring_source === 'accepted_submission' ? '정상 제출 스냅샷' : setup.wiring_source === 'practice_draft' ? '사용자 연습 초안' : setup.wiring_source === 'draft_preview' ? '임시저장 미리보기' : '없음'}</small>
          {session && <small>계산 방식: {session.simulation_mode === 'actual_wiring' ? '실제 결선' : '기존 호환'}{session.catalog_composed ? ' · 기구 카탈로그 적용' : ''}</small>}
        </section>

        {session && <>
          <section className="operation-controls" aria-label="동작시험 조작부">
            <div className="operation-section-title"><strong>조작부</strong><span>{session.power_state === 'tripped' ? '오류 차단' : session.powered ? '전원 투입' : '전원 차단'}</span></div>
            <button className={`power-switch ${session.powered ? 'on' : ''}`} disabled={busy || (!session.powered && !session.power_permitted)} onClick={() => void perform({ action: 'set_power', value: !session.powered })}>전원 {session.powered ? 'OFF' : 'ON'}</button>
            {practiceMode && <div className={`operation-faults ${session.safety_status === 'blocked' ? 'active' : ''}`}><strong>연습 안전 검사 · {session.safety_status === 'blocked' ? '전원 차단' : session.safety_status === 'attention' ? '확인 필요' : '투입 가능'}</strong>{session.safety_issues.length ? session.safety_issues.map((issue) => <p key={issue.code}>{issue.message}</p>) : <p>정답과 무관한 기본 단락 검사에서 차단 항목이 없습니다.</p>}</div>}
            <div className="control-grid">{Object.entries(session.controls).map(([controlId, state]) => state.mode === 'maintained' ?
              <button key={controlId} disabled={busy} className={`control-button maintained ${state.active ? 'active' : ''}`} onClick={() => void perform({ action: 'toggle_control', control_id: controlId })} aria-pressed={state.active}><b>{controlId}<ContactTypeBadge contactType={state.contact_type} /></b><span>{state.control_type === 'selector' ? state.active ? '자동(A)' : '수동(M)' : state.active ? '작동' : '복귀'}</span></button>
              : <button key={controlId} className={`control-button momentary ${state.active ? 'active' : ''}`}
                disabled={busy}
                onPointerDown={(event) => { event.currentTarget.setPointerCapture?.(event.pointerId); pressMomentary(controlId) }}
                onPointerUp={() => releaseMomentaryId(controlId)}
                onPointerCancel={() => releaseMomentaryId(controlId)}
                onPointerLeave={() => releaseMomentaryId(controlId)}
                onKeyDown={(event) => { if (!event.repeat && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); pressMomentary(controlId) } }}
                onKeyUp={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); releaseMomentaryId(controlId) } }}
                onBlur={() => releaseMomentaryId(controlId)} aria-pressed={state.active}><b>{controlId}<ContactTypeBadge contactType={state.contact_type} /></b><span>{state.active ? '누름' : '복귀'}</span></button>
            )}</div>
            {Object.entries(session.level_relays ?? {}).length > 0 && <div className="level-controls">
              <p>수위 입력은 E1·E2·E3가 실제로 결선되고 FLS 전원이 공급될 때만 접점에 반영됩니다.</p>
              {Object.entries(session.level_relays ?? {}).map(([levelId, level]) => <button key={levelId} disabled={busy} className={level.requested ? 'active' : ''} onClick={() => void perform({ action: 'set_level', target_id: levelId, value: !level.requested })}>{level.label} · {level.requested ? '수위 감지 해제' : '수위 감지'}</button>)}
            </div>}
            {Object.entries(session.protections).length > 0 && <div className="protection-controls">
              <p>아래 기능은 실제 전류 측정이 아닌 교육용 과부하 시뮬레이션입니다.</p>
              {Object.entries(session.protections).map(([protectionId, protection]) => <div key={protectionId}>
                <span>{protection.label} 전원: {protection.powered === false ? '무전원' : 'A1-A2 인가'}</span>
                <button className="fault-trigger" disabled={busy || protection.status !== 'normal' || protection.powered === false} onClick={() => void perform({ action: 'trigger_fault', target_id: protectionId, fault_type: 'overload' })}>{protection.label} 과부하 발생</button>
                <button className="fault-reset" disabled={busy || protection.status === 'normal'} onClick={() => void perform({ action: 'reset_fault', target_id: protectionId })}>{protection.label} 복귀</button>
              </div>)}
              <p className="eocr-pin-guide">12P EOCR: 4=96(NC 출력), 5=98(NO 출력), 6=A1, 10=95(NC 공통), 11=97(NO 공통), 12=A2 · 95–97 내부 공통</p>
            </div>}
            {Object.entries(session.fuses ?? {}).length > 0 && <div className="fuse-controls"><p>각 퓨즈 채널은 독립적으로 단선 시험합니다.</p>{Object.entries(session.fuses ?? {}).map(([channelId, fuse]) => <button key={channelId} className={fuse.status === 'open' ? 'fault-reset' : 'fault-trigger'} disabled={busy} onClick={() => void perform({ action: 'set_fuse_state', target_id: channelId, value: fuse.status === 'open' })}>{fuse.label} ({fuse.terminal_a_id}–{fuse.terminal_b_id}) · {fuse.status === 'open' ? '복구' : '단선'}</button>)}</div>}
          </section>



          {Object.keys(session.interlocks).length > 0 && <section className="operation-interlocks">
            <div className="operation-section-title"><strong>인터록 상태</strong><span>동시 투입 방지</span></div>
            {Object.entries(session.interlocks).map(([id, state]) => <p key={id} className={state.status}><b>{state.type === 'electrical' ? '전기적' : '기계적'}</b><span>{state.label}</span><em>{state.status === 'ready' ? '대기' : state.status === 'blocking' ? `${state.blocked_contactor_id === 'all' ? '양쪽' : state.blocked_contactor_id ?? '반대편'} 차단` : '이상'}</em></p>)}
          </section>}

          <section className={session.faults.length ? 'operation-faults active' : 'operation-faults'}>
            <strong>현재 오류</strong>
            {session.faults.length ? session.faults.map((fault) => <p key={fault.code}>{fault.message}</p>) : <p>검출된 오류가 없습니다.</p>}
          </section>

          <section className="operation-log"><strong>최근 동작 기록</strong><ol>{recentEvents.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ol></section>

          {practiceMode && requirementCount === 0 && <p className="operation-manual-note">문제별 요구사항은 아직 정의 전입니다. 현재 결선의 전기·기구 동작을 조작부에서 직접 확인하세요.</p>}
          <div className="operation-actions">{!practiceMode && <button disabled={busy} onClick={() => void runCheck()}>자동 동작검사</button>}{practiceMode && requirementCount > 0 && <button disabled={busy} onClick={() => void runRequirements()}>{requirementCount}개 요구사항 확인</button>}<button className="secondary-action" disabled={busy} onClick={() => void reset()}>전체 상태·타이머 초기화</button></div>
          {checkResult && <section className={`operation-check-result ${checkResult.gradable ? checkResult.overall_passed ? 'passed' : 'failed' : 'warning'}`} role="status"><strong>{checkResult.overall_passed ? '동작시험 완료' : checkResult.gradable ? '재확인 필요' : '채점 불가'}</strong><p>{checkResult.message}</p><span>{checkResult.passed_count}/{checkResult.total_count} 통과</span></section>}
          {practiceMode && scenarioResults.length > 0 && <section className="operation-requirements" role="status">
            <strong>현재 결선의 {requirementCount}개 동작 요구사항</strong>
            {requirementResult && <p>{requirementResult.message}</p>}
            <ul>{scenarioResults.map((item) => <li key={item.scenario_id} className={item.status}>
              <div className="requirement-title"><span>{item.label.replace(/^PDF\s*8\s*쪽\s*[·:–-]?\s*/i, '')}</span><b>{item.status === 'satisfied' ? '확인 · 충족' : item.status === 'unsatisfied' ? '확인 · 미충족' : item.status === 'unavailable' ? '확인 불가' : '미확인'}</b></div>
              {item.status !== 'not_run' && item.current_observation && <p>{item.current_observation}</p>}
              <details><summary>동작 순서·확인 항목</summary><ol>{(setup?.behavior_requirements ?? []).filter((requirement) => requirement.scenario_id === item.scenario_id).map((requirement) => <li key={requirement.requirement_id}>{requirement.label}</li>)}</ol></details>
              {item.missing_conditions.length > 0 && <details><summary>부족한 동작 조건 {item.missing_conditions.length}개</summary><ul>{item.missing_conditions.map((condition) => <li key={condition}>{condition}</li>)}</ul></details>}
              <small>다음 조작: {item.next_action}</small>
            </li>)}</ul>
          </section>}
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
