import { useEffect, useMemo, useState } from 'react'
import {
  deleteMountingDraft, getBoard, getMounting, getMountingDraft, getMountingProgress,
  getWiringDraft, getWiringProgress, saveMountingDraft, submitMountingAttempt,
  type BoardDefinition, type MountDevice, type MountTarget, type MountingAttemptResult,
  type MountingDefinition, type MountingPlacement, type MountingProgress,
  type PublicProblemDetail, type WiringConnection, type WiringProgress,
} from '../api/client'
import { MountingBoard } from '../features/mounting/components/MountingBoard'
import { PlaceholderPage } from './PlaceholderPage'

function socketName(socketTypeId: string) {
  if (socketTypeId === 'socket_8p_base') return '8P 소켓'
  if (socketTypeId === 'socket_12p_base') return '12P 소켓'
  return socketTypeId
}

function compatibilityError(device: MountDevice, target: MountTarget) {
  if (!target.enabled) return '이 위치는 현재 사용할 수 없습니다.'
  if (!device.compatible_socket_type_ids.includes(target.socket_type_id)) {
    return `${socketName(device.compatible_socket_type_ids[0])}용 기구는 ${socketName(target.socket_type_id)}에 장착할 수 없습니다.`
  }
  if (!target.allowed_device_type_ids.includes(device.device_type_id)) {
    return `${target.socket_id} 위치에는 ${device.label} 기구를 장착할 수 없습니다.`
  }
  return undefined
}

