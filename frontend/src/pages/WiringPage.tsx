import { isProtectiveEarth, workspaceTime } from '../features/wiring/engine/workspaceDisplay'
import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { WorkspaceDialog } from '../components/WorkspaceDialog'
import { useNavigate } from 'react-router-dom'
import {
  deletePracticeWiringDraft, clonePracticeWiringSnapshot, createPracticeWiringSnapshot, createPracticeWiringWorkspace, deleteWiringDraft,
  exportPracticeWiring, getBoard, getDiagram, getPracticeWiringDraft, getPracticeWiringSnapshots,
  getPracticeWiringWorkspaces, getWiringDraft, getWiringProgress, importPracticeWiring, savePracticeWiringDraft,
  saveWiringDraft, submitWiringAttempt, getCircuitAnalysisDraft, schematicUrl, layoutReferenceUrl, type CircuitAnalysisDraft,
  type BoardDefinition, type PracticeWiringExport, type PracticeWiringSnapshot, type PracticeWiringWorkspace,
  type PublicProblemDetail, type SchematicDiagram, type StructuralWarning, type WiringAttemptResult,
  type WiringConnection, type WiringProgress,
} from '../api/client'
import { CircuitDiagram } from '../components/circuit/CircuitDiagram'
import { ContactTypeBadge, contactTypeDescription } from '../components/ContactTypeBadge'
import { restoreCircuitDraft, type CircuitDraft } from '../features/circuit/circuitDraft'
import { WiringBoard } from '../features/wiring/components/WiringBoard'
import { isFreeJunction, terminalBlockBank, terminalBlockUsage } from '../features/wiring/engine/terminalCapacity'
import { PlaceholderPage } from './PlaceholderPage'
import { layoutReferenceDiagram, parseAnnotations } from '../features/circuit/analysisAnnotations'

