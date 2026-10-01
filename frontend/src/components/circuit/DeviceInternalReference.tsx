import { useState } from 'react'
import { analysisReferenceUrl, type PublicProblemDetail } from '../../api/client'
import { WorkspaceDialog } from '../WorkspaceDialog'

export function deviceReferenceId(deviceId: string): string | undefined {
  if (/^MC\d+$/.test(deviceId)) return 'mc'
  if (/^X\d*$/.test(deviceId)) return 'relay'
  if (/^T\d*$/.test(deviceId)) return 'timer'
  return ({ EOCR: 'eocr', FR: 'fr', FLS: 'fls', SS: 'ss' } as Record<string, string>)[deviceId]
}

export function DeviceInternalReference({ problem, deviceId, onSelect }: {
  problem: PublicProblemDetail; deviceId: string; onSelect: (id: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [failedUrl, setFailedUrl] = useState('')
  const devices = [...new Set([
    ...problem.available_devices.flatMap(item => typeof item.device_id === 'string' ? [item.device_id] : []),
    ...problem.circuit.devices.map(item => item.device_id),
    ...(problem.wiring_semantics?.external_devices ?? []).map(item => item.device_id),
    ...(deviceId ? [deviceId] : []),
  ])].filter(id => id !== 'PWR').sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
  const referenceId = deviceReferenceId(deviceId)
  const url = referenceId ? analysisReferenceUrl(problem.problem_id, referenceId) : undefined
  const missing = !url
  const failed = Boolean(url && url === failedUrl)
  return <section className="device-internal-reference" aria-label="선택 기구 내부결선도">
    <strong>선택 기구 내부결선도</strong>
    <label>기구 선택<select aria-label="내부결선도 기구 선택" value={deviceId} onChange={event => onSelect(event.target.value)}>
      <option value="">접점·코일을 클릭하거나 선택하세요</option>
      {devices.map(id => <option key={id} value={id}>{id}</option>)}
    </select></label>
    {!deviceId ? <p>회로도의 접점·코일을 누르면 해당 기구의 원본 그림이 표시됩니다.</p>
      : missing ? <p>{deviceId}의 별도 내부결선도는 이 PDF에 없습니다. 시퀀스 회로도의 기호를 참고하세요.</p>
        : failed ? <div role="alert"><p>그림을 불러오지 못했습니다. 서버 연결을 확인한 뒤 다시 시도하세요.</p><button type="button" onClick={() => setFailedUrl('')}>다시 불러오기</button></div>
        : <><button type="button" className="device-reference-image" aria-label={`${deviceId} 내부결선도 확대`} onClick={() => setExpanded(true)}>
          <img src={url} alt={`${deviceId} 내부결선도 · 공개문제 9쪽 원본`} draggable={false} onError={() => setFailedUrl(url!)} />
        </button><small>원본 그림 · 클릭하여 크게 보기</small></>}
    {expanded && !missing && !failed && <WorkspaceDialog title={`${deviceId} 내부결선도`} onClose={() => setExpanded(false)}>
      <div className="device-reference-expanded"><img src={url} alt={`${deviceId} 내부결선도 확대 그림`} draggable={false} /></div>
    </WorkspaceDialog>}
  </section>
}
