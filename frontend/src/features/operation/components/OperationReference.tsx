import { useEffect, useState } from 'react'
import { getCircuitAnalysisDraft, getDiagram, layoutReferenceUrl, schematicUrl, type OperationSessionState, type SchematicDiagram } from '../../../api/client'
import { CircuitDiagram } from '../../../components/circuit/CircuitDiagram'
import { parseAnnotations, type DiagramAnnotationMarker } from '../../circuit/analysisAnnotations'
import { layoutDevices } from '../layoutDevices'

const layoutDiagram: SchematicDiagram = { schema_version: '1.0', view_box: { x: 0, y: 0, width: 992, height: 1402 }, sections: [], elements: [], conductors: [] }
const colors: Record<string, string> = { RL: '#ef4444', GL: '#22c55e', YL: '#facc15', WL: '#f8fafc' }

export function LayoutActivity({ problemId, session }: { problemId: string; session?: OperationSessionState }) {
  return <g className="layout-activity" aria-label="배관도 실시간 기구 상태">{layoutDevices(problemId).map(device => {
    const control = session?.controls[device.id]
    const output = device.id === 'BZ' ? session?.audible_outputs?.[device.id] : session?.indicators[device.id]
    const state = control ? (control.active ? 'active' : 'idle') : output ?? 'unknown'
    const active = state === 'on' || state === 'active'
    const label = control ? device.id === 'SS' ? control.active ? '자동 A' : '수동 M' : control.active ? '누름' : '복귀' : state === 'unknown' ? '상태 없음' : state === 'error' ? '오류' : state === 'on' ? device.id === 'BZ' ? '울림' : '점등' : '꺼짐'
    return <g key={device.id} data-layout-device={device.id} data-state={state} role="img" aria-label={`${device.id} ${label}`} transform={`translate(${device.x} ${device.y})`} className={`layout-device ${active ? 'active' : ''} ${device.id === 'BZ' ? 'buzzer' : ''}`}>
      <title>{device.id} · {label}</title>
      <circle r="11" fill={state === 'error' ? '#dc2626' : active ? colors[device.id] ?? '#38bdf8' : 'transparent'} stroke={active ? '#075985' : state === 'unknown' ? '#94a3b8' : 'transparent'} strokeWidth="2" />
      {device.id === 'SS' && control && <line x1="-6" x2="6" y1={control.active ? 6 : -6} y2={control.active ? -6 : 6} stroke="#0f172a" strokeWidth="3" />}
      {device.id === 'BZ' && active && <circle className="buzzer-wave" r="14" fill="none" stroke="#0284c7" strokeWidth="2" />}
    </g>
  })}</g>
}

export function OperationReference({ problemId, view, session }: { problemId: string; view: 'schematic' | 'layout'; session?: OperationSessionState }) {
  const [diagram, setDiagram] = useState<SchematicDiagram>()
  const [markers, setMarkers] = useState<DiagramAnnotationMarker[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    setDiagram(undefined); setMarkers([]); setError('')
    getDiagram(problemId, controller.signal).then(value => { if (!controller.signal.aborted) setDiagram(value) }).catch(() => { if (!controller.signal.aborted) setError('회로도를 불러오지 못했습니다.') })
    getCircuitAnalysisDraft(problemId, controller.signal).then(value => { if (!controller.signal.aborted) setMarkers(parseAnnotations(value?.annotations ?? {})) }).catch(() => undefined)
    return () => controller.abort()
  }, [problemId])
  return <section className="operation-reference" aria-label="동작시험 도면">
    <p>{view === 'layout' ? '실제 엔진 상태 표시 · 표시등 점등 / 부저 울림 표시 / PB·SS 조작 상태 (소리 출력 없음)' : '시퀀스 회로도는 분석 메모를 표시하는 읽기 전용 참고 자료입니다.'}</p>
    {view === 'schematic' && error && <p role="alert">{error}</p>}
    {(view === 'layout' || diagram) && <CircuitDiagram key={`${problemId}-${view}`} diagram={view === 'layout' ? layoutDiagram : diagram!} questions={[]} draft={{}} selectedQuestionId={null} readOnly
      ariaLabel={view === 'layout' ? '동작시험 배관배치도' : '동작시험 시퀀스 회로도'} backgroundHref={view === 'layout' ? layoutReferenceUrl(problemId) : schematicUrl(problemId)}
      annotationMarkers={view === 'schematic' ? markers : []} overlay={view === 'layout' ? <LayoutActivity problemId={problemId} session={session} /> : undefined} onSelect={() => undefined} onClear={() => undefined} />}
    {view === 'layout' && <div className="layout-output-legend" aria-label="실시간 외부 기구 상태">
      {!session && <span>동작 세션 없음 · 상태를 표시할 수 없습니다.</span>}
      {Object.entries(session?.indicators ?? {}).map(([id,state]) => <span key={id} className={`output-${state}`}><i style={{ background: state === 'on' ? colors[id] ?? '#38bdf8' : '#cbd5e1' }} />{id} {state === 'on' ? '점등' : state === 'off' ? '꺼짐' : '오류'}</span>)}
      {Object.entries(session?.audible_outputs ?? {}).map(([id,state]) => <span key={id}>{id} {state === 'on' ? '울림' : state === 'off' ? '정지' : '오류'}</span>)}
      {Object.entries(session?.motors ?? {}).map(([id,state]) => <span key={id}><i className={state === 'forward' || state === 'reverse' ? `motor-rotor ${state}` : 'motor-rotor'}>✣</i>{id} {state === 'forward' ? '정회전' : state === 'reverse' ? '역회전' : state === 'stopped' || state === 'power_off' ? '정지' : '상태 확인'}</span>)}
    </div>}
  </section>
}