export function WiringPage({ problem }: { problem?: PublicProblemDetail }) {
  const navigate = useNavigate()
  const [workspaceOpen, setWorkspaceOpen] = useState(false)
  const [confirmWorkspaceDelete, setConfirmWorkspaceDelete] = useState(false)
  const workspaceMenuHost = document.getElementById('workspace-menu-slot')
  const practiceMode = Boolean(problem?.capabilities.wiring_editable && !problem.capabilities.wiring_gradable)
  const unavailable = Boolean(problem && !problem.capabilities.wiring_editable)
  const [board, setBoard] = useState<BoardDefinition>()
  const [referenceDiagram, setReferenceDiagram] = useState<SchematicDiagram>()
  const [circuitDraft, setCircuitDraft] = useState<CircuitDraft>({})
  const [analysisDraft, setAnalysisDraft] = useState<CircuitAnalysisDraft | null>(null)
  const [referenceView, setReferenceView] = useState<'schematic' | 'layout'>('schematic')

  useEffect(() => {
    if (!problem || !practiceMode) return
    const controller = new AbortController()
    setAnalysisDraft(null)
    getCircuitAnalysisDraft(problem.problem_id, controller.signal).then(setAnalysisDraft).catch(() => {
      if (!controller.signal.aborted) setNotice('분석 내용을 불러오지 못했습니다. 새로고침해 주세요.')
    })
    return () => controller.abort()
  }, [problem, practiceMode])
  const [connections, setConnections] = useState<WiringConnection[]>([])
  const [history, setHistory] = useState<WiringConnection[][]>([])
  const [future, setFuture] = useState<WiringConnection[][]>([])
  const [mode, setMode] = useState<'graphic' | 'summary'>('graphic')
  const [selectedPin, setSelectedPin] = useState<string | null>(null)
  const [selectedWire, setSelectedWire] = useState<number | null>(null)
  const [selectedSummaryTerminal, setSelectedSummaryTerminal] = useState<string | null>(null)
  const [progress, setProgress] = useState<WiringProgress>()
  const [result, setResult] = useState<WiringAttemptResult>()
  const [notice, setNotice] = useState<string>()
  const [error, setError] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [ready, setReady] = useState(false)
  const [workspaceId, setWorkspaceId] = useState('main')
  const [workspaceName, setWorkspaceName] = useState('기본 작업공간')
  const [workspaces, setWorkspaces] = useState<PracticeWiringWorkspace[]>([])
  const [snapshots, setSnapshots] = useState<PracticeWiringSnapshot[]>([])
  const [structuralWarnings, setStructuralWarnings] = useState<StructuralWarning[]>([])
  const [saveState, setSaveState] = useState<'changed' | 'waiting' | 'saving' | 'saved' | 'failed'>('saved')
  const [exporting, setExporting] = useState(false)
  const [lastSavedAt, setLastSavedAt] = useState<string>()
  const deletingWorkspace = useRef(false)
  const saveSequence = useRef(0)
  const saveQueue = useRef<Promise<void>>(Promise.resolve())
  const mounted = useRef(true)
  const importInput = useRef<HTMLInputElement>(null)
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
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  useEffect(() => {
    if (!problem || unavailable) return
    const controller = new AbortController()
    setLoading(true); setReady(false); setError(undefined); setNotice(undefined); setResult(undefined)
    setSelectedPin(null); setSelectedWire(null); setSelectedSummaryTerminal(null); setHistory([]); setFuture([])
    setCircuitDraft(restoreCircuitDraft(problem.problem_id, problem.version))
    const loadDraft = async () => {
      if (!practiceMode) return getWiringDraft(problem.problem_id, controller.signal)
      const available = await getPracticeWiringWorkspaces(problem.problem_id, controller.signal)
      const remembered = window.localStorage.getItem(`electrician.qnetWorkspace.${problem.problem_id}`)
      const chosen = available.find((item) => item.workspace_id === remembered)?.workspace_id ?? available[0]?.workspace_id ?? 'main'
      setWorkspaces(available); setWorkspaceId(chosen)
      const draft = await getPracticeWiringDraft(problem.problem_id, chosen, controller.signal)
      setWorkspaceName(draft?.workspace_name ?? '기본 작업공간')
      setStructuralWarnings(draft?.structural_warnings ?? [])
      setLastSavedAt(draft?.updated_at ?? undefined)
      if (draft) setSnapshots(await getPracticeWiringSnapshots(problem.problem_id, chosen, controller.signal))
      else setSnapshots([])
      return draft
    }
    Promise.all([getBoard(problem.problem_id, controller.signal), loadDraft(), getWiringProgress(problem.problem_id, controller.signal), getDiagram(problem.problem_id, controller.signal)])
      .then(([nextBoard, draft, nextProgress, nextDiagram]) => {
        setBoard(nextBoard); setConnections(draft?.problem_version === problem.version ? draft.connections : [])
        setMode(draft?.problem_version === problem.version ? draft.mode : 'graphic'); setProgress(nextProgress); setReferenceDiagram(nextDiagram); setSaveState('saved'); setReady(true)
      })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '제어함 배치를 불러올 수 없습니다.') })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [practiceMode, problem, unavailable])

  useEffect(() => {
    if (!problem || unavailable || !ready) return
    setSaveState('waiting')
    const sequence = ++saveSequence.current
    const timer = window.setTimeout(() => {
      const save = practiceMode ? savePracticeWiringDraft : saveWiringDraft
      saveQueue.current = saveQueue.current.catch(() => undefined).then(async () => {
        if (deletingWorkspace.current) return
        if (mounted.current && sequence === saveSequence.current) setSaveState('saving')
        try {
          const draft = practiceMode
            ? await savePracticeWiringDraft(problem.problem_id, problem.version, mode, connections, workspaceId, workspaceName)
            : await save(problem.problem_id, problem.version, mode, connections)
          if (!mounted.current || sequence !== saveSequence.current) return
          setSaveState('saved'); setLastSavedAt(draft.updated_at ?? new Date().toISOString())
          if ('structural_warnings' in draft) setStructuralWarnings((draft as { structural_warnings: StructuralWarning[] }).structural_warnings)
        } catch (reason) {
          if (!mounted.current || sequence !== saveSequence.current) return
          setSaveState('failed'); setNotice(reason instanceof Error ? reason.message : '임시 결선을 저장할 수 없습니다.')
          throw reason
        }
      })
    }, 650)
    return () => window.clearTimeout(timer)
  }, [connections, mode, practiceMode, problem, ready, unavailable, workspaceId, workspaceName])

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
    commit([]); setSelectedPin(null)
    if (practiceMode) await savePracticeWiringDraft(problem!.problem_id, problem!.version, mode, [], workspaceId, workspaceName).catch(() => undefined)
    else await deleteWiringDraft(problem!.problem_id).catch(() => undefined)
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

  const openPracticeOperation = async () => {
    try {
      await savePracticeWiringDraft(problem!.problem_id, problem!.version, mode, connections, workspaceId, workspaceName)
      navigate(`/operation?workspace=${encodeURIComponent(workspaceId)}`)
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '연습 결선을 저장할 수 없습니다.') }
  }

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if (workspaceOpen || (event.target instanceof HTMLElement && event.target.closest('input, textarea, select'))) return
      if ((event.key === 'Delete' || event.key === 'Backspace') && selectedWire !== null) { event.preventDefault(); removeSelected() }
      if (event.key === 'Escape') { setSelectedPin(null); setSelectedWire(null); setSelectedSummaryTerminal(null) }
    }
    window.addEventListener('keydown', keydown)
    return () => window.removeEventListener('keydown', keydown)
  })

  useEffect(() => {
    const resetFromHeader = () => {
      setConnections([]); setHistory([]); setFuture([]); setSelectedPin(null); setSelectedWire(null); setSelectedSummaryTerminal(null); setResult(undefined); setNotice(undefined)
      if (problem) void (practiceMode ? savePracticeWiringDraft(problem.problem_id, problem.version, mode, [], workspaceId, workspaceName) : deleteWiringDraft(problem.problem_id)).catch(() => undefined)
    }
    window.addEventListener('electrician:reset-wiring', resetFromHeader)
    return () => window.removeEventListener('electrician:reset-wiring', resetFromHeader)
  }, [mode, practiceMode, problem, workspaceId, workspaceName])

  const refreshWorkspaceList = async (selectedId = workspaceId) => {
    if (!problem) return
    const next = await getPracticeWiringWorkspaces(problem.problem_id)
    setWorkspaces(next)
    const selected = next.find((item) => item.workspace_id === selectedId)
    if (selected) setWorkspaceName(selected.workspace_name)
  }
  const selectWorkspace = async (nextId: string) => {
    if (!problem || nextId === workspaceId) return
    try {
      await savePracticeWiringDraft(problem.problem_id, problem.version, mode, connections, workspaceId, workspaceName)
      setReady(false); setWorkspaceId(nextId); window.localStorage.setItem(`electrician.qnetWorkspace.${problem.problem_id}`, nextId)
      const draft = await getPracticeWiringDraft(problem.problem_id, nextId)
      setConnections(draft?.connections ?? []); setMode(draft?.mode ?? 'graphic'); setWorkspaceName(draft?.workspace_name ?? '기본 작업공간')
      setStructuralWarnings(draft?.structural_warnings ?? []); setLastSavedAt(draft?.updated_at ?? undefined)
      setSnapshots(draft ? await getPracticeWiringSnapshots(problem.problem_id, nextId) : []); setHistory([]); setFuture([]); setSaveState('saved')
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '현재 변경을 저장하지 못해 작업공간을 전환하지 않았습니다.') }
    finally { setReady(true) }
  }
  const removeWorkspace = async () => {
    if (!problem || !ready || deletingWorkspace.current) return
    setConfirmWorkspaceDelete(false)
    deletingWorkspace.current = true
    setReady(false)
    ++saveSequence.current
    let deleted = false
    try {
      await saveQueue.current.catch(() => undefined)
      await deletePracticeWiringDraft(problem.problem_id, workspaceId)
      deleted = true
      window.localStorage.removeItem(`electrician.qnetWorkspace.${problem.problem_id}`)
      let remaining = await getPracticeWiringWorkspaces(problem.problem_id)
      const nextId = remaining[0]?.workspace_id ?? (await createPracticeWiringWorkspace(problem.problem_id, problem.version, '기본 작업공간')).workspace_id
      const next = await getPracticeWiringDraft(problem.problem_id, nextId)
      const versions = await getPracticeWiringSnapshots(problem.problem_id, nextId)
      remaining = await getPracticeWiringWorkspaces(problem.problem_id)
      setWorkspaces(remaining); setWorkspaceId(nextId); setWorkspaceName(next?.workspace_name ?? '기본 작업공간')
      setConnections(next?.connections ?? []); setMode(next?.mode ?? 'graphic'); setSnapshots(versions)
      setStructuralWarnings(next?.structural_warnings ?? []); setLastSavedAt(next?.updated_at ?? undefined)
      setHistory([]); setFuture([]); setSelectedWire(null); setSelectedPin(null); setSelectedSummaryTerminal(null)
      window.localStorage.setItem(`electrician.qnetWorkspace.${problem.problem_id}`, nextId)
      setNotice('작업공간과 저장된 버전을 삭제했습니다.'); setSaveState('saved'); setReady(true)
    } catch (reason) {
      setNotice(deleted ? '삭제는 완료했지만 다음 작업공간을 불러오지 못했습니다. 새로고침해 주세요.' : reason instanceof Error ? reason.message : '작업공간 삭제에 실패했습니다.')
      if (!deleted) setReady(true)
    } finally { deletingWorkspace.current = false }
  }
  const addWorkspace = async () => {
    if (!problem) return
    const name = `사용자 답안 ${workspaces.length + 1}`
    const created = await createPracticeWiringWorkspace(problem.problem_id, problem.version, name)
    await refreshWorkspaceList(created.workspace_id); await selectWorkspace(created.workspace_id)
  }
  const saveSnapshot = async () => {
    if (!problem) return
    await savePracticeWiringDraft(problem.problem_id, problem.version, mode, connections, workspaceId, workspaceName)
    await createPracticeWiringSnapshot(problem.problem_id, workspaceId, `버전 ${snapshots.length + 1}`)
    setSnapshots(await getPracticeWiringSnapshots(problem.problem_id, workspaceId)); await refreshWorkspaceList()
  }
  const restoreSnapshot = async (snapshotId: string) => {
    if (!problem || !snapshotId) return
    const restored = await clonePracticeWiringSnapshot(problem.problem_id, workspaceId, snapshotId)
    await refreshWorkspaceList(restored.workspace_id); await selectWorkspace(restored.workspace_id)
  }
  const downloadExport = async () => {
    if (!problem) return
    setExporting(true); setNotice(undefined)
    try {
      await savePracticeWiringDraft(problem.problem_id, problem.version, mode, connections, workspaceId, workspaceName)
      const blob = await exportPracticeWiring(problem.problem_id, workspaceId)
      const safeName = workspaceName.replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_').trim() || workspaceId
      const url = URL.createObjectURL(blob); const anchor = document.createElement('a')
      anchor.href = url; anchor.download = `${problem.problem_id}-${safeName}.json`; anchor.style.display = 'none'
      document.body.appendChild(anchor); anchor.click(); anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000)
      setNotice('JSON 다운로드가 시작되었습니다. 저장 위치를 선택해 주세요.')
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : 'JSON을 내보낼 수 없습니다.')
    } finally { setExporting(false) }
  }
  const importExport = async (file?: File) => {
    if (!problem || !file) return
    setNotice(undefined)
    try {
      if (file.size > 1_000_000) throw new Error('가져오기 파일은 1MB 이하여야 합니다.')
      const payload = JSON.parse(await file.text()) as PracticeWiringExport
      const imported = await importPracticeWiring(problem.problem_id, payload)
      await refreshWorkspaceList(imported.workspace_id); await selectWorkspace(imported.workspace_id)
      setNotice('JSON을 새 작업공간으로 가져왔습니다. 기존 작업공간은 그대로 보존됩니다.')
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : 'JSON을 가져올 수 없습니다.') }
    finally { if (importInput.current) importInput.current.value = '' }
  }

  useEffect(() => {
    const resetCircuitReference = () => setCircuitDraft({})
    window.addEventListener('electrician:reset-circuit', resetCircuitReference)
    return () => window.removeEventListener('electrician:reset-circuit', resetCircuitReference)
  }, [])

  if (!problem) return <PlaceholderPage stage="2단계" title="제어함 결선" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="⎍" />
  if (unavailable) return <PlaceholderPage stage="2단계 · 검증 대기" title="공식 결선 데이터 교차검증 중" description="원본 회로도는 1단계에서 확인할 수 있습니다. 접점별 소켓 핀과 정답 네트워크 검증이 끝나기 전에는 결선 채점을 제공하지 않습니다." icon="⌁" />

  return <section className={`workspace-page wiring-workspace${practiceMode ? ' practice-capture-workspace' : ''}`}>
    {practiceMode && workspaceOpen && <WorkspaceDialog onClose={() => { if (confirmWorkspaceDelete) setConfirmWorkspaceDelete(false); else setWorkspaceOpen(false) }}><fieldset disabled={!ready || exporting} className="capture-toolbar" aria-label="사용자 답안 작업공간 도구">
      {confirmWorkspaceDelete ? <div className="workspace-delete-confirm" role="alert"><h3>작업공간을 삭제할까요?</h3><strong>{workspaceName}</strong><p>이 작업공간의 결선과 저장 버전이 함께 삭제되며 복구할 수 없습니다. 필요하면 취소 후 JSON으로 먼저 내보내세요.</p><div><button type="button" autoFocus onClick={() => setConfirmWorkspaceDelete(false)}>취소</button><button type="button" className="confirm-danger" onClick={() => void removeWorkspace()}>삭제하기</button></div></div> : <>
      <label>작업공간<select aria-label="작업공간 선택" value={workspaceId} onChange={(event) => void selectWorkspace(event.target.value)}>{workspaces.length === 0 && <option value="main">기본 작업공간</option>}{workspaces.map((item) => <option key={item.workspace_id} value={item.workspace_id}>{item.workspace_name} · {item.workspace_id === workspaceId ? connections.length : item.connection_count}선 · {workspaceTime(item.workspace_id === workspaceId ? lastSavedAt ?? item.updated_at : item.updated_at)}</option>)}</select></label>
      <button type="button" onClick={() => void addWorkspace()}>새 작업공간</button>
      <button type="button" className="danger" onClick={() => setConfirmWorkspaceDelete(true)}>작업공간 삭제</button>
      <label>버전<select aria-label="스냅샷 선택" value="" onChange={(event) => void restoreSnapshot(event.target.value)}><option value="">이전 버전 불러오기</option>{snapshots.map((item) => <option key={item.snapshot_id} value={item.snapshot_id}>{item.label || new Date(item.created_at).toLocaleString()} · {item.connections.length}선</option>)}</select></label>
      <button type="button" onClick={() => void saveSnapshot()}>새 버전 저장</button><button type="button" disabled={exporting} onClick={() => void downloadExport()}>{exporting ? '내보내는 중…' : 'JSON 내보내기'}</button><button type="button" onClick={() => importInput.current?.click()}>JSON 가져오기</button>
      <input ref={importInput} hidden type="file" accept="application/json,.json" onChange={(event) => void importExport(event.target.files?.[0])} />

      </>}
      {notice && <p role="status">{notice}</p>}
    </fieldset></WorkspaceDialog>}
    {practiceMode && workspaceMenuHost && createPortal(<button type="button" aria-haspopup="dialog" aria-expanded={workspaceOpen} onClick={() => setWorkspaceOpen(true)}>작업공간</button>, workspaceMenuHost)}
    <header className="workspace-toolbar wiring-header"><div><span>2단계 · 실제 제어함 결선</span><h2>제어함 결선</h2></div><div className="wiring-stats">{practiceMode && <><span className={`capture-save-state ${saveState}`}>{saveState === 'waiting' ? '저장 대기' : saveState === 'saving' ? '저장 중' : saveState === 'failed' ? '저장 실패 · 편집 내용 유지' : saveState === 'changed' ? '변경됨' : `저장됨${lastSavedAt ? ` · ${workspaceTime(lastSavedAt)}` : ''}`}</span>{!workspaceMenuHost && <button type="button" aria-haspopup="dialog" aria-expanded={workspaceOpen} onClick={() => setWorkspaceOpen(true)}>작업공간</button>}</>}<span>{problem.problem_id} · v{problem.version}</span><span>연결 {connections.length}</span>{!practiceMode && <span>제출 {progress?.attempt_count ?? 0}회</span>}</div></header>
    {loading && <div className="circuit-loading">문제별 제어함 배치를 불러오는 중입니다.</div>}
    {error && <div className="circuit-load-error" role="alert"><strong>제어함을 표시할 수 없습니다.</strong><span>{error}</span></div>}
    {!loading && !error && board && <div className={`wiring-layout${externalDevices.length ? ' with-left-sidebar' : ''}`}>
      {externalDevices.length > 0 && <aside className="work-left-sidebar wiring-external-panel" aria-label="외부 결선 패널">{externalDevices.length > 0 && <section className="external-wiring-tray" aria-label="외부 기구선"><div className="external-wiring-heading"><strong>외부 기구선</strong><span>전선 끝을 선택하거나 TB 단자로 드래그하세요.</span><small>TB 한 번호: 외부측 2가닥 + 내부측 2가닥</small></div><div className="external-device-list">{externalDevices.map((device) => <article key={device.device_id} className="external-device-card" aria-label={device.contact_type ? `${device.label}, ${contactTypeDescription(device.contact_type)}` : device.label}><strong>{device.label}{device.contact_type && <ContactTypeBadge contactType={device.contact_type} />}</strong><div>{device.terminals.map((terminal) => { const linked = connections.flatMap((item, index) => item.from === terminal.terminal_id ? [{ id: item.to, index }] : item.to === terminal.terminal_id ? [{ id: item.from, index }] : [])[0]; const count = terminalConnectionCounts.get(terminal.terminal_id) ?? 0; return <button key={terminal.terminal_id} type="button" draggable={!linked} className={selectedPin === terminal.terminal_id ? 'selected' : ''} aria-label={`${terminal.terminal_id} 외부 기구선, ${count} / ${terminal.max_connections} 연결`} onClick={() => { if (linked) { setSelectedWire(linked.index); setSelectedPin(null) } else pinClick(terminal.terminal_id) }} onDragStart={(event) => { event.dataTransfer.setData('application/x-electrician-terminal', terminal.terminal_id); event.dataTransfer.effectAllowed = 'link' }}><span className={`external-wire-swatch ${isProtectiveEarth(terminal.terminal_id) ? 'green' : terminal.wire_color}`} />{terminal.terminal_id}<small>{linked ? `→ ${linked.id}` : '미연결'} · {count}/{terminal.max_connections}</small></button> })}</div></article>)}</div></section>}</aside>}
      <div className="wiring-stage">
        <div className="wiring-toolbar" aria-label="결선 편집 도구">
          <button className={mode === 'graphic' ? 'active' : ''} onClick={() => { setMode('graphic'); setSelectedSummaryTerminal(null) }}>그래픽 모드</button><button className={mode === 'summary' ? 'active' : ''} onClick={() => setMode('summary')}>요약 모드</button>
          <span className="toolbar-separator" /><button disabled={!history.length} onClick={undo}>실행 취소</button><button disabled={!future.length} onClick={redo}>다시 실행</button><button disabled={selectedWire === null} onClick={removeSelected}>선택 전선 삭제</button><button className="danger" onClick={() => void reset()}>전체 초기화</button><span className="board-auto-fit-label">화면 자동 맞춤</span>
        </div>

        <WiringBoard board={board} connections={connections} externalDevices={externalDevices} mode={mode} selectedPin={selectedPin} selectedWire={selectedWire} selectedSummaryTerminal={selectedSummaryTerminal} zoom={1} onPinClick={pinClick} onPinPointerDown={(id) => { dragStart.current = id }} onPinPointerUp={pinPointerUp} onExternalDrop={(externalId, targetId) => connect(externalId, targetId)} onWireSelect={(index) => { setSelectedWire(index); setSelectedPin(null); if (mode === 'graphic') setSelectedSummaryTerminal(null) }} onSummarySelect={(terminalId, connectionIndices) => { setSelectedSummaryTerminal(terminalId); setSelectedWire(connectionIndices[0] ?? null); setSelectedPin(null) }} onClearSelection={() => { setSelectedPin(null); setSelectedWire(null); setSelectedSummaryTerminal(null) }} />
      </div>
      <aside className="wiring-panel">
        <section><span className="panel-kicker">현재 작업</span><h3>{selectedSummaryTerminal ? `${selectedSummaryTerminal} · ${selectedSummaryConnections.length}개 연결` : selectedConnection ? `${selectedConnection.from} → ${selectedConnection.to}` : selectedPin ? `시작 단자 ${selectedPin}` : '단자를 선택하세요'}</h3>{mode === 'graphic' && <p>시작 단자와 종료 단자를 차례로 클릭하거나 드래그하여 연결합니다. 새 전선은 노란색으로 생성됩니다.</p>}{selectedSummaryTerminal && mode === 'summary' && <div className="summary-connection-list" aria-label={`${selectedSummaryTerminal} 상대 단자 목록`}>{selectedSummaryConnections.map((item, index) => <button key={item.connectionIndex} type="button" className={selectedWire === item.connectionIndex ? 'selected' : ''} onClick={() => setSelectedWire(item.connectionIndex)}><span>{index + 1}번째 연결</span><strong>{item.other}</strong></button>)}</div>}{selectedConnection && !selectedSummaryTerminal && mode === 'summary' && <dl className="summary-connection-detail"><div><dt>연결 단자 1</dt><dd>{selectedConnection.from}</dd></div><div><dt>연결 단자 2</dt><dd>{selectedConnection.to}</dd></div></dl>}{selectedConnection && (isProtectiveEarth(selectedConnection.from) || isProtectiveEarth(selectedConnection.to) ? <p>PE 보호접지선 · 녹색</p> : <label className="wire-color-select">물리 전선 색상<select value={selectedConnection.wire_color} onChange={(event) => changeWireColor(event.target.value as WiringConnection['wire_color'])}><option value="yellow">노란색</option><option value="brown">갈색</option><option value="black">검은색</option><option value="gray">회색</option></select></label>)}</section>
        {!practiceMode && <section className="virtual-warning"><strong>가상 학습 데이터</strong><p>이 문제는 배선 기능 확인용이며 실제 시험 정답이 아닙니다.</p></section>}
        <section><span className="panel-kicker">결선 상태</span><dl><div><dt>표시 모드</dt><dd>{mode === 'graphic' ? '그래픽' : '요약'}</dd></div><div><dt>연결 수</dt><dd>{connections.length}</dd></div><div><dt>경로 방식</dt><dd>직교·빈 통로 우선</dd></div></dl>{notice && <div className="submission-notice" role="alert">{notice}</div>}{practiceMode && structuralWarnings.length > 0 && <div className="structural-warning-list" role="status"><strong>결선은 저장되었습니다. 구조 경고를 확인하세요.</strong>{structuralWarnings.map((warning, index) => <span key={`${warning.code}-${index}`}>구조 경고: {warning.message}</span>)}</div>}{result && <div className={`wiring-result ${result.overall_correct ? 'correct' : result.gradable ? 'wrong' : 'warning'}`}><b>{resultClassificationLabels[result.result_classification ?? (result.gradable ? 'incorrect' : 'ungradable')]}</b><strong>{result.message}</strong><span>정상 네트워크 {result.correct_net_count ?? result.correct_count}/{result.required_net_count ?? result.required_count}</span>{result.gradable && <span>누락 {result.missing_net_count ?? result.missing_connections.length} · 합쳐짐 {result.merged_net_count ?? 0} · 불필요 {result.extra_connection_count ?? result.extra_connections.length}</span>}{result.used_alternative_tb_numbers && <span>다른 TB 번호 사용 · 전기적 동등성 인정</span>}{(result.warnings ?? []).map((warning) => <span key={warning}>{warning}</span>)}</div>}{!practiceMode && result?.gradable === false && <button className="preview-operation" type="button" onClick={() => navigate('/operation')}>동작시험 화면 미리보기</button>}{practiceMode && problem.capabilities.operation_previewable ? <button className="submit-circuit" onClick={() => void openPracticeOperation()}>저장 후 동작시험</button> : practiceMode ? <div className="operation-waiting">결선 저장 완료 · 동작 엔진 검증 대기</div> : <button className="submit-circuit" onClick={() => void submit()}>결선 제출</button>}</section>
        <section className="circuit-reference-panel" aria-label="회로도 분석 참고">
          <div className="circuit-reference-header"><div><span className="panel-kicker">1단계 참고</span><h3>{practiceMode ? '회로도 분석 참고' : '회로도 분석 결과'}</h3></div>{!practiceMode && <strong>{analyzedQuestionCount} / {problem.socket_questions.length} 입력</strong>}</div>
          {practiceMode && <div className="analysis-source-tabs" role="group" aria-label="결선 참고 자료 선택"><button type="button" className={referenceView === 'schematic' ? 'active' : ''} onClick={() => setReferenceView('schematic')}>시퀀스 회로도</button><button type="button" className={referenceView === 'layout' ? 'active' : ''} onClick={() => setReferenceView('layout')}>배관·배치도</button></div>}
          {referenceDiagram && <CircuitDiagram key={`${problem.problem_id}-reference-${referenceView}`} diagram={referenceView === 'layout' ? layoutReferenceDiagram : referenceDiagram} questions={referenceView === 'schematic' ? problem.socket_questions : []} selectedQuestionId={null} draft={circuitDraft} readOnly compact showToolbar={practiceMode} ariaLabel="회로도 분석 참고창" backgroundHref={problem.problem_type === 'official' ? (referenceView === 'layout' ? layoutReferenceUrl(problem.problem_id) : schematicUrl(problem.problem_id)) : undefined} annotationMarkers={referenceView === 'schematic' ? parseAnnotations(analysisDraft?.annotations ?? {}) : []} onSelect={() => undefined} onClear={() => undefined} />}
          {practiceMode && analysisDraft?.memo && <p className="reference-analysis-memo">{analysisDraft.memo}</p>}
          {!practiceMode && analyzedQuestionCount === 0 && <p className="circuit-reference-empty">1단계에서 입력한 소켓번호가 아직 없습니다.</p>}
        </section>
      </aside>
    </div>}
  </section>
}
