import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  deleteWiringDraft, getBoard, getDiagram, getWiringDraft, getWiringProgress, saveWiringDraft, submitWiringAttempt,
  type BoardDefinition, type PublicProblemDetail, type SchematicDiagram, type WiringAttemptResult, type WiringConnection, type WiringProgress,
} from '../api/client'
import { CircuitDiagram } from '../components/circuit/CircuitDiagram'
import { restoreCircuitDraft, type CircuitDraft } from '../features/circuit/circuitDraft'
import { WiringBoard } from '../features/wiring/components/WiringBoard'
import { isFreeJunction, terminalBlockBank, terminalBlockUsage } from '../features/wiring/engine/terminalCapacity'
import { PlaceholderPage } from './PlaceholderPage'

export function WiringPage({ problem }: { problem?: PublicProblemDetail }) {
  const navigate = useNavigate()
  const [board, setBoard] = useState<BoardDefinition>()
  const [referenceDiagram, setReferenceDiagram] = useState<SchematicDiagram>()
  const [circuitDraft, setCircuitDraft] = useState<CircuitDraft>({})
  const [connections, setConnections] = useState<WiringConnection[]>([])
  const [history, setHistory] = useState<WiringConnection[][]>([])
  const [future, setFuture] = useState<WiringConnection[][]>([])
  const [mode, setMode] = useState<'graphic' | 'summary'>('graphic')
  const [selectedPin, setSelectedPin] = useState<string | null>(null)
  const [selectedWire, setSelectedWire] = useState<number | null>(null)
  const [selectedSummaryTerminal, setSelectedSummaryTerminal] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const [progress, setProgress] = useState<WiringProgress>()
  const [result, setResult] = useState<WiringAttemptResult>()
  const [notice, setNotice] = useState<string>()
  const [error, setError] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [ready, setReady] = useState(false)
  const dragStart = useRef<string | null>(null)
  const suppressClick = useRef(false)
  const resultClassificationLabels: Record<NonNullable<WiringAttemptResult['result_classification']>, string> = {
    correct: '정답',
    functionally_equivalent: '기능적으로 동등한 정답',
    operates_but_incorrect: '동작하지만 오답',
    incorrect: '오답 / 오동작',
    ungradable: '채점 준비 중',
  }

  const selectedConnection = selectedWire === null ? undefined : connections[selectedWire]
  const selectedSummaryConnections = useMemo(() => selectedSummaryTerminal === null ? [] : connections.flatMap((connection, connectionIndex) => {
    if (connection.from === selectedSummaryTerminal) return [{ connectionIndex, other: connection.to }]
    if (connection.to === selectedSummaryTerminal) return [{ connectionIndex, other: connection.from }]
    return []
  }), [connections, selectedSummaryTerminal])
  const connectionKeys = useMemo(() => new Set(connections.map((item) => [item.from, item.to].sort().join('|'))), [connections])
  const pinByTerminal = useMemo(() => new Map(board?.items.flatMap((item) => item.pins).map((pin) => [pin.terminal_id, pin]) ?? []), [board])
  const externalDevices = problem?.wiring_semantics?.external_devices ?? []
  const externalByTerminal = useMemo(() => new Map(externalDevices.flatMap((device) => device.terminals.map((terminal) => [terminal.terminal_id, terminal] as const))), [externalDevices])
  const externalTerminalIds = useMemo(() => new Set(externalByTerminal.keys()), [externalByTerminal])
  const terminalConnectionCounts = useMemo(() => {
    const counts = new Map<string, number>()
    connections.forEach((connection) => {
      counts.set(connection.from, (counts.get(connection.from) ?? 0) + 1)
      counts.set(connection.to, (counts.get(connection.to) ?? 0) + 1)
    })
    return counts
  }, [connections])
  const analyzedQuestionCount = useMemo(() => problem?.socket_questions.filter((question) =>
    question.answer_slots.every((slot) => Boolean(circuitDraft[question.question_id]?.[slot.slot_id])),
  ).length ?? 0, [circuitDraft, problem])

  useEffect(() => {
    if (!problem) return
    const controller = new AbortController()
    setLoading(true); setReady(false); setError(undefined); setNotice(undefined); setResult(undefined)
    setSelectedPin(null); setSelectedWire(null); setSelectedSummaryTerminal(null); setHistory([]); setFuture([])
    setCircuitDraft(restoreCircuitDraft(problem.problem_id, problem.version))
    Promise.all([getBoard(problem.problem_id, controller.signal), getWiringDraft(problem.problem_id, controller.signal), getWiringProgress(problem.problem_id, controller.signal), getDiagram(problem.problem_id, controller.signal)])
      .then(([nextBoard, draft, nextProgress, nextDiagram]) => {
        setBoard(nextBoard); setConnections(draft?.problem_version === problem.version ? draft.connections : [])
        setMode(draft?.problem_version === problem.version ? draft.mode : 'graphic'); setProgress(nextProgress); setReferenceDiagram(nextDiagram); setReady(true)
      })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '제어함 배치를 불러올 수 없습니다.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [problem])

  useEffect(() => {
    if (!problem || !ready) return
    const timer = window.setTimeout(() => {
      saveWiringDraft(problem.problem_id, problem.version, mode, connections).catch((reason: unknown) => setNotice(reason instanceof Error ? reason.message : '임시 결선을 저장할 수 없습니다.'))
    }, 450)
    return () => window.clearTimeout(timer)
  }, [connections, mode, problem, ready])

  const commit = (next: WiringConnection[]) => {
    setHistory((values) => [...values.slice(-29), connections]); setFuture([]); setConnections(next)
    setResult(undefined); setNotice(undefined); setSelectedWire(null); setSelectedSummaryTerminal(null)
  }
  const connect = (from: string, to: string) => {
    if (from === to) { setNotice('같은 단자끼리는 연결할 수 없습니다.'); return }
    const fromExternal = externalByTerminal.has(from), toExternal = externalByTerminal.has(to)
    if (fromExternal || toExternal) {
      const target = pinByTerminal.get(fromExternal ? to : from)
      if (fromExternal && toExternal) { setNotice('외부 기구선끼리는 직접 연결할 수 없습니다.'); return }
      if (!target || (target.terminal_role !== 'free_junction' && !target.terminal_id.startsWith('TB5-') && !target.terminal_id.startsWith('TB6-'))) { setNotice('외부 기구선은 TB5 또는 TB6 단자에 연결해 주세요.'); return }
    }
    const key = [from, to].sort().join('|')
    if (connectionKeys.has(key)) { setNotice('이미 연결된 단자입니다.'); return }
    for (const terminalId of [from, to]) {
      const pin = pinByTerminal.get(terminalId)
      if (isFreeJunction(pin)) {
        const bank = terminalBlockBank({ from, to }, terminalId, externalTerminalIds)
        const usage = terminalBlockUsage(connections, terminalId, externalTerminalIds)
        const maximum = pin?.max_connections ?? 2
        if (usage[bank] >= maximum) {
          const side = bank === 'external' ? '외부측' : '내부측'
          setNotice(`${terminalId} 단자의 ${side}에는 전선을 최대 ${maximum}개까지 연결할 수 있습니다.`)
          return
        }
        continue
      }
      const maximum = pin?.max_connections ?? externalByTerminal.get(terminalId)?.max_connections ?? 2
      if ((terminalConnectionCounts.get(terminalId) ?? 0) >= maximum) {
        setNotice(`${terminalId} 단자에는 전선을 최대 ${maximum}개까지 연결할 수 있습니다.`)
        return
      }
    }
    const external = externalByTerminal.get(from) ?? externalByTerminal.get(to)
    commit([...connections, { from, to, wire_color: external?.wire_color ?? 'yellow', pair_display_color: '#64748b' }])
    setSelectedPin(null)
  }
  const pinClick = (terminalId: string) => {
    if (suppressClick.current) { suppressClick.current = false; return }
    if (!selectedPin) { setSelectedPin(terminalId); setSelectedWire(null); setSelectedSummaryTerminal(null); setNotice(undefined); return }
    if (selectedPin === terminalId) { setSelectedPin(null); return }
    connect(selectedPin, terminalId)
  }
  const pinPointerUp = (terminalId: string) => {
    const from = dragStart.current; dragStart.current = null
    if (from && from !== terminalId) { suppressClick.current = true; connect(from, terminalId) }
  }
  const removeSelected = () => {
    if (selectedWire === null) return
    commit(connections.filter((_, index) => index !== selectedWire)); setSelectedWire(null)
  }
  const undo = () => {
    const previous = history.at(-1); if (!previous) return
    setFuture((values) => [connections, ...values]); setConnections(previous); setHistory((values) => values.slice(0, -1)); setSelectedWire(null); setSelectedSummaryTerminal(null)
  }
  const redo = () => {
    const next = future[0]; if (!next) return
    setHistory((values) => [...values, connections]); setConnections(next); setFuture((values) => values.slice(1)); setSelectedWire(null); setSelectedSummaryTerminal(null)
  }
  const reset = async () => {
    if (!window.confirm('현재 문제의 모든 결선을 초기화하시겠습니까?')) return
    commit([]); setSelectedPin(null); await deleteWiringDraft(problem!.problem_id).catch(() => undefined)
  }
  const changeWireColor = (wireColor: WiringConnection['wire_color']) => {
    if (selectedWire === null) return
    const targetIndex = selectedWire
    setHistory((values) => [...values.slice(-29), connections]); setFuture([])
    setConnections(connections.map((item, index) => index === targetIndex ? { ...item, wire_color: wireColor } : item))
    setResult(undefined)
  }
  const submit = async () => {
    try {
      await saveWiringDraft(problem!.problem_id, problem!.version, mode, connections)
      const next = await submitWiringAttempt(problem!.problem_id, problem!.version, connections)
      setResult(next); setNotice(undefined)
      setProgress((value) => ({ problem_id: problem!.problem_id, attempt_count: (value?.attempt_count ?? 0) + 1, last_submitted_at: new Date().toISOString(), last_overall_correct: next.overall_correct, last_gradable: next.gradable, last_correct_count: next.correct_count, required_count: next.required_count }))
      window.dispatchEvent(new CustomEvent('electrician:progress-changed'))
      if (next.overall_correct) navigate('/operation')
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '결선 제출에 실패했습니다.') }
  }

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if ((event.key === 'Delete' || event.key === 'Backspace') && selectedWire !== null) { event.preventDefault(); removeSelected() }
      if (event.key === 'Escape') { setSelectedPin(null); setSelectedWire(null); setSelectedSummaryTerminal(null) }
    }
    window.addEventListener('keydown', keydown)
    return () => window.removeEventListener('keydown', keydown)
  })

  useEffect(() => {
    const resetFromHeader = () => {
      setConnections([]); setHistory([]); setFuture([]); setSelectedPin(null); setSelectedWire(null); setSelectedSummaryTerminal(null); setResult(undefined); setNotice(undefined)
      if (problem) void deleteWiringDraft(problem.problem_id).catch(() => undefined)
    }
    window.addEventListener('electrician:reset-wiring', resetFromHeader)
    return () => window.removeEventListener('electrician:reset-wiring', resetFromHeader)
  }, [problem])

  useEffect(() => {
    const resetCircuitReference = () => setCircuitDraft({})
    window.addEventListener('electrician:reset-circuit', resetCircuitReference)
    return () => window.removeEventListener('electrician:reset-circuit', resetCircuitReference)
  }, [])

  if (!problem) return <PlaceholderPage stage="2단계" title="제어함 결선" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="⎍" />

  return <section className="workspace-page wiring-workspace">
    <header className="workspace-toolbar wiring-header"><div><span>2단계 · 실제 제어함 결선</span><h2>제어함 결선</h2></div><div className="wiring-stats"><span>연결 {connections.length}</span><span>제출 {progress?.attempt_count ?? 0}회</span></div></header>
    {loading && <div className="circuit-loading">문제별 제어함 배치를 불러오는 중입니다.</div>}
    {error && <div className="circuit-load-error" role="alert"><strong>제어함을 표시할 수 없습니다.</strong><span>{error}</span></div>}
    {!loading && !error && board && <div className="wiring-layout">
      <div className={`wiring-stage${externalDevices.length > 0 ? ' has-external-wiring' : ''}`}>
        <div className="wiring-toolbar" aria-label="결선 편집 도구">
          <button className={mode === 'graphic' ? 'active' : ''} onClick={() => { setMode('graphic'); setSelectedSummaryTerminal(null) }}>그래픽 모드</button><button className={mode === 'summary' ? 'active' : ''} onClick={() => setMode('summary')}>요약 모드</button>
          <span className="toolbar-separator" /><button aria-label="확대" onClick={() => setZoom((value) => Math.min(1.35, value + .1))}>＋</button><button aria-label="축소" onClick={() => setZoom((value) => Math.max(.7, value - .1))}>－</button><button onClick={() => setZoom(1)}>화면 맞춤</button>
          <span className="toolbar-separator" /><button disabled={!history.length} onClick={undo}>실행 취소</button><button disabled={!future.length} onClick={redo}>다시 실행</button><button disabled={selectedWire === null} onClick={removeSelected}>선택 전선 삭제</button><button className="danger" onClick={() => void reset()}>전체 초기화</button>
        </div>
        {externalDevices.length > 0 && <section className="external-wiring-tray" aria-label="외부 기구선"><div className="external-wiring-heading"><strong>외부 기구선</strong><span>전선 끝을 선택하거나 TB 단자로 드래그하세요.</span><small>TB 한 번호: 외부측 2가닥 + 내부측 2가닥</small></div><div className="external-device-list">{externalDevices.map((device) => <article key={device.device_id} className="external-device-card"><strong>{device.label}</strong><div>{device.terminals.map((terminal) => { const linked = connections.flatMap((item, index) => item.from === terminal.terminal_id ? [{ id: item.to, index }] : item.to === terminal.terminal_id ? [{ id: item.from, index }] : [])[0]; const count = terminalConnectionCounts.get(terminal.terminal_id) ?? 0; return <button key={terminal.terminal_id} type="button" draggable={!linked} className={selectedPin === terminal.terminal_id ? 'selected' : ''} aria-label={`${terminal.terminal_id} 외부 기구선, ${count} / ${terminal.max_connections} 연결`} onClick={() => { if (linked) { setSelectedWire(linked.index); setSelectedPin(null) } else pinClick(terminal.terminal_id) }} onDragStart={(event) => { event.dataTransfer.setData('application/x-electrician-terminal', terminal.terminal_id); event.dataTransfer.effectAllowed = 'link' }}><span className={`external-wire-swatch ${terminal.wire_color}`} />{terminal.terminal_id}<small>{linked ? `→ ${linked.id}` : '미연결'} · {count}/{terminal.max_connections}</small></button> })}</div></article>)}</div></section>}
        <WiringBoard board={board} connections={connections} externalDevices={externalDevices} mode={mode} selectedPin={selectedPin} selectedWire={selectedWire} selectedSummaryTerminal={selectedSummaryTerminal} zoom={zoom} onPinClick={pinClick} onPinPointerDown={(id) => { dragStart.current = id }} onPinPointerUp={pinPointerUp} onExternalDrop={(externalId, targetId) => connect(externalId, targetId)} onWireSelect={(index) => { setSelectedWire(index); setSelectedPin(null); setSelectedSummaryTerminal(null) }} onSummarySelect={(terminalId, connectionIndices) => { setSelectedSummaryTerminal(terminalId); setSelectedWire(connectionIndices[0] ?? null); setSelectedPin(null) }} onClearSelection={() => { setSelectedPin(null); setSelectedWire(null); setSelectedSummaryTerminal(null) }} />
      </div>
      <aside className="wiring-panel">
        <section><span className="panel-kicker">현재 작업</span><h3>{selectedSummaryTerminal ? `${selectedSummaryTerminal} · ${selectedSummaryConnections.length}개 연결` : selectedConnection ? `${selectedConnection.from} → ${selectedConnection.to}` : selectedPin ? `시작 단자 ${selectedPin}` : '단자를 선택하세요'}</h3><p>시작 단자와 종료 단자를 차례로 클릭하거나 드래그하여 연결합니다. 새 전선은 노란색으로 생성됩니다.</p>{selectedSummaryTerminal && mode === 'summary' && <div className="summary-connection-list" aria-label={`${selectedSummaryTerminal} 상대 단자 목록`}>{selectedSummaryConnections.map((item, index) => <button key={item.connectionIndex} type="button" className={selectedWire === item.connectionIndex ? 'selected' : ''} onClick={() => setSelectedWire(item.connectionIndex)}><span>{index + 1}번째 연결</span><strong>{item.other}</strong></button>)}</div>}{selectedConnection && !selectedSummaryTerminal && mode === 'summary' && <dl className="summary-connection-detail"><div><dt>연결 단자 1</dt><dd>{selectedConnection.from}</dd></div><div><dt>연결 단자 2</dt><dd>{selectedConnection.to}</dd></div></dl>}{selectedConnection && <label className="wire-color-select">물리 전선 색상<select value={selectedConnection.wire_color} onChange={(event) => changeWireColor(event.target.value as WiringConnection['wire_color'])}><option value="yellow">노란색</option><option value="brown">갈색</option><option value="black">검은색</option><option value="gray">회색</option></select></label>}</section>
        <section className="virtual-warning"><strong>가상 학습 데이터</strong><p>이 문제는 배선 기능 확인용이며 실제 시험 정답이 아닙니다.</p></section>
        <section><span className="panel-kicker">결선 상태</span><dl><div><dt>표시 모드</dt><dd>{mode === 'graphic' ? '그래픽' : '요약'}</dd></div><div><dt>연결 수</dt><dd>{connections.length}</dd></div><div><dt>경로 방식</dt><dd>직교·빈 통로 우선</dd></div></dl>{notice && <div className="submission-notice" role="alert">{notice}</div>}{result && <div className={`wiring-result ${result.overall_correct ? 'correct' : result.gradable ? 'wrong' : 'warning'}`}><b>{resultClassificationLabels[result.result_classification ?? (result.gradable ? 'incorrect' : 'ungradable')]}</b><strong>{result.message}</strong><span>정상 네트워크 {result.correct_net_count ?? result.correct_count}/{result.required_net_count ?? result.required_count}</span>{result.gradable && <span>누락 {result.missing_net_count ?? result.missing_connections.length} · 합쳐짐 {result.merged_net_count ?? 0} · 불필요 {result.extra_connection_count ?? result.extra_connections.length}</span>}{result.used_alternative_tb_numbers && <span>다른 TB 번호 사용 · 전기적 동등성 인정</span>}{(result.warnings ?? []).map((warning) => <span key={warning}>{warning}</span>)}</div>}{result?.gradable === false && <button className="preview-operation" type="button" onClick={() => navigate('/operation')}>동작시험 화면 미리보기</button>}<button className="submit-circuit" onClick={() => void submit()}>결선 제출</button></section>
        <section><span className="panel-kicker">경로 규칙</span><p>같은 수평 통로의 단자는 최단거리로 직접 연결하고, 서로 다른 수평 통로로 이동할 때만 좌우 외곽 통로를 사용합니다.</p></section>
        <section className="circuit-reference-panel" aria-label="회로도 분석 참고">
          <div className="circuit-reference-header"><div><span className="panel-kicker">1단계 참고</span><h3>회로도 분석 결과</h3></div><strong>{analyzedQuestionCount} / {problem.socket_questions.length} 입력</strong></div>
          {referenceDiagram && <CircuitDiagram key={`${problem.problem_id}-reference`} diagram={referenceDiagram} questions={problem.socket_questions} selectedQuestionId={null} draft={circuitDraft} readOnly compact ariaLabel="회로도 분석 참고창" onSelect={() => undefined} onClear={() => undefined} />}
          {analyzedQuestionCount === 0 && <p className="circuit-reference-empty">1단계에서 입력한 소켓번호가 아직 없습니다.</p>}
          <p className="circuit-reference-note">입력한 번호를 읽기 전용으로 표시합니다. 버튼과 마우스 휠로 빠르게 확대·축소하고 회로도를 드래그해 이동할 수 있습니다.</p>
        </section>
      </aside>
    </div>}
  </section>
}
