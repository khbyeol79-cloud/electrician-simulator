import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  applyOperationAction, createFreeCircuitSession, createFreeCircuitWorkspace, deleteFreeCircuitWorkspace,
  deleteOperationSession, getFreeCircuitDiagnostics, getFreeCircuitTemplates, getFreeCircuitWorkspace,
  getFreeCircuitWorkspaces, resetOperationSession, saveFreeCircuitWorkspace,
  type FreeCircuitDiagnostics, type FreeCircuitTemplate, type FreeCircuitWorkspace,
  type FreeCircuitWorkspaceSummary, type OperationSessionState, type WiringConnection,
} from '../api/client'
import { OperationBoard } from '../features/operation/components/OperationBoard'
import { WiringBoard } from '../features/wiring/components/WiringBoard'
import { isFreeJunction, terminalBlockBank, terminalBlockUsage } from '../features/wiring/engine/terminalCapacity'

function slug(value: string) {
  return value.trim().replace(/[^A-Za-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 64)
}

export function FreeCircuitPage() {
  const [templates, setTemplates] = useState<FreeCircuitTemplate[]>([])
  const [summaries, setSummaries] = useState<FreeCircuitWorkspaceSummary[]>([])
  const [workspace, setWorkspace] = useState<FreeCircuitWorkspace>()
  const [templateId, setTemplateId] = useState('operation_demo_001')
  const [newName, setNewName] = useState('자기유지 자유회로')
  const [newId, setNewId] = useState('self_hold_01')
  const [connections, setConnections] = useState<WiringConnection[]>([])
  const [history, setHistory] = useState<WiringConnection[][]>([])
  const [future, setFuture] = useState<WiringConnection[][]>([])
  const [mode, setMode] = useState<'graphic' | 'summary'>('graphic')
  const [selectedPin, setSelectedPin] = useState<string | null>(null)
  const [selectedWire, setSelectedWire] = useState<number | null>(null)
  const [selectedSummaryTerminal, setSelectedSummaryTerminal] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const [notice, setNotice] = useState<string>()
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [operation, setOperation] = useState<OperationSessionState>()
  const [diagnostics, setDiagnostics] = useState<FreeCircuitDiagnostics>()
  const dragStart = useRef<string | null>(null)
  const suppressClick = useRef(false)
  const sessionRef = useRef<string | undefined>(undefined)

  const reloadList = useCallback(async () => setSummaries(await getFreeCircuitWorkspaces()), [])
  useEffect(() => {
    Promise.all([getFreeCircuitTemplates(), getFreeCircuitWorkspaces()])
      .then(([nextTemplates, nextSummaries]) => { setTemplates(nextTemplates); setSummaries(nextSummaries); setError(undefined) })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : '자유회로 정보를 불러올 수 없습니다.'))
  }, [])
  useEffect(() => () => { if (sessionRef.current) void deleteOperationSession(sessionRef.current).catch(() => undefined) }, [])

  const board = workspace?.board ?? undefined
  const externalDevices = workspace?.wiring_semantics?.external_devices ?? []
  const pinByTerminal = useMemo(() => new Map(board?.items.flatMap((item) => item.pins).map((pin) => [pin.terminal_id, pin]) ?? []), [board])
  const externalByTerminal = useMemo(() => new Map(externalDevices.flatMap((device) => device.terminals.map((terminal) => [terminal.terminal_id, terminal] as const))), [externalDevices])
  const externalIds = useMemo(() => new Set(externalByTerminal.keys()), [externalByTerminal])
  const counts = useMemo(() => {
    const result = new Map<string, number>()
    connections.forEach((item) => { result.set(item.from, (result.get(item.from) ?? 0) + 1); result.set(item.to, (result.get(item.to) ?? 0) + 1) })
    return result
  }, [connections])

  const openWorkspace = async (workspaceId: string) => {
    setBusy(true)
    try {
      if (sessionRef.current) await deleteOperationSession(sessionRef.current).catch(() => undefined)
      sessionRef.current = undefined; setOperation(undefined)
      const value = await getFreeCircuitWorkspace(workspaceId)
      setWorkspace(value); setConnections(value.connections); setMode(value.editor.mode)
      setHistory([]); setFuture([]); setSelectedPin(null); setSelectedWire(null); setDiagnostics(undefined); setNotice(undefined); setError(undefined)
    } catch (reason) { setError(reason instanceof Error ? reason.message : '작업공간을 불러올 수 없습니다.') }
    finally { setBusy(false) }
  }

  const createWorkspace = async () => {
    const workspaceId = slug(newId)
    if (!workspaceId) { setNotice('작업공간 ID는 영문, 숫자, 밑줄 또는 하이픈으로 입력해 주세요.'); return }
    setBusy(true)
    try {
      const value = await createFreeCircuitWorkspace(templateId, workspaceId, newName.trim())
      await reloadList(); setWorkspace(value); setConnections([]); setMode('graphic'); setHistory([]); setFuture([]); setNotice('새 자유회로 작업공간을 만들었습니다.'); setError(undefined)
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '작업공간을 만들 수 없습니다.') }
    finally { setBusy(false) }
  }

  const commit = (next: WiringConnection[]) => {
    setHistory((items) => [...items.slice(-29), connections]); setFuture([]); setConnections(next)
    setSelectedWire(null); setSelectedSummaryTerminal(null); setNotice(undefined); setDiagnostics(undefined)
  }
  const connect = (from: string, to: string) => {
    if (from === to) { setNotice('같은 단자끼리는 연결할 수 없습니다.'); return }
    if (connections.some((item) => [item.from, item.to].sort().join('|') === [from, to].sort().join('|'))) { setNotice('이미 연결된 단자입니다.'); return }
    const fromExternal = externalIds.has(from), toExternal = externalIds.has(to)
    if (fromExternal && toExternal) { setNotice('외부 기구선끼리는 직접 연결할 수 없습니다.'); return }
    if (fromExternal || toExternal) {
      const target = pinByTerminal.get(fromExternal ? to : from)
      if (!isFreeJunction(target)) { setNotice('외부 기구선은 TB5 또는 TB6에 연결해 주세요.'); return }
    }
    for (const terminalId of [from, to]) {
      const pin = pinByTerminal.get(terminalId)
      if (isFreeJunction(pin)) {
        const bank = terminalBlockBank({ from, to }, terminalId, externalIds)
        if (terminalBlockUsage(connections, terminalId, externalIds)[bank] >= (pin?.max_connections ?? 2)) {
          setNotice(`${terminalId} ${bank === 'external' ? '외부측' : '내부측'}은 최대 ${pin?.max_connections ?? 2}가닥입니다.`); return
        }
      } else {
        const maximum = pin?.max_connections ?? externalByTerminal.get(terminalId)?.max_connections ?? 2
        if ((counts.get(terminalId) ?? 0) >= maximum) { setNotice(`${terminalId} 연결은 최대 ${maximum}가닥입니다.`); return }
      }
    }
    const external = externalByTerminal.get(from) ?? externalByTerminal.get(to)
    commit([...connections, { from, to, wire_color: external?.wire_color ?? 'yellow', pair_display_color: '#64748b' }]); setSelectedPin(null)
  }
  const pinClick = (terminalId: string) => {
    if (suppressClick.current) { suppressClick.current = false; return }
    if (!selectedPin) { setSelectedPin(terminalId); setSelectedWire(null); return }
    if (selectedPin === terminalId) { setSelectedPin(null); return }
    connect(selectedPin, terminalId)
  }
  const pinPointerUp = (terminalId: string) => {
    const from = dragStart.current; dragStart.current = null
    if (from && from !== terminalId) { suppressClick.current = true; connect(from, terminalId) }
  }
  const undo = () => { const previous = history.at(-1); if (!previous) return; setFuture((items) => [connections, ...items]); setConnections(previous); setHistory((items) => items.slice(0, -1)); setSelectedWire(null) }
  const redo = () => { const next = future[0]; if (!next) return; setHistory((items) => [...items, connections]); setConnections(next); setFuture((items) => items.slice(1)); setSelectedWire(null) }

  const save = async () => {
    if (!workspace) return
    setBusy(true)
    try {
      const value = await saveFreeCircuitWorkspace({ ...workspace, connections, editor: { ...workspace.editor, mode } })
      setWorkspace(value); await reloadList(); setNotice('자유회로를 저장했습니다.'); setError(undefined)
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '자유회로를 저장할 수 없습니다.') }
    finally { setBusy(false) }
  }
  const startOperation = async () => {
    if (!workspace) return
    setBusy(true)
    try {
      await saveFreeCircuitWorkspace({ ...workspace, connections, editor: { ...workspace.editor, mode } })
      if (sessionRef.current) await deleteOperationSession(sessionRef.current).catch(() => undefined)
      const state = await createFreeCircuitSession(workspace.workspace_id)
      sessionRef.current = state.session_id; setOperation(state); setDiagnostics(await getFreeCircuitDiagnostics(workspace.workspace_id)); setError(undefined)
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '자유회로 동작시험을 시작할 수 없습니다.') }
    finally { setBusy(false) }
  }
  const perform = async (action: Record<string, unknown>) => {
    if (!sessionRef.current) return
    try { setOperation(await applyOperationAction(sessionRef.current, action)); setError(undefined) }
    catch (reason) { setError(reason instanceof Error ? reason.message : '동작을 계산할 수 없습니다.') }
  }

  useEffect(() => {
    if (!operation?.powered || !sessionRef.current) return
    const timer = window.setInterval(() => void perform({ action: 'advance_time', milliseconds: 250 }), 250)
    return () => window.clearInterval(timer)
  // perform intentionally follows the active session id.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [operation?.powered])

  const removeWorkspace = async () => {
    if (!workspace || !window.confirm(`'${workspace.name}' 작업공간을 삭제하시겠습니까?`)) return
    setBusy(true)
    try { await deleteFreeCircuitWorkspace(workspace.workspace_id); setWorkspace(undefined); setConnections([]); setOperation(undefined); await reloadList() }
    catch (reason) { setNotice(reason instanceof Error ? reason.message : '작업공간을 삭제할 수 없습니다.') }
    finally { setBusy(false) }
  }

  if (!workspace) return <section className="workspace-page free-circuit-home">
    <header className="workspace-toolbar"><div><span>정답 없는 실제 결선 실험</span><h2>자유회로 실험</h2></div><div className="wiring-stats"><span>작업공간 {summaries.length}</span><span>공통 동작 엔진</span></div></header>
    <div className="free-home-scroll">
      <section className="free-create-card"><h3>새 실험 보드</h3><p>검증된 기구 구성이 배치된 빈 보드에서 원하는 결선을 만들고 실제 논리 동작을 확인합니다.</p>
        <label>시작 보드<select value={templateId} onChange={(event) => setTemplateId(event.target.value)}>{templates.map((item) => <option key={item.template_id} value={item.template_id}>{item.name}</option>)}</select></label>
        <small>{templates.find((item) => item.template_id === templateId)?.description}</small>
        <label>작업공간 이름<input value={newName} onChange={(event) => setNewName(event.target.value)} /></label>
        <label>작업공간 ID<input value={newId} onChange={(event) => setNewId(event.target.value)} /></label>
        <button disabled={busy || !templates.length} onClick={() => void createWorkspace()}>자유회로 만들기</button>{notice && <p className="submission-notice">{notice}</p>}
      </section>
      <section className="free-workspace-list"><h3>저장된 작업공간</h3>{summaries.length ? summaries.map((item) => <button key={item.workspace_id} disabled={busy} onClick={() => void openWorkspace(item.workspace_id)}><strong>{item.name}</strong><span>{item.workspace_id} · 전선 {item.connection_count}개</span><small>{item.updated_at ? new Date(item.updated_at).toLocaleString('ko-KR') : '저장 전'}</small></button>) : <p>저장된 자유회로가 없습니다.</p>}</section>
      {error && <div className="circuit-load-error compact"><strong>자유회로를 준비할 수 없습니다.</strong><span>{error}</span></div>}
    </div>
  </section>

  if (operation && board) return <section className="workspace-page free-circuit-operation">
    <header className="workspace-toolbar"><div><span>자유회로 · 실제 결선 계산</span><h2>{workspace.name}</h2></div><div className="wiring-stats"><span>전원 {operation.power_state.toUpperCase()}</span><span>정답 채점 없음</span></div></header>
    <div className="operation-layout">
      <div className="wiring-stage operation-stage"><div className="wiring-toolbar"><button onClick={() => setZoom((value) => Math.min(1.35, value + .1))}>＋</button><button onClick={() => setZoom((value) => Math.max(.7, value - .1))}>－</button><button onClick={() => setZoom(1)}>화면 맞춤</button><span>현재 저장된 실제 결선 · 읽기 전용</span></div><OperationBoard board={board} connections={connections} placements={workspace.device_layout?.fixed_placements ?? []} zoom={zoom} energizedSocketIds={new Set(workspace.circuit.coils.filter((coil) => operation.coils[coil.coil_id]).map((coil) => coil.owner_device_id))} /></div>
      <aside className="wiring-panel operation-panel"><section className="operation-ready-card"><span className="panel-kicker">자유회로 동작시험</span><h3>공통 논리 엔진 실행 중</h3><p>정답과 비교하지 않고 현재 결선의 Net과 접점 상태를 계산합니다.</p></section>
        <section className="operation-controls"><button className={`power-switch ${operation.powered ? 'on' : ''}`} onClick={() => void perform({ action: 'set_power', value: !operation.powered })}>전원 {operation.powered ? 'OFF' : 'ON'}</button><div className="control-grid">{Object.entries(operation.controls).map(([id, state]) => state.mode === 'maintained' ? <button key={id} className={state.active ? 'control-button active' : 'control-button'} onClick={() => void perform({ action: 'toggle_control', control_id: id })}><b>{id}</b><span>{state.active ? '작동' : '복귀'}</span></button> : <button key={id} className={state.active ? 'control-button active' : 'control-button'} onPointerDown={() => void perform({ action: 'press_control', control_id: id })} onPointerUp={() => void perform({ action: 'release_control', control_id: id })} onPointerLeave={() => state.active && void perform({ action: 'release_control', control_id: id })}><b>{id}</b><span>{state.contact_type} · 누르는 동안</span></button>)}</div></section>
        {Object.entries(operation.protections).map(([id, state]) => <section key={id} className="protection-controls"><strong>{state.label}</strong><button disabled={state.status !== 'normal'} onClick={() => void perform({ action: 'trigger_fault', target_id: id, fault_type: 'overload' })}>과부하 발생</button><button disabled={state.status === 'normal'} onClick={() => void perform({ action: 'reset_fault', target_id: id })}>복귀</button></section>)}
        <section className="operation-status-panel"><strong>기구 상태</strong><div className="status-chip-grid">{Object.entries(operation.coils).map(([id, on]) => <div key={id} className={`status-chip ${on ? 'on' : ''}`}><span>{id}</span><b>{on ? 'ON' : 'OFF'}</b></div>)}{Object.entries(operation.timers).map(([id, state]) => <div key={id} className={`status-chip timer ${state.status}`}><span>{id}</span><b>{state.status}</b></div>)}{Object.entries(operation.indicators).map(([id, state]) => <div key={id} className={`status-chip lamp ${state}`}><span>{id}</span><b>{state}</b></div>)}{Object.entries(operation.motors).map(([id, state]) => <div key={id} className={`status-chip motor ${state}`}><span>{id}</span><b>{state}</b></div>)}</div></section>
        <section className={operation.faults.length ? 'operation-faults active' : 'operation-faults'}><strong>회로 진단</strong>{operation.faults.map((item) => <p key={item.code}>{item.message}</p>)}{diagnostics?.diagnostics.map((item) => <p key={item.code}>{item.message}</p>)}{!operation.faults.length && !diagnostics?.diagnostics.length && <p>현재 확인된 이상이 없습니다.</p>}</section>
        <button className="secondary-action submit-circuit" onClick={async () => { if (sessionRef.current) await deleteOperationSession(sessionRef.current).catch(() => undefined); sessionRef.current = undefined; setOperation(undefined) }}>결선 편집으로 돌아가기</button><button className="secondary-action submit-circuit" onClick={async () => { if (sessionRef.current) setOperation(await resetOperationSession(sessionRef.current)) }}>시험 초기화</button>
      </aside>
    </div>
  </section>

  if (!board) return <section className="workspace-page free-circuit-home">
    <header className="workspace-toolbar"><div><span>이전 자유회로 데이터</span><h2>{workspace.name}</h2></div></header>
    <div className="workspace-canvas"><div className="placeholder-card"><div className="placeholder-icon">!</div><h3>표시할 보드 배치가 없습니다.</h3><p>이 작업공간은 0.9.x API로 저장되어 동작 정의는 유지되지만 편집용 보드가 없습니다. 기존 데이터는 삭제하지 않았습니다.</p><button className="submit-circuit" onClick={() => { setWorkspace(undefined); setConnections([]) }}>작업공간 목록으로 돌아가기</button></div></div>
  </section>

  return <section className="workspace-page free-circuit-editor">
    <header className="workspace-toolbar"><div><span>자유회로 · 정답 채점 없음</span><h2>{workspace.name}</h2></div><div className="wiring-stats"><span>전선 {connections.length}</span><span>{workspace.editor.template_id ?? '기존 작업공간'}</span></div></header>
    <div className="wiring-layout"><div className={`wiring-stage${externalDevices.length ? ' has-external-wiring' : ''}`}><div className="wiring-toolbar"><button className={mode === 'graphic' ? 'active' : ''} onClick={() => setMode('graphic')}>그래픽 모드</button><button className={mode === 'summary' ? 'active' : ''} onClick={() => setMode('summary')}>요약 모드</button><span className="toolbar-separator"/><button onClick={() => setZoom((value) => Math.min(1.35, value + .1))}>＋</button><button onClick={() => setZoom((value) => Math.max(.7, value - .1))}>－</button><button onClick={() => setZoom(1)}>화면 맞춤</button><span className="toolbar-separator"/><button disabled={!history.length} onClick={undo}>실행 취소</button><button disabled={!future.length} onClick={redo}>다시 실행</button><button disabled={selectedWire === null} onClick={() => selectedWire !== null && commit(connections.filter((_, index) => index !== selectedWire))}>선택 전선 삭제</button><button className="danger" onClick={() => window.confirm('모든 전선을 초기화하시겠습니까?') && commit([])}>전체 초기화</button></div>
      {externalDevices.length > 0 && <section className="external-wiring-tray"><div className="external-wiring-heading"><strong>외부 기구선</strong><span>외부선은 TB5 위쪽 또는 TB6 아래쪽 물리 포트로 연결됩니다.</span><small>같은 TB 번호: 외부측 2가닥 + 내부측 2가닥</small></div><div className="external-device-list">{externalDevices.map((device) => <article key={device.device_id} className="external-device-card"><strong>{device.label}</strong><div>{device.terminals.map((terminal) => { const linked = connections.findIndex((item) => item.from === terminal.terminal_id || item.to === terminal.terminal_id); return <button key={terminal.terminal_id} draggable={linked < 0} className={selectedPin === terminal.terminal_id ? 'selected' : ''} onClick={() => linked >= 0 ? setSelectedWire(linked) : pinClick(terminal.terminal_id)} onDragStart={(event) => event.dataTransfer.setData('application/x-electrician-terminal', terminal.terminal_id)}><span className={`external-wire-swatch ${terminal.wire_color}`}/>{terminal.terminal_id}<small>{linked >= 0 ? '연결됨' : '미연결'}</small></button>})}</div></article>)}</div></section>}
      <WiringBoard board={board} connections={connections} externalDevices={externalDevices} mode={mode} selectedPin={selectedPin} selectedWire={selectedWire} selectedSummaryTerminal={selectedSummaryTerminal} zoom={zoom} onPinClick={pinClick} onPinPointerDown={(id) => { dragStart.current = id }} onPinPointerUp={pinPointerUp} onExternalDrop={(externalId, targetId) => connect(externalId, targetId)} onWireSelect={(index) => { setSelectedWire(index); setSelectedPin(null) }} onSummarySelect={(id, indices) => { setSelectedSummaryTerminal(id); setSelectedWire(indices[0] ?? null) }} onClearSelection={() => { setSelectedPin(null); setSelectedWire(null); setSelectedSummaryTerminal(null) }}/></div>
      <aside className="wiring-panel"><section><span className="panel-kicker">작업공간</span><h3>{workspace.name}</h3><p>기구 배치는 시작 보드에서 고정되며 전선은 자유롭게 연결할 수 있습니다.</p><button className="secondary-action submit-circuit" disabled={busy} onClick={() => { setWorkspace(undefined); setConnections([]) }}>다른 작업공간</button></section><section><span className="panel-kicker">현재 선택</span><h3>{selectedWire === null ? selectedPin ? `시작 단자 ${selectedPin}` : '단자를 선택하세요' : `${connections[selectedWire]?.from} → ${connections[selectedWire]?.to}`}</h3>{selectedWire !== null && <label className="wire-color-select">전선 색상<select value={connections[selectedWire].wire_color} onChange={(event) => commit(connections.map((item, index) => index === selectedWire ? { ...item, wire_color: event.target.value as WiringConnection['wire_color'] } : item))}><option value="yellow">노란색</option><option value="brown">갈색</option><option value="black">검은색</option><option value="gray">회색</option></select></label>}</section><section className="free-mode-notice"><strong>정답 데이터 없음</strong><p>자유회로는 정답·오답으로 채점하지 않고 현재 결선으로 실제 논리 상태를 계산합니다.</p>{notice && <div className="submission-notice">{notice}</div>}{error && <div className="submission-notice">{error}</div>}<button className="submit-circuit" disabled={busy} onClick={() => void save()}>저장</button><button className="submit-circuit operation-start" disabled={busy} onClick={() => void startOperation()}>현재 결선으로 동작시험</button></section><section><span className="panel-kicker">기구 구성</span><p>0.10.0은 검증된 시작 보드 3종의 고정 슬롯을 사용합니다. 개별 기구 임의 배치는 다음 단계에서 확장합니다.</p><div className="free-device-tags">{workspace.circuit.devices.map((device) => <span key={device.device_id}>{device.label}</span>)}</div></section><button className="danger-zone-button" disabled={busy} onClick={() => void removeWorkspace()}>이 작업공간 삭제</button></aside></div>
  </section>
}
