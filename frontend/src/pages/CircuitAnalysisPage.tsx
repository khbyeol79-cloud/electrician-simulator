import { SlotNumberExample } from '../components/SlotNumberExample'
import { studyDraftStorage } from '../features/user/authSession'
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  getCircuitAnalysisDraft, getCircuitProgress, getDiagram, getSocketTypes, saveCircuitAnalysisDraft, submitCircuitAttempt,
  layoutReferenceUrl, schematicUrl,
  type CircuitAttemptResult, type CircuitProgress, type PublicProblemDetail,
  type SchematicDiagram, type SocketType,
} from '../api/client'
import { CircuitDiagram, type DiagramAnnotationMarker } from '../components/circuit/CircuitDiagram'
import { CircuitQuestionPanel } from '../components/circuit/CircuitQuestionPanel'
import { circuitDraftKey, restoreCircuitDraft, type CircuitDraft } from '../features/circuit/circuitDraft'
import { PlaceholderPage } from './PlaceholderPage'
import { contactTargets, layoutReferenceDiagram, parseAnnotations, type ContactTarget } from '../features/circuit/analysisAnnotations'
import { activeUserStorageSuffix } from '../features/user/userProfile'
import { AnalysisReferencePage } from '../components/circuit/AnalysisReferencePage'
import { DeviceInternalReference } from '../components/circuit/DeviceInternalReference'

