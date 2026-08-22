import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  addFreeCircuitDevice, applyOperationAction, createFreeCircuitSession, createFreeCircuitWorkspace,
  deleteFreeCircuitDevice, deleteFreeCircuitWorkspace,
  deleteOperationSession, getFreeCircuitDiagnostics, getFreeCircuitWorkspace,
  getFreeCircuitPalette, getFreeCircuitTemplates, getFreeCircuitWorkspaces, moveFreeCircuitDevice, resetOperationSession, saveFreeCircuitWorkspace,
  type FreeCircuitDiagnostics, type FreeCircuitMountingSlot, type FreeCircuitPalette, type FreeCircuitWorkspace,
  type FreeCircuitWorkspaceSummary, type OperationSessionState, type WiringConnection,
} from '../api/client'
import { OperationBoard } from '../features/operation/components/OperationBoard'
import { isTextEditingTarget, useFreeCircuitAutosave } from '../features/free-circuit/useFreeCircuitAutosave'
import { WiringBoard } from '../features/wiring/components/WiringBoard'
import { isFreeJunction, terminalBlockBank, terminalBlockUsage } from '../features/wiring/engine/terminalCapacity'

export function FreeCircuitPage() {
  const [summaries, setSummaries] = useState<FreeCircuitWorkspaceSummary[]>([])
  const [workspace, setWorkspace] = useState<FreeCircuitWorkspace>()
  const [newName, setNewName] = useState('새 자유회로')
  const [newTemplateId, setNewTemplateId] = useState('basic_board_001')
  const [templates, setTemplates] = useState<{ template_id: string; name: string; description: string }[]>([])
  const [palette, setPalette] = useState<FreeCircuitPalette>()
  const [pendingPaletteId, setPendingPaletteId] = useState<string | null>(null)
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null)
  const [movingDevice, setMovingDevice] = useState(false)
  const [connections, setConnections] = useState<WiringConnection[]>([])
  type EditSnapshot = { workspace: FreeCircuitWorkspace; connections: WiringConnection[]; mode: 'graphic' | 'summary' }
  const [history, setHistory] = useState<EditSnapshot[]>([])
  const [future, setFuture] = useState<EditSnapshot[]>([])
  const [mode, setMode] = useState<'graphic' | 'summary'>('graphic')
  const [selectedPin, setSelectedPin] = useState<string | null>(null)
  const [selectedWire, setSelectedWire] = useState<number | null>(null)
  const [selectedSummaryTerminal, setSelectedSummaryTerminal] = useState<string | null>(null)
  const [notice, setNotice] = useState<string>()
  const [error, setError] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [operation, setOperation] = useState<OperationSessionState>()
  const [diagnostics, setDiagnostics] = useState<FreeCircuitDiagnostics>()
  const dragStart = useRef<string | null>(null)
  const suppressClick = useRef(false)
  const sessionRef = useRef<string | undefined>(undefined)

  const handleAutosaveSaved = useCallback((saved: FreeCircuitWorkspace) => {
    setWorkspace((current) => current?.workspace_id === saved.workspace_id
      ? { ...current, updated_at: saved.updated_at }
      : current)
    setError(undefined)
  }, [])
  const handleAutosaveError = useCallback((message: string) => setError(`자동 저장 실패: ${message}`), [])
  const autosave = useFreeCircuitAutosave({
    workspace, connections, mode,
    onSaved: handleAutosaveSaved,
    onError: handleAutosaveError,
  })

  const reloadList = useCallback(async () => setSummaries(await getFreeCircuitWorkspaces()), [])
  useEffect(() => {
    Promise.all([getFreeCircuitWorkspaces(), getFreeCircuitTemplates(), getFreeCircuitPalette()])
      .then(([nextSummaries, nextTemplates, nextPalette]) => { setSummaries(nextSummaries); setTemplates(nextTemplates); setPalette(nextPalette); setError(undefined) })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : '자유회로 정보를 불러올 수 없습니다.'))
  }, [])
  useEffect(() => () => { if (sessionRef.current) void deleteOperationSession(sessionRef.current).catch(() => undefined) }, [])

  const board = workspace?.board ?? undefined
  const externalDevices = workspace?.wiring_semantics?.external_devices ?? []
  const selectedDevice = workspace?.assembly?.installed_devices.find((item) => item.instance_id === selectedDeviceId)
  const selectedDevicePalette = palette?.items.find((item) => item.palette_id === selectedDevice?.palette_id)
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
      setHistory([]); setFuture([]); setSelectedPin(null); setSelectedWire(null); setSelectedDeviceId(null); setPendingPaletteId(null); setDiagnostics(undefined); setNotice(undefined); setError(undefined)
    } catch (reason) { setError(reason instanceof Error ? reason.message : '작업공간을 불러올 수 없습니다.') }
    finally { setBusy(false) }
  }

  const createWorkspace = async () => {
    const name = newName.trim()
    if (!name) { setNotice('작업공간 이름을 입력해 주세요.'); return }
    setBusy(true)
    try {
      const value = await createFreeCircuitWorkspace(name, newTemplateId)
      await reloadList(); setWorkspace(value); setConnections([]); setMode('graphic'); setHistory([]); setFuture([]); setNotice('새 자유회로 작업공간을 만들었습니다.'); setError(undefined)
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '작업공간을 만들 수 없습니다.') }
    finally { setBusy(false) }
  }

  const currentSnapshot = (): EditSnapshot | undefined => workspace
    ? { workspace, connections, mode }
    : undefined
  const rememberSnapshot = (snapshot: EditSnapshot | undefined) => {
    if (!snapshot) return
    setHistory((items) => [...items.slice(-29), snapshot]); setFuture([])
  }

  const commit = (next: WiringConnection[]) => {
    rememberSnapshot(currentSnapshot()); setConnections(next)
    setSelectedWire(null); setSelectedSummaryTerminal(null); setNotice(undefined); setDiagnostics(undefined)
    autosave.schedule({ connections: next })
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
  const restoreSnapshot = async (snapshot: EditSnapshot) => {
    autosave.discardPending()
    setWorkspace(snapshot.workspace); setConnections(snapshot.connections); setMode(snapshot.mode)
    const saved = await saveFreeCircuitWorkspace({
      ...snapshot.workspace, connections: snapshot.connections,
      editor: { ...snapshot.workspace.editor, mode: snapshot.mode },
    })
    setWorkspace(saved); setConnections(saved.connections); setMode(saved.editor.mode)
  }
  const undo = async () => {
    const previous = history.at(-1), current = currentSnapshot(); if (!previous || !current) return
    setFuture((items) => [current, ...items]); setHistory((items) => items.slice(0, -1)); setSelectedWire(null); setSelectedDeviceId(null)
    try { await restoreSnapshot(previous) } catch (reason) { setNotice(reason instanceof Error ? reason.message : '실행 취소 저장에 실패했습니다.') }
  }
  const redo = async () => {
    const next = future[0], current = currentSnapshot(); if (!next || !current) return
    setHistory((items) => [...items, current]); setFuture((items) => items.slice(1)); setSelectedWire(null); setSelectedDeviceId(null)
    try { await restoreSnapshot(next) } catch (reason) { setNotice(reason instanceof Error ? reason.message : '다시 실행 저장에 실패했습니다.') }
  }
  const removeSelected = () => {
    if (selectedWire === null || !connections[selectedWire]) return
    commit(connections.filter((_, index) => index !== selectedWire))
  }

  const installAt = async (slot: FreeCircuitMountingSlot, explicitPaletteId?: string, forceAdd = false) => {
    if (!workspace) return
    const before = currentSnapshot()
    if (!forceAdd && movingDevice && selectedDeviceId) {
      setBusy(true)
      try {
        await autosave.flushPending()
        const saved = await moveFreeCircuitDevice(workspace.workspace_id, selectedDeviceId, { zone: slot.zone, row: slot.row, column: slot.column })
        rememberSnapshot(before); setWorkspace(saved); setConnections(saved.connections); setMovingDevice(false); setNotice(`${selectedDeviceId} 기구를 이동하고 자동 저장했습니다.`)
      } catch (reason) { setNotice(reason instanceof Error ? reason.message : '기구를 이동할 수 없습니다.') }
      finally { setBusy(false) }
      return
    }
    const paletteId = explicitPaletteId ?? pendingPaletteId
    if (!paletteId) return
    setBusy(true)
    try {
      await autosave.flushPending()
      const saved = await addFreeCircuitDevice(workspace.workspace_id, paletteId, { zone: slot.zone, row: slot.row, column: slot.column })
      rememberSnapshot(before); setWorkspace(saved); setConnections(saved.connections); setPendingPaletteId(null)
      setSelectedDeviceId(saved.assembly?.installed_devices.at(-1)?.instance_id ?? null)
      setNotice('기구를 설치하고 자동 저장했습니다.')
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '기구를 설치할 수 없습니다.') }
    finally { setBusy(false) }
  }

  const choosePalette = async (paletteId: string) => {
    if (!workspace || !palette) return
    const item = palette.items.find((value) => value.palette_id === paletteId)
    if (!item?.enabled) return
    if (item.mounting_kind === 'internal') {
      setPendingPaletteId(paletteId); setMovingDevice(false); setSelectedDeviceId(null)
      setNotice(`${item.name}: 보드의 빈 장착칸을 선택하세요.`)
      return
    }
    const used = new Set(workspace.assembly?.installed_devices.map((device) => `${device.placement.zone}-${device.placement.column}`))
    const slot = palette.slots.find((value) => value.zone === item.default_zone && !used.has(`${value.zone}-${value.column}`))
    if (!slot) { setNotice('사용 가능한 외부 기구 위치가 없습니다.'); return }
    setMovingDevice(false); setSelectedDeviceId(null)
    await installAt(slot, paletteId, true)
  }

  const removeSelectedDevice = async () => {
    if (!workspace || !selectedDeviceId) return
    const before = currentSnapshot()
    setBusy(true)
    try {
      await autosave.flushPending()
      let saved: FreeCircuitWorkspace
      try { saved = await deleteFreeCircuitDevice(workspace.workspace_id, selectedDeviceId) }
      catch (reason) {
        if (!window.confirm(`${reason instanceof Error ? reason.message : '연결된 전선이 있습니다.'}\n기구와 연결 전선을 함께 삭제하시겠습니까?`)) return
        saved = await deleteFreeCircuitDevice(workspace.workspace_id, selectedDeviceId, true)
      }
      rememberSnapshot(before); setWorkspace(saved); setConnections(saved.connections); setSelectedDeviceId(null); setNotice('기구와 관련 데이터를 삭제하고 자동 저장했습니다.')
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '기구를 삭제할 수 없습니다.') }
    finally { setBusy(false) }
  }

  const updateSelectedDeviceProperties = async (properties: Record<string, string | number | boolean>) => {
    if (!workspace || !selectedDeviceId) return
    const before = currentSnapshot()
    setBusy(true)
    try {
      await autosave.flushPending()
      const saved = await moveFreeCircuitDevice(workspace.workspace_id, selectedDeviceId, undefined, properties)
      rememberSnapshot(before); setWorkspace(saved); setConnections(saved.connections); setNotice('기구 설정을 변경하고 자동 저장했습니다.')
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '기구 설정을 변경할 수 없습니다.') }
    finally { setBusy(false) }
  }
  const changeMode = (nextMode: 'graphic' | 'summary') => {
    if (nextMode === mode) return
    setMode(nextMode)
    setSelectedWire(null); setSelectedSummaryTerminal(null)
    autosave.schedule({ mode: nextMode })
  }

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if (event.key !== 'Delete' || isTextEditingTarget(event.target)) return
      if (selectedWire === null && !selectedDeviceId) return
      event.preventDefault()
      if (selectedWire !== null) removeSelected()
      else void removeSelectedDevice()
    }
    window.addEventListener('keydown', keydown)
    return () => window.removeEventListener('keydown', keydown)
  })

  const save = async () => {
    if (!workspace) return
    setBusy(true)
    try {
      await autosave.saveNow()
      await reloadList(); setNotice('자유회로를 저장했습니다.'); setError(undefined)
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '자유회로를 저장할 수 없습니다.') }
    finally { setBusy(false) }
  }
  const startOperation = async () => {
    if (!workspace) return
    setBusy(true)
    try {
      await autosave.flushPending()
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
    try { await autosave.flushPending(); autosave.discardPending(); await deleteFreeCircuitWorkspace(workspace.workspace_id); setWorkspace(undefined); setConnections([]); setOperation(undefined); await reloadList() }
    catch (reason) { setNotice(reason instanceof Error ? reason.message : '작업공간을 삭제할 수 없습니다.') }
    finally { setBusy(false) }
  }

  const templateLabel = (templateId: string | null | undefined) => ({
    basic_board_001: '기본보드',
    empty_board_001: '빈보드',
    operation_demo_001: '기존 자기유지 보드',
    forward_reverse_interlock_demo_001: '기존 정역회전 보드',
    eocr_sequence_demo_001: '기존 EOCR 보드',
  }[templateId ?? ''] ?? '기존 형식 작업공간')

  if (!workspace) return <section className="workspace-page free-circuit-home">
    <header className="workspace-toolbar"><div><span>정답 없는 실제 결선 실험</span><h2>자유회로 실험</h2></div><div className="wiring-stats"><span>작업공간 {summaries.length}</span><span>공통 동작 엔진</span></div></header>
    <div className="free-home-scroll">
      <section className="free-create-card"><h3>새 실험 보드</h3><p>기본보드 또는 기구를 직접 설치하는 빈보드에서 실제 결선 동작을 확인합니다.</p>
        <label>작업공간 이름<input value={newName} onChange={(event) => setNewName(event.target.value)} /></label>
        <div className="free-template-cards">{templates.map((template) => <button type="button" key={template.template_id} className={newTemplateId === template.template_id ? 'selected' : ''} onClick={() => setNewTemplateId(template.template_id)}><strong>{template.name}</strong><span>{template.description}</span></button>)}</div>
        <small>작업공간 ID는 서버가 자동으로 생성합니다.</small>
        <button disabled={busy} onClick={() => void createWorkspace()}>{newTemplateId === 'empty_board_001' ? '빈보드로 만들기' : '기본보드로 만들기'}</button>{notice && <p className="submission-notice">{notice}</p>}
      </section>
      <section className="free-workspace-list"><h3>저장된 작업공간</h3>{summaries.length ? summaries.map((item) => <button key={item.workspace_id} disabled={busy} onClick={() => void openWorkspace(item.workspace_id)}><strong>{item.name}</strong><span>전선 {item.connection_count}개 · {templateLabel(item.template_id)}</span><small>{item.updated_at ? new Date(item.updated_at).toLocaleString('ko-KR') : '저장 전'}</small></button>) : <p>저장된 자유회로가 없습니다.</p>}</section>
      {error && <div className="circuit-load-error compact"><strong>자유회로를 준비할 수 없습니다.</strong><span>{error}</span></div>}
    </div>
  </section>

  if (operation && board) return <section className="workspace-page free-circuit-operation">
    <header className="workspace-toolbar"><div><span>자유회로 · 실제 결선 계산</span><h2>{workspace.name}</h2></div><div className="wiring-stats"><span>전원 {operation.power_state.toUpperCase()}</span><span>정답 채점 없음</span></div></header>
    <div className="operation-layout">
      <div className="wiring-stage operation-stage"><div className="wiring-toolbar"><span>현재 저장된 실제 결선 · 읽기 전용 · 화면 자동 맞춤</span></div><OperationBoard board={board} connections={connections} placements={workspace.device_layout?.fixed_placements ?? []} zoom={1} energizedSocketIds={new Set(workspace.circuit.coils.filter((coil) => operation.coils[coil.coil_id]).map((coil) => coil.owner_device_id))} /></div>
      <aside className="wiring-panel operation-panel"><section className="operation-ready-card"><span className="panel-kicker">자유회로 동작시험</span><h3>{operation.simulation_mode === 'actual_wiring' ? '실제 결선 모드 실행 중' : '기존 호환 모드 실행 중'}</h3><p>정답과 비교하지 않고 현재 결선의 Net과 접점 상태를 계산합니다.</p>{operation.catalog_composed && <span>공통 기구 카탈로그 적용</span>}</section>
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
    <header className="workspace-toolbar"><div><span>자유회로 · 정답 채점 없음</span><h2>{workspace.name}</h2></div><div className="wiring-stats"><span>전선 {connections.length}</span><span>{templateLabel(workspace.editor.template_id)}</span><span>{workspace.operation.simulation_mode === 'actual_wiring' ? '실제 결선 모드' : '기존 호환 모드'}</span></div></header>
    <div className="wiring-layout"><div className={`wiring-stage${externalDevices.length ? ' has-external-wiring' : ''}`}><div className="wiring-toolbar"><button className={mode === 'graphic' ? 'active' : ''} onClick={() => changeMode('graphic')}>그래픽 모드</button><button className={mode === 'summary' ? 'active' : ''} onClick={() => changeMode('summary')}>요약 모드</button><span className="toolbar-separator"/><button disabled={!history.length} onClick={() => void undo()}>실행 취소</button><button disabled={!future.length} onClick={() => void redo()}>다시 실행</button><button disabled={selectedWire === null} onClick={removeSelected}>선택 전선 삭제</button><button className="danger" onClick={() => window.confirm('모든 전선을 초기화하시겠습니까?') && commit([])}>전체 초기화</button><span className="board-auto-fit-label">화면 자동 맞춤</span></div>
      {externalDevices.length > 0 && <section className="external-wiring-tray"><div className="external-wiring-heading"><strong>외부 기구선</strong><span>외부선은 TB5 위쪽 또는 TB6 아래쪽 물리 포트로 연결됩니다.</span><small>같은 TB 번호: 외부측 2가닥 + 내부측 2가닥</small></div><div className="external-device-list">{externalDevices.map((device) => <article key={device.device_id} className="external-device-card"><strong>{device.label}</strong><div>{device.terminals.map((terminal) => { const linked = connections.findIndex((item) => item.from === terminal.terminal_id || item.to === terminal.terminal_id); return <button key={terminal.terminal_id} draggable={linked < 0} className={selectedPin === terminal.terminal_id ? 'selected' : ''} onClick={() => linked >= 0 ? setSelectedWire(linked) : pinClick(terminal.terminal_id)} onDragStart={(event) => event.dataTransfer.setData('application/x-electrician-terminal', terminal.terminal_id)}><span className={`external-wire-swatch ${terminal.wire_color}`}/>{terminal.terminal_id}<small>{linked >= 0 ? '연결됨' : '미연결'}</small></button>})}</div></article>)}</div></section>}
      <WiringBoard board={board} connections={connections} externalDevices={externalDevices} mode={mode} selectedPin={selectedPin} selectedWire={selectedWire} selectedSummaryTerminal={selectedSummaryTerminal} zoom={1} mountingSlots={workspace.assembly?.mode === 'editable' ? palette?.slots : undefined} placementMode={Boolean(pendingPaletteId || movingDevice)} selectedDeviceId={selectedDeviceId} onMountingSlotClick={(slot) => void installAt(slot)} onDeviceSelect={(id) => { setSelectedDeviceId(id); setSelectedWire(null); setPendingPaletteId(null) }} onPinClick={pinClick} onPinPointerDown={(id) => { dragStart.current = id }} onPinPointerUp={pinPointerUp} onExternalDrop={(externalId, targetId) => connect(externalId, targetId)} onWireSelect={(index) => { setSelectedWire(index); setSelectedDeviceId(null); setSelectedPin(null) }} onSummarySelect={(id, indices) => { setSelectedSummaryTerminal(id); setSelectedWire(indices[0] ?? null) }} onClearSelection={() => { setSelectedPin(null); setSelectedWire(null); setSelectedDeviceId(null); setSelectedSummaryTerminal(null) }}/></div>
      <aside className="wiring-panel"><section><span className="panel-kicker">작업공간</span><h3>{workspace.name}</h3><p>{workspace.assembly?.mode === 'editable' ? '빈 장착칸에 기구를 설치하고 자유롭게 결선합니다.' : '기본보드의 고정 기구를 자유롭게 결선합니다.'}</p><button className="secondary-action submit-circuit" disabled={busy} onClick={async () => { try { await autosave.flushPending(); setWorkspace(undefined); setConnections([]) } catch { setNotice('자동 저장에 실패해 작업공간을 닫지 않았습니다. 다시 시도해 주세요.') } }}>다른 작업공간</button></section>
        <section><span className="panel-kicker">현재 선택</span><h3>{selectedDeviceId ? `기구 ${selectedDeviceId}` : selectedWire === null ? selectedPin ? `시작 단자 ${selectedPin}` : '단자 또는 기구를 선택하세요' : `${connections[selectedWire]?.from} → ${connections[selectedWire]?.to}`}</h3>{selectedWire !== null && <label className="wire-color-select">전선 색상<select value={connections[selectedWire].wire_color} onChange={(event) => commit(connections.map((item, index) => index === selectedWire ? { ...item, wire_color: event.target.value as WiringConnection['wire_color'] } : item))}><option value="yellow">노란색</option><option value="brown">갈색</option><option value="black">검은색</option><option value="gray">회색</option></select></label>}{selectedDevice?.palette_id === 'timer_8p' && <label className="wire-color-select">지연시간(ms)<input type="number" min="1" max="3600000" defaultValue={Number(selectedDevice.properties.delay_ms ?? 1000)} onBlur={(event) => void updateSelectedDeviceProperties({ ...selectedDevice.properties, delay_ms: Number(event.target.value) })} /></label>}{selectedDeviceId && workspace.assembly?.mode === 'editable' && <div className="free-device-actions"><button onClick={() => { setMovingDevice(true); setPendingPaletteId(null); setNotice(selectedDevicePalette?.mounting_kind === 'external' ? '이동할 외부 위치를 선택하세요.' : '이동할 빈 장착칸을 선택하세요.') }}>이동</button><button className="danger" onClick={() => void removeSelectedDevice()}>기구 삭제</button></div>}{movingDevice && selectedDevicePalette?.mounting_kind === 'external' && <div className="free-external-slots"><strong>외부 위치</strong>{palette?.slots.filter((slot) => slot.zone.startsWith('external')).map((slot) => <button key={slot.slot_id} disabled={workspace.assembly?.installed_devices.some((item) => item.instance_id !== selectedDeviceId && item.placement.zone === slot.zone && item.placement.column === slot.column)} onClick={() => void installAt(slot)}>{slot.zone === 'external_top' ? '상단' : '하단'} {slot.column + 1}</button>)}</div>}</section>
        {workspace.assembly?.mode === 'editable' && <section className="free-palette"><span className="panel-kicker">기구 팔레트</span><p>내부 기구는 추가 후 빈 칸을 선택합니다. 외부 기구는 빈 외부 위치에 자동 배치됩니다.</p>{['internal', 'external'].map((kind) => <div key={kind}><strong>{kind === 'internal' ? '내부 기구' : '외부 기구'}</strong>{palette?.items.filter((item) => item.mounting_kind === kind).map((item) => { const count = workspace.assembly?.installed_devices.filter((device) => device.palette_id === item.palette_id).length ?? 0; return <button key={item.palette_id} disabled={busy || !item.enabled} className={pendingPaletteId === item.palette_id ? 'selected' : ''} title={item.disabled_reason ?? undefined} onClick={() => void choosePalette(item.palette_id)}><span>{item.name}</span><small>{item.socket_type_id ?? '외부'} · {item.definition_status === 'unverified' ? '교육용·미검증' : '검토됨'} · {count}개</small></button> })}</div>)}</section>}
        <section className="free-mode-notice"><strong>정답 데이터 없음</strong><p>자유회로는 정답·오답으로 채점하지 않고 현재 결선으로 실제 논리 상태를 계산합니다.</p><div className={`autosave-status ${autosave.status}`} role="status">{{ idle: '자동 저장 준비', pending: '저장 대기 중…', saving: '저장 중…', saved: '자동 저장됨', error: '저장 실패 · 다시 시도' }[autosave.status]}</div>{notice && <div className="submission-notice">{notice}</div>}{error && <div className="submission-notice">{error}</div>}<button className="submit-circuit" disabled={busy || autosave.status === 'saving'} onClick={() => void save()}>저장</button><button className="submit-circuit operation-start" disabled={busy} onClick={() => void startOperation()}>현재 결선으로 동작시험</button></section><section><span className="panel-kicker">설치된 기구</span><div className="free-device-tags">{workspace.circuit.devices.map((device) => <button type="button" className={selectedDeviceId === device.device_id ? 'selected' : ''} key={device.device_id} onClick={() => { setSelectedDeviceId(device.device_id); setSelectedWire(null); setPendingPaletteId(null) }}>{device.label}</button>)}</div></section><button className="danger-zone-button" disabled={busy} onClick={() => void removeWorkspace()}>이 작업공간 삭제</button></aside></div>
  </section>
}