export function DeviceMountingPage({ problem }: { problem?: PublicProblemDetail }) {
  const [board, setBoard] = useState<BoardDefinition>()
  const [mounting, setMounting] = useState<MountingDefinition | null>()
  const [connections, setConnections] = useState<WiringConnection[]>([])
  const [wiringProgress, setWiringProgress] = useState<WiringProgress>()
  const [placements, setPlacements] = useState<MountingPlacement[]>([])
  const [history, setHistory] = useState<MountingPlacement[][]>([])
  const [future, setFuture] = useState<MountingPlacement[][]>([])
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)
  const [progress, setProgress] = useState<MountingProgress>()
  const [result, setResult] = useState<MountingAttemptResult>()
  const [notice, setNotice] = useState<string>()
  const [error, setError] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [ready, setReady] = useState(false)

  const deviceMap = useMemo(() => new Map(mounting?.available_devices.map((item) => [item.mount_device_id, item]) ?? []), [mounting])
  const targetMap = useMemo(() => new Map(mounting?.mount_targets.map((item) => [item.socket_id, item]) ?? []), [mounting])
  const placementByDevice = useMemo(() => new Map(placements.map((item) => [item.mount_device_id, item])), [placements])
  const placementBySocket = useMemo(() => new Map(placements.map((item) => [item.socket_id, item])), [placements])
  const selectedDevice = selectedDeviceId ? deviceMap.get(selectedDeviceId) : undefined
  const wiringIncomplete = Boolean(wiringProgress?.required_count && connections.length < wiringProgress.required_count)

  useEffect(() => {
    if (!problem) return
    const controller = new AbortController()
    setLoading(true); setReady(false); setError(undefined); setNotice(undefined); setResult(undefined)
    setSelectedDeviceId(null); setHistory([]); setFuture([]); setZoom(1)
    Promise.all([
      getBoard(problem.problem_id, controller.signal),
      getWiringDraft(problem.problem_id, controller.signal),
      getWiringProgress(problem.problem_id, controller.signal),
      getMounting(problem.problem_id, controller.signal),
      getMountingDraft(problem.problem_id, controller.signal),
      getMountingProgress(problem.problem_id, controller.signal),
    ]).then(([nextBoard, wiringDraft, nextWiringProgress, nextMounting, mountingDraft, nextProgress]) => {
      setBoard(nextBoard)
      setConnections(wiringDraft?.problem_version === problem.version ? wiringDraft.connections : [])
      setWiringProgress(nextWiringProgress)
      setMounting(nextMounting)
      setPlacements(mountingDraft?.problem_version === problem.version ? mountingDraft.placements : [])
      if (mountingDraft && mountingDraft.problem_version !== problem.version) setNotice('이전 문제 버전의 장착 임시저장은 적용하지 않았습니다.')
      setProgress(nextProgress)
      setReady(true)
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '기구 장착 데이터를 불러올 수 없습니다.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [problem])

  useEffect(() => {
    if (!problem || !mounting || !ready) return
    const timer = window.setTimeout(() => {
      saveMountingDraft(problem.problem_id, problem.version, placements)
        .catch((reason: unknown) => setNotice(reason instanceof Error ? reason.message : '기구 장착 상태를 저장할 수 없습니다.'))
    }, 450)
    return () => window.clearTimeout(timer)
  }, [mounting, placements, problem, ready])

  const commit = (next: MountingPlacement[]) => {
    setHistory((values) => [...values.slice(-29), placements])
    setFuture([]); setPlacements(next); setResult(undefined); setNotice(undefined)
  }

  const placeDevice = (deviceId: string, socketId: string) => {
    const device = deviceMap.get(deviceId)
    const target = targetMap.get(socketId)
    if (!device || !target) { setNotice('기구 또는 장착 위치를 찾을 수 없습니다.'); return }
    const incompatible = compatibilityError(device, target)
    if (incompatible) { setNotice(incompatible); return }
    const occupied = placementBySocket.get(socketId)
    if (occupied && occupied.mount_device_id !== deviceId) { setNotice('이미 다른 기구가 장착된 소켓입니다.'); return }
    const current = placementByDevice.get(deviceId)
    if (current?.socket_id === socketId) { setSelectedDeviceId(deviceId); return }
    const next = placements.filter((item) => item.mount_device_id !== deviceId)
    commit([...next, { mount_device_id: deviceId, socket_id: socketId }])
    setSelectedDeviceId(deviceId)
  }

  const targetClick = (socketId: string) => {
    const occupied = placementBySocket.get(socketId)
    if (!selectedDeviceId) {
      if (occupied) { setSelectedDeviceId(occupied.mount_device_id); setNotice(undefined) }
      else setNotice('오른쪽 기구 보관함에서 장착할 기구를 먼저 선택하세요.')
      return
    }
    if (occupied?.mount_device_id === selectedDeviceId) { setNotice(undefined); return }
    placeDevice(selectedDeviceId, socketId)
  }

  const removeSelected = () => {
    if (!selectedDeviceId || !placementByDevice.has(selectedDeviceId)) return
    commit(placements.filter((item) => item.mount_device_id !== selectedDeviceId))
    setSelectedDeviceId(null)
  }
  const undo = () => {
    const previous = history.at(-1); if (!previous) return
    setFuture((values) => [placements, ...values]); setPlacements(previous)
    setHistory((values) => values.slice(0, -1)); setSelectedDeviceId(null); setResult(undefined); setNotice(undefined)
  }
  const redo = () => {
    const next = future[0]; if (!next) return
    setHistory((values) => [...values, placements]); setPlacements(next)
    setFuture((values) => values.slice(1)); setSelectedDeviceId(null); setResult(undefined); setNotice(undefined)
  }
  const reset = async () => {
    if (!window.confirm('현재 문제의 기구 장착 상태를 모두 초기화하시겠습니까?')) return
    commit([]); setSelectedDeviceId(null)
    await deleteMountingDraft(problem!.problem_id).catch(() => undefined)
  }
  const submit = async () => {
    try {
      const next = await submitMountingAttempt(problem!.problem_id, problem!.version, placements)
      setResult(next); setNotice(undefined)
      setProgress((value) => ({
        problem_id: problem!.problem_id, attempt_count: (value?.attempt_count ?? 0) + 1,
        last_submitted_at: new Date().toISOString(), last_overall_correct: next.overall_correct,
        last_correct_count: next.correct_count, required_count: next.required_count,
      }))
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : '기구 장착 제출에 실패했습니다.') }
  }

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if ((event.key === 'Delete' || event.key === 'Backspace') && selectedDeviceId && placementByDevice.has(selectedDeviceId)) { event.preventDefault(); removeSelected() }
      if (event.key === 'Escape') { setSelectedDeviceId(null); setNotice(undefined) }
    }
    window.addEventListener('keydown', keydown)
    return () => window.removeEventListener('keydown', keydown)
  })

  useEffect(() => {
    const resetMounting = () => {
      setPlacements([]); setHistory([]); setFuture([]); setSelectedDeviceId(null); setResult(undefined); setNotice(undefined)
      if (problem) void deleteMountingDraft(problem.problem_id).catch(() => undefined)
    }
    const resetWiring = () => setConnections([])
    window.addEventListener('electrician:reset-mounting', resetMounting)
    window.addEventListener('electrician:reset-wiring', resetWiring)
    return () => {
      window.removeEventListener('electrician:reset-mounting', resetMounting)
      window.removeEventListener('electrician:reset-wiring', resetWiring)
    }
  }, [problem])

  if (!problem) return <PlaceholderPage stage="3단계" title="기구 장착" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="▦" />

  return <section className="workspace-page mounting-workspace">
    <header className="workspace-toolbar mounting-header"><div><span>3단계 · 기구 장착</span><h2>기구 장착</h2></div><div className="wiring-stats"><span>장착 {placements.length}/{mounting?.available_devices.length ?? 0}</span><span>제출 {progress?.attempt_count ?? 0}회</span></div></header>
    {loading && <div className="circuit-loading">문제별 기구와 장착 위치를 불러오는 중입니다.</div>}
    {error && <div className="circuit-load-error" role="alert"><strong>기구 장착 화면을 표시할 수 없습니다.</strong><span>{error}</span></div>}
    {!loading && !error && board && mounting === null && <div className="mounting-not-ready"><strong>기구 장착 데이터 준비 중</strong><span>이 문제에는 아직 장착할 기구와 소켓 위치가 정의되지 않았습니다.</span></div>}
    {!loading && !error && board && mounting && <div className="mounting-layout">
      <div className="wiring-stage mounting-stage">
        <div className="wiring-toolbar" aria-label="기구 장착 편집 도구">
          <button aria-label="확대" onClick={() => setZoom((value) => Math.min(1.4, value + .1))}>＋</button><button aria-label="축소" onClick={() => setZoom((value) => Math.max(.7, value - .1))}>－</button><button onClick={() => setZoom(1)}>화면 맞춤</button>
          <span className="toolbar-separator" /><button disabled={!history.length} onClick={undo}>실행 취소</button><button disabled={!future.length} onClick={redo}>다시 실행</button><button disabled={!selectedDeviceId || !placementByDevice.has(selectedDeviceId)} onClick={removeSelected}>선택 기구 분리</button><button className="danger" onClick={() => void reset()}>장착 초기화</button>
          <span className="mounting-readonly-note">배선은 읽기 전용입니다.</span>
        </div>
        <MountingBoard board={board} connections={connections} devices={mounting.available_devices} targets={mounting.mount_targets} placements={placements} selectedDeviceId={selectedDeviceId} zoom={zoom} result={result} onTargetClick={targetClick} onDropDevice={placeDevice} onClearSelection={() => setSelectedDeviceId(null)} />
      </div>
      <aside className="wiring-panel mounting-panel">
        <section><span className="panel-kicker">현재 선택</span><h3>{selectedDevice?.label ?? '기구를 선택하세요'}</h3><p>{selectedDevice ? `${selectedDevice.device_type_id} · ${selectedDevice.compatible_socket_type_ids.map(socketName).join(', ')}` : '기구를 클릭하거나 드래그한 뒤 중앙의 장착 소켓을 선택하세요.'}</p>{selectedDevice && placementByDevice.has(selectedDevice.mount_device_id) && <button className="clear-answer" onClick={removeSelected}>현재 기구 분리</button>}</section>
        {wiringIncomplete && <section className="mounting-wiring-warning"><strong>결선이 아직 완성되지 않았습니다.</strong><p>현재 저장된 결선 {connections.length}개 / 최근 문제 기준 {wiringProgress?.required_count ?? 0}개입니다. 장착 연습은 계속할 수 있습니다.</p></section>}
        {problem.status !== 'verified' && <section className="virtual-warning"><strong>가상 학습 데이터</strong><p>현재 문제의 기구와 장착 정답은 기능 확인용 데이터입니다.</p></section>}
        <section className="device-shelf"><span className="panel-kicker">기구 보관함</span><div className="device-card-list">{mounting.available_devices.map((device) => {
          const placement = placementByDevice.get(device.mount_device_id)
          return <button key={device.mount_device_id} type="button" draggable className={`mount-device-card${selectedDeviceId === device.mount_device_id ? ' selected' : ''}${placement ? ' mounted' : ''}`} aria-pressed={selectedDeviceId === device.mount_device_id} onClick={() => { setSelectedDeviceId(device.mount_device_id); setNotice(undefined) }} onDragStart={(event) => { event.dataTransfer.setData('text/plain', device.mount_device_id); event.dataTransfer.effectAllowed = 'move'; setSelectedDeviceId(device.mount_device_id) }}>
            <span className={`device-card-icon ${device.graphic_type}`}>{device.graphic_type === 'timer' ? '◷' : device.graphic_type === 'relay' ? '▣' : '▤'}</span><span><strong>{device.label}</strong><small>{socketName(device.compatible_socket_type_ids[0])}</small></span><em>{placement ? `${placement.socket_id} 장착` : '대기'}</em>
          </button>
        })}</div></section>
        <section><span className="panel-kicker">장착 상태</span><dl><div><dt>장착 완료</dt><dd>{placements.length}/{mounting.available_devices.length}</dd></div><div><dt>결선 표시</dt><dd>{connections.length}개 · 읽기 전용</dd></div><div><dt>임시저장</dt><dd>{ready ? '자동 저장' : '준비 중'}</dd></div></dl>{notice && <div className="submission-notice" role="alert">{notice}</div>}{result && <div className={`mounting-result ${result.overall_correct ? 'correct' : result.gradable ? 'wrong' : 'warning'}`}><strong>{result.message}</strong><span>정상 {result.correct_count}/{result.required_count}</span>{result.gradable && <span>누락 {result.missing_device_ids.length} · 위치 오류 {result.wrong_placements.length} · 추가 {result.extra_device_ids.length}</span>}</div>}<button className="submit-circuit" onClick={() => void submit()}>기구 장착 제출</button></section>
        <section><span className="panel-kicker">호환 규칙</span><p>소켓의 8P·12P 형식과 위치별 허용 기구 종류가 모두 맞아야 장착됩니다. 제출 전에는 정답 위치를 표시하지 않습니다.</p></section>
      </aside>
    </div>}
  </section>
}