export function CircuitAnalysisPage({ problem }: { problem?: PublicProblemDetail }) {
  const memoMode = Boolean(problem?.capabilities.operation_previewable && !problem.capabilities.operation_gradable)
  const [diagram, setDiagram] = useState<SchematicDiagram>()
  const [sockets, setSockets] = useState<SocketType[]>([])
  const [progress, setProgress] = useState<CircuitProgress>()
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null)
  const [draft, setDraft] = useState<CircuitDraft>({})
  const [result, setResult] = useState<CircuitAttemptResult>()
  const [error, setError] = useState<string>()
  const [notice, setNotice] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [memo, setMemo] = useState('')
  const [selectedDeviceIds, setSelectedDeviceIds] = useState<string[]>([])
  const [selectedSocketIds, setSelectedSocketIds] = useState<string[]>([])
  const [selectedTerminalIds, setSelectedTerminalIds] = useState<string[]>([])
  const [annotations, setAnnotations] = useState<Record<string, string>>({})
  const [selectedAnnotationId, setSelectedAnnotationId] = useState<string | null>(null)
  const [annotationMode, setAnnotationMode] = useState(false)
  const [sourceView, setSourceView] = useState<'schematic' | 'layout' | 'split' | 'operation' | 'internal'>('schematic')
  const [referenceDeviceId, setReferenceDeviceId] = useState('')
  const [memoHydrated, setMemoHydrated] = useState<string | null>(null)
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const pendingSave = useRef<(() => void) | null>(null)

  // Route changes must not discard the last edit while the debounce timer is pending.
  useEffect(() => () => { pendingSave.current?.(); pendingSave.current = null }, [problem?.problem_id])
  const selectedQuestion = useMemo(
    () => problem?.socket_questions.find((item) => item.question_id === selectedQuestionId),
    [problem, selectedQuestionId],
  )

  useEffect(() => {
    if (!problem) return
    const controller = new AbortController()
    setLoading(true)
    setError(undefined)
    setNotice(undefined)
    setResult(undefined)
    setSelectedQuestionId(null)
    setMemoHydrated(null)
    setSelectedAnnotationId(null)
    setReferenceDeviceId('')
    setAnnotationMode(false)
    setDraft(restoreCircuitDraft(problem.problem_id, problem.version))
    Promise.all([
      getDiagram(problem.problem_id, controller.signal),
      memoMode ? Promise.resolve([] as SocketType[]) : getSocketTypes(controller.signal),
      memoMode ? Promise.resolve(undefined) : getCircuitProgress(problem.problem_id, controller.signal),
      memoMode ? getCircuitAnalysisDraft(problem.problem_id, controller.signal) : Promise.resolve(null),
    ]).then(([nextDiagram, nextSockets, nextProgress, analysisDraft]) => {
      setDiagram(nextDiagram)
      setSockets(nextSockets)
      setProgress(nextProgress)
      if (memoMode) {
        setMemo(analysisDraft?.memo ?? '')
        setSelectedDeviceIds(analysisDraft?.selected_device_ids ?? [])
        setSelectedSocketIds(analysisDraft?.selected_socket_ids ?? [])
        setSelectedTerminalIds(analysisDraft?.selected_terminal_ids ?? [])
        setAnnotations(analysisDraft?.annotations ?? {})
        setMemoHydrated(problem.problem_id)
      }
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '회로도를 불러올 수 없습니다.')
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [memoMode, problem])

  useEffect(() => {
    if (!problem || !memoMode || memoHydrated !== problem.problem_id) return
    setSaveState('saving')
    const userId = activeUserStorageSuffix()
    const save = () => {
      pendingSave.current = null
      saveCircuitAnalysisDraft(problem.problem_id, {
        problem_version: problem.version, memo, selected_device_ids: selectedDeviceIds,
        selected_socket_ids: selectedSocketIds, selected_terminal_ids: selectedTerminalIds, annotations,
      }, userId).then(() => setSaveState('saved')).catch(() => setSaveState('error'))
    }
    pendingSave.current = save
    const timer = window.setTimeout(save, 500)
    return () => window.clearTimeout(timer)
  }, [annotations, memo, memoHydrated, memoMode, problem, selectedDeviceIds, selectedSocketIds, selectedTerminalIds])

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setSelectedQuestionId(null)
    }
    window.addEventListener('keydown', listener)
    return () => window.removeEventListener('keydown', listener)
  }, [])

  useEffect(() => {
    const reset = () => { setDraft({}); setResult(undefined); setNotice(undefined); setSelectedQuestionId(null) }
    window.addEventListener('electrician:reset-circuit', reset)
    return () => window.removeEventListener('electrician:reset-circuit', reset)
  }, [])

  if (!problem) {
    return <PlaceholderPage stage="1단계" title="회로도 분석" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="⌁" />
  }

  if (memoMode) {
    const annotationMarkers = parseAnnotations(annotations)
    const selectedMarker = annotationMarkers.find((item) => item.id === selectedAnnotationId)
    const selectedDeviceId = selectedMarker
      ? selectedMarker.deviceId ?? contactTargets(problem.problem_id).find(item => item.id === selectedMarker.id)?.deviceId ?? ''
      : referenceDeviceId
    const updateMarker = (id: string, update: Partial<DiagramAnnotationMarker>) => {
      const current = annotationMarkers.find((item) => item.id === id)
      if (!current) return
      const next = { ...current, ...update }
      setAnnotations((values) => ({ ...values, [id]: JSON.stringify(next) }))
    }
    const selectContact = (target: ContactTarget) => {
      setAnnotations((values) => values[target.id] ? values : { ...values, [target.id]: JSON.stringify({ ...target, label: '', second: '' }) })
      setSelectedAnnotationId(target.id)
    }
    const addMarker = (point: { x: number; y: number }) => {
      const id = `marker:${typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`}`
      setAnnotations((values) => ({ ...values, [id]: JSON.stringify({ ...point, label: '', second: '', orientation: 'vertical' }) }))
      setSelectedAnnotationId(id)
      setAnnotationMode(false)
    }
    const deleteMarker = (id: string) => {
      setAnnotations((values) => { const next = { ...values }; delete next[id]; return next })
      setSelectedAnnotationId((value) => value === id ? null : value)
    }
    return <section className="workspace-page circuit-workspace analysis-memo-workspace">
      <header className="workspace-toolbar">
        <div><span>1단계 · 개인 회로 분석</span><h2>회로도 분석</h2></div>
        <div className="analysis-save-state" role="status">{saveState === 'saving' ? '자동저장 중…' : saveState === 'saved' ? '자동저장됨' : saveState === 'error' ? '저장 실패' : '개인 분석'}</div>
      </header>
      {loading && <div className="circuit-loading">회로도와 개인 메모를 불러오는 중입니다.</div>}
      {error && <div className="circuit-load-error" role="alert"><strong>회로도를 표시할 수 없습니다.</strong><span>{error}</span></div>}
      {!loading && !error && diagram && <div className="analysis-memo-layout">
        <div className="analysis-source-column">
          <div className="analysis-source-tabs" role="group" aria-label="분석 자료 선택">
            <button type="button" className={sourceView === 'schematic' ? 'active' : ''} onClick={() => setSourceView('schematic')}>시퀀스 회로도</button>
            <button type="button" className={sourceView === 'layout' ? 'active' : ''} onClick={() => setSourceView('layout')}>배관·배치도</button>
            <button type="button" className={sourceView === 'operation' ? 'active' : ''} onClick={() => setSourceView('operation')}>동작사항</button>
            <button type="button" className={sourceView === 'internal' ? 'active' : ''} onClick={() => setSourceView('internal')}>기구 내부결선도</button>
            <button type="button" className={sourceView === 'split' ? 'active' : ''} onClick={() => setSourceView('split')}>나란히 보기</button>
          </div>
          <div className={`analysis-source-view ${sourceView}`}>
            {(sourceView === 'schematic' || sourceView === 'split') && <CircuitDiagram key={problem.problem_id} diagram={diagram} questions={[]} selectedQuestionId={null} draft={{}} onSelect={() => undefined} onClear={() => setSelectedAnnotationId(null)} backgroundHref={problem.problem_type === 'official' ? schematicUrl(problem.problem_id) : undefined} annotationMarkers={annotationMarkers} contactTargets={contactTargets(problem.problem_id)} onContactSelect={selectContact} annotationMode={annotationMode} selectedAnnotationId={selectedAnnotationId} onCanvasAnnotate={addMarker} onAnnotationSelect={setSelectedAnnotationId} />}
            {(sourceView === 'layout' || sourceView === 'split') && <section className="layout-reference-stage" aria-label="공개문제 배관 및 기구 배치도"><header><strong>배관 및 기구 배치도</strong></header><CircuitDiagram key={`${problem.problem_id}-layout`} diagram={layoutReferenceDiagram} questions={[]} selectedQuestionId={null} draft={{}} readOnly ariaLabel={`${problem.title} 배관 및 기구 배치도`} backgroundHref={layoutReferenceUrl(problem.problem_id)} onSelect={() => undefined} onClear={() => undefined} /></section>}
            {(sourceView === 'operation' || sourceView === 'internal') && <AnalysisReferencePage problemId={problem.problem_id} kind={sourceView} />}
          </div>
        </div>
        <aside className="analysis-memo-panel">
          <div className="analysis-editor-scroll">
          <section className="analysis-annotation-editor"><strong>접점·코일 슬롯번호</strong><p>회로도의 접점을 클릭하고 양쪽 단자에 숫자·글자를 각각 3자까지 입력하세요. 가로 접점은 좌우, 세로 접점은 위아래에 표시됩니다.</p><button type="button" className={annotationMode ? 'active' : ''} onClick={() => { setSourceView('schematic'); setAnnotationMode((value) => !value) }}>{annotationMode ? '회로도에서 위치를 클릭하세요' : '＋ 다른 위치에 입력'}</button>
            {selectedMarker && <div className={`analysis-annotation-input${selectedMarker.orientation ? ' paired-slots' : ''}`}>
              <label htmlFor="analysis-slot-number">{selectedMarker.orientation === 'horizontal' ? '왼쪽 단자' : selectedMarker.orientation === 'vertical' ? '위쪽 단자' : '선택한 슬롯번호'}</label>
              <input id="analysis-slot-number" key={selectedMarker.id} autoFocus value={selectedMarker.label} maxLength={3} placeholder="예: 10, A1" onChange={(event) => updateMarker(selectedMarker.id, { label: Array.from(event.target.value).slice(0, 3).join('') })} />
              {selectedMarker.orientation && <><label htmlFor="analysis-slot-second">{selectedMarker.orientation === 'horizontal' ? '오른쪽 단자' : '아래쪽 단자'}</label><input id="analysis-slot-second" value={selectedMarker.second ?? ''} maxLength={3} placeholder="예: 4, A2" onChange={(event) => updateMarker(selectedMarker.id, { second: Array.from(event.target.value).slice(0, 3).join('') })} /><label>표시 방향<select aria-label="단자 표시 방향" value={selectedMarker.orientation} onChange={(event) => updateMarker(selectedMarker.id, { orientation: event.target.value as 'horizontal' | 'vertical' })}><option value="horizontal">가로 · 왼쪽/오른쪽</option><option value="vertical">세로 · 위쪽/아래쪽</option></select></label></>}
              <div className="annotation-position-controls" aria-label="번호 표시 위치 조정">
                <span>번호 위치</span>
                {([{ label: '왼쪽', x: -8, y: 0 }, { label: '오른쪽', x: 8, y: 0 }, { label: '위', x: 0, y: -8 }, { label: '아래', x: 0, y: 8 }]).map(direction => <button key={direction.label} type="button" aria-label={`번호 ${direction.label} 이동`} onClick={() => updateMarker(selectedMarker.id, { offsetX: (selectedMarker.offsetX ?? 0) + direction.x, offsetY: (selectedMarker.offsetY ?? 0) + direction.y })}>{direction.label}</button>)}
                <button type="button" onClick={() => updateMarker(selectedMarker.id, { offsetX: 0, offsetY: 0 })}>기본 위치</button>
              </div>
              <button type="button" onClick={() => deleteMarker(selectedMarker.id)}>표시 삭제</button>
            </div>}
            {annotationMarkers.length > 0 && <div className="analysis-annotation-list" aria-label="작성한 슬롯번호 목록">{annotationMarkers.map((marker, index) => <button type="button" key={marker.id} className={marker.id === selectedAnnotationId ? 'selected' : ''} onClick={() => { setSourceView('schematic'); setSelectedAnnotationId(marker.id) }}>{index + 1}. {marker.label || '미입력'}{marker.orientation ? ` / ${marker.second || '미입력'}` : ''}</button>)}</div>}
          </section>
          </div>
          <DeviceInternalReference key={problem.problem_id} problem={problem} deviceId={selectedDeviceId} onSelect={id => {
            if (selectedMarker) updateMarker(selectedMarker.id, { deviceId: id })
            else setReferenceDeviceId(id)
          }} />
          <SlotNumberExample />
        </aside>
      </div>}
    </section>
  }

  const updateAnswer = (questionId: string, slotId: string, pin: number) => {
    const next = { ...draft, [questionId]: { ...(draft[questionId] ?? {}), [slotId]: pin } }
    setDraft(next)
    studyDraftStorage().setItem(circuitDraftKey(problem.problem_id, problem.version), JSON.stringify(next))
    setResult(undefined)
    setNotice(undefined)
  }
  const clearSelected = () => {
    if (!selectedQuestionId) return
    const next = { ...draft }
    delete next[selectedQuestionId]
    setDraft(next)
    studyDraftStorage().setItem(circuitDraftKey(problem.problem_id, problem.version), JSON.stringify(next))
    setResult(undefined)
  }
  const submit = async () => {
    const complete = problem.socket_questions.every((question) =>
      question.answer_slots.every((slot) => draft[question.question_id]?.[slot.slot_id]),
    )
    if (problem.socket_questions.length > 0 && !complete) {
      setNotice('아직 입력하지 않은 소켓번호가 있습니다. 모든 슬롯을 입력해 주세요.')
      return
    }
    try {
      setNotice(undefined)
      const nextResult = await submitCircuitAttempt(problem.problem_id, problem.version, draft)
      setResult(nextResult)
      setProgress((value) => ({ problem_id: problem.problem_id, attempt_count: (value?.attempt_count ?? 0) + 1, last_submitted_at: new Date().toISOString(), last_overall_correct: nextResult.overall_correct, last_correct_count: nextResult.correct_count, total_count: nextResult.total_count }))
      window.dispatchEvent(new CustomEvent('electrician:progress-changed'))
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : '채점 요청에 실패했습니다.')
    }
  }

  return <section className="workspace-page circuit-workspace">
    <header className="workspace-toolbar">
      <div><span>1단계 · SVG 회로도 분석</span><h2>회로도 분석</h2></div>
      <div className="circuit-overview" role="region" aria-label="회로 데이터 요약">
        <span>장치 {problem.circuit.devices.length}</span><span>단자 {problem.circuit.terminals.length}</span>
        <span>접점 {problem.circuit.contacts.length}</span><span>코일 {problem.circuit.coils.length}</span>
      </div>
    </header>
    {loading && <div className="circuit-loading">구조화된 회로도를 불러오는 중입니다.</div>}
    {error && <div className="circuit-load-error" role="alert"><strong>회로도를 표시할 수 없습니다.</strong><span>{error}</span><button type="button" onClick={() => window.location.reload()}>다시 불러오기</button></div>}
    {!loading && !error && diagram && <div className="circuit-layout">
      <CircuitDiagram key={problem.problem_id} diagram={diagram} questions={problem.socket_questions} selectedQuestionId={selectedQuestionId} draft={draft} result={result} onSelect={(id) => { setSelectedQuestionId(id); setNotice(undefined) }} onClear={() => setSelectedQuestionId(null)} backgroundHref={problem.problem_type === 'official' && problem.status === 'draft' ? schematicUrl(problem.problem_id) : undefined} />
      <CircuitQuestionPanel problem={problem} question={selectedQuestion} sockets={sockets} draft={draft} result={result} attemptCount={progress?.attempt_count ?? 0} notice={notice} onChange={updateAnswer} onSubmit={() => void submit()} onClear={clearSelected} />
    </div>}
  </section>
}
