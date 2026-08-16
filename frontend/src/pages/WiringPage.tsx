import { useEffect, useMemo, useRef, useState } from 'react'
import {
  deleteWiringDraft, getBoard, getWiringDraft, getWiringProgress, saveWiringDraft, submitWiringAttempt,
  type BoardDefinition, type PublicProblemDetail, type WiringAttemptResult, type WiringConnection, type WiringProgress,
} from '../api/client'
import { WiringBoard } from '../features/wiring/components/WiringBoard'
import { PlaceholderPage } from './PlaceholderPage'

function inferWireColor(from: string, to: string): WiringConnection['wire_color'] {
  const value = `${from}|${to}`
  if (/(L1|T1)/.test(value)) return 'brown'
  if (/(L2|T2)/.test(value)) return 'black'
  if (/(L3|T3)/.test(value)) return 'gray'
  return 'yellow'
}

export function WiringPage({ problem }: { problem?: PublicProblemDetail }) {
  const [board, setBoard] = useState<BoardDefinition>()
  const [connections, setConnections] = useState<WiringConnection[]>([])
  const [history, setHistory] = useState<WiringConnection[][]>([])
  const [future, setFuture] = useState<WiringConnection[][]>([])
  const [mode, setMode] = useState<'graphic' | 'summary'>('graphic')
  const [selectedPin, setSelectedPin] = useState<string | null>(null)
  const [selectedWire, setSelectedWire] = useState<number | null>(null)
  const [zoom, setZoom] = useState(1)
  const [progress, setProgress] = useState<WiringProgress>()
  const [result, setResult] = useState<WiringAttemptResult>()
  const [notice, setNotice] = useState<string>()
  const [error, setError] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [ready, setReady] = useState(false)
  const dragStart = useRef<string | null>(null)
  const suppressClick = useRef(false)

  const selectedConnection = selectedWire === null ? undefined : connections[selectedWire]
  const connectionKeys = useMemo(() => new Set(connections.map((item) => [item.from, item.to].sort().join('|'))), [connections])

  useEffect(() => {
    if (!problem) return
    const controller = new AbortController()
    setLoading(true); setReady(false); setError(undefined); setNotice(undefined); setResult(undefined)
    setSelectedPin(null); setSelectedWire(null); setHistory([]); setFuture([])
    Promise.all([getBoard(problem.problem_id, controller.signal), getWiringDraft(problem.problem_id, controller.signal), getWiringProgress(problem.problem_id, controller.signal)])
      .then(([nextBoard, draft, nextProgress]) => {
        setBoard(nextBoard); setConnections(draft?.problem_version === problem.version ? draft.connections : [])
        setMode(draft?.problem_version === problem.version ? draft.mode : 'graphic'); setProgress(nextProgress); setReady(true)
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
    setResult(undefined); setNotice(undefined); setSelectedWire(null)
  }
  const connect = (from: string, to: string) => {
    if (from === to) { setNotice('같은 단자끼리는 연결할 수 없습니다.'); return }
    const key = [from, to].sort().join('|')
    if (connectionKeys.has(key)) { setNotice('이미 연결된 단자입니다.'); return }
    commit([...connections, { from, to, wire_color: inferWireColor(from, to), pair_display_color: '#64748b' }])
    setSelectedPin(null)
  }
  const pinClick = (terminalId: string) => {
    if (suppressClick.current) { suppressClick.current = false; return }
    if (!selectedPin) { setSelectedPin(terminalId); setSelectedWire(null); setNotice(undefined); return }
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
    setFuture((values) => [connections, ...values]); setConnections(previous); setHistory((values) => values.slice(0, -1)); setSelectedWire(null)
  }
  const redo = () => {
    const next = future[0]; if (!next) return
    setHistory((values) => [...values, connections]); setConnections(next); setFuture((values) => values.slice(1)); setSelectedWire(null)
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
      const next = await submitWiringAttempt(problem!.problem_id, problem!.version, connections)
      setResult(next); setNotice(undefined)
      setProgress((value) => ({ problem_id: problem!.problem_id, attempt_count: (value?.attempt_count ?? 0) + 1, last_submitted_at: new Date().toISOString(), last_overall_correct: next.overall_correct, last_correct_count: next.correct_count, required_count: next.required_count }))
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '결선 제출에 실패했습니다.') }
  }

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if ((event.key === 'Delete' || event.key === 'Backspace') && selectedWire !== null) { event.preventDefault(); removeSelected() }
      if (event.key === 'Escape') { setSelectedPin(null); setSelectedWire(null) }
    }
    window.addEventListener('keydown', keydown)
    return () => window.removeEventListener('keydown', keydown)
  })

  useEffect(() => {
    const resetFromHeader = () => {
      setConnections([]); setHistory([]); setFuture([]); setSelectedPin(null); setSelectedWire(null); setResult(undefined); setNotice(undefined)
      if (problem) void deleteWiringDraft(problem.problem_id).catch(() => undefined)
    }
    window.addEventListener('electrician:reset-wiring', resetFromHeader)
    return () => window.removeEventListener('electrician:reset-wiring', resetFromHeader)
  }, [problem])

  if (!problem) return <PlaceholderPage stage="2단계" title="제어함 결선" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="⎍" />

  return <section className="workspace-page wiring-workspace">
    <header className="workspace-toolbar wiring-header"><div><span>2단계 · 실제 제어함 결선</span><h2>제어함 결선</h2></div><div className="wiring-stats"><span>연결 {connections.length}</span><span>제출 {progress?.attempt_count ?? 0}회</span></div></header>
    {loading && <div className="circuit-loading">문제별 제어함 배치를 불러오는 중입니다.</div>}
    {error && <div className="circuit-load-error" role="alert"><strong>제어함을 표시할 수 없습니다.</strong><span>{error}</span></div>}
    {!loading && !error && board && <div className="wiring-layout">
      <div className="wiring-stage">
        <div className="wiring-toolbar" aria-label="결선 편집 도구">
          <button className={mode === 'graphic' ? 'active' : ''} onClick={() => setMode('graphic')}>그래픽 모드</button><button className={mode === 'summary' ? 'active' : ''} onClick={() => setMode('summary')}>요약 모드</button>
          <span className="toolbar-separator" /><button aria-label="확대" onClick={() => setZoom((value) => Math.min(1.35, value + .1))}>＋</button><button aria-label="축소" onClick={() => setZoom((value) => Math.max(.7, value - .1))}>－</button><button onClick={() => setZoom(1)}>화면 맞춤</button>
          <span className="toolbar-separator" /><button disabled={!history.length} onClick={undo}>실행 취소</button><button disabled={!future.length} onClick={redo}>다시 실행</button><button disabled={selectedWire === null} onClick={removeSelected}>선택 전선 삭제</button><button className="danger" onClick={() => void reset()}>전체 초기화</button>
        </div>
        <WiringBoard board={board} connections={connections} mode={mode} selectedPin={selectedPin} selectedWire={selectedWire} zoom={zoom} onPinClick={pinClick} onPinPointerDown={(id) => { dragStart.current = id }} onPinPointerUp={pinPointerUp} onWireSelect={(index) => { setSelectedWire(index); setSelectedPin(null) }} onClearSelection={() => { setSelectedPin(null); setSelectedWire(null) }} />
      </div>
      <aside className="wiring-panel">
        <section><span className="panel-kicker">현재 작업</span><h3>{selectedConnection ? `${selectedConnection.from} → ${selectedConnection.to}` : selectedPin ? `시작 단자 ${selectedPin}` : '단자를 선택하세요'}</h3><p>시작 단자와 종료 단자를 차례로 클릭하거나 드래그하여 연결합니다.</p>{selectedConnection && <label className="wire-color-select">물리 전선 색상<select value={selectedConnection.wire_color} onChange={(event) => changeWireColor(event.target.value as WiringConnection['wire_color'])}><option value="yellow">노란색</option><option value="brown">갈색</option><option value="black">검은색</option><option value="gray">회색</option></select></label>}</section>
        <section className="virtual-warning"><strong>가상 학습 데이터</strong><p>이 문제는 배선 기능 확인용이며 실제 시험 정답이 아닙니다.</p></section>
        <section><span className="panel-kicker">결선 상태</span><dl><div><dt>표시 모드</dt><dd>{mode === 'graphic' ? '그래픽' : '요약'}</dd></div><div><dt>연결 수</dt><dd>{connections.length}</dd></div><div><dt>경로 방식</dt><dd>직교·빈 통로 우선</dd></div></dl>{notice && <div className="submission-notice" role="alert">{notice}</div>}{result && <div className={`wiring-result ${result.overall_correct ? 'correct' : result.gradable ? 'wrong' : 'warning'}`}><strong>{result.message}</strong><span>정상 {result.correct_count}/{result.required_count}</span>{result.gradable && <span>누락 {result.missing_connections.length} · 추가 {result.extra_connections.length} · 금지 {result.forbidden_connections.length}</span>}</div>}<button className="submit-circuit" onClick={() => void submit()}>결선 제출</button></section>
        <section><span className="panel-kicker">경로 규칙</span><p>위·아래에서 거의 마주 보는 단자만 가운데로 직접 연결하며, 가로 이동이 큰 교차 행 연결은 좌우 외곽 통로로 우회합니다.</p></section>
      </aside>
    </div>}
  </section>
}
