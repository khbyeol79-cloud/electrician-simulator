import type {
  BoardDefinition, BoardItem, MountDevice, MountTarget, MountingAttemptResult,
  MountingPlacement, WiringConnection,
} from '../../../api/client'
import { BoardItemBody, WIRE_COLORS } from '../../wiring/components/WiringBoard'
import { routeConnections } from '../../wiring/engine/orthogonalRouter'

const graphicLabels = { relay: '8P RELAY', timer: '8P TIMER', contactor: '12P RELAY' }

function StaticPins({ item }: { item: BoardItem }) {
  return <>{item.pins.map((pin) => {
    const labelY = pin.side === 'top' ? pin.y + 25 : pin.y - 16
    return <g key={pin.terminal_id} className={`board-pin static${pin.enabled ? '' : ' disabled'}`}>
      <circle cx={pin.x} cy={pin.y} r="13" /><circle cx={pin.x} cy={pin.y} r="5" />
      <text x={pin.x} y={labelY} textAnchor="middle">{pin.label}</text>
    </g>
  })}</>
}

function MountedDeviceGraphic({ item, device }: { item: BoardItem; device: MountDevice }) {
  const x = item.x + 24
  const y = item.y + 36
  const width = item.width - 48
  const height = item.height - 72
  const cx = x + width / 2
  const cy = y + height / 2
  const shortLabel = device.label.split(' ')[0]
  return <g className={`mounted-device-graphic ${device.graphic_type}`}>
    <rect className="mounted-device-shell" x={x} y={y} width={width} height={height} rx="9" />
    {device.graphic_type === 'timer' && <g className="timer-face"><circle cx={cx} cy={cy - 5} r={Math.min(width, height) * .25} /><line x1={cx} y1={cy - 5} x2={cx + 15} y2={cy - 20} /><circle cx={cx} cy={cy - 5} r="4" /></g>}
    {device.graphic_type === 'relay' && <g className="relay-face"><rect x={cx - 29} y={cy - 25} width="58" height="38" rx="4" /><path d={`M ${cx - 23} ${cy - 6} q 8 -16 16 0 t 16 0 t 16 0`} /></g>}
    {device.graphic_type === 'contactor' && <g className="contactor-face">{[-28, 0, 28].map((offset) => <g key={offset}><rect x={cx + offset - 9} y={cy - 29} width="18" height="35" rx="2" /><line x1={cx + offset - 7} y1={cy + 15} x2={cx + offset + 7} y2={cy + 15} /></g>)}</g>}
    <text className="mounted-device-name" x={cx} y={y + height - 20} textAnchor="middle">{shortLabel}</text>
    <text className="mounted-device-type" x={cx} y={y + height - 7} textAnchor="middle">{graphicLabels[device.graphic_type]}</text>
  </g>
}

function resultClass(target: MountTarget, placement: MountingPlacement | undefined, result: MountingAttemptResult | undefined) {
  if (!result) return ''
  if (placement && result.correct_device_ids.includes(placement.mount_device_id)) return ' correct'
  if (placement && result.wrong_placements.some((item) => item.mount_device_id === placement.mount_device_id)) return ' wrong'
  if (result.missing_socket_ids.includes(target.socket_id)) return ' missing'
  return ''
}

export function MountingBoard({
  board, connections, devices, targets, placements, selectedDeviceId, zoom, result,
  onTargetClick, onDropDevice, onClearSelection,
}: {
  board: BoardDefinition; connections: WiringConnection[]; devices: MountDevice[]; targets: MountTarget[]
  placements: MountingPlacement[]; selectedDeviceId: string | null; zoom: number; result?: MountingAttemptResult
  onTargetClick: (socketId: string) => void
  onDropDevice: (deviceId: string, socketId: string) => void; onClearSelection: () => void
}) {
  const routed = routeConnections(board, connections)
  const deviceMap = new Map(devices.map((device) => [device.mount_device_id, device]))
  const itemMap = new Map(board.items.map((item) => [item.item_id, item]))
  const placementBySocket = new Map(placements.map((placement) => [placement.socket_id, placement]))
  return <div className="wiring-board-scroll mounting-board-scroll">
    <svg className="wiring-board mounting-board" role="img" aria-label="기구 장착 제어함" viewBox={`0 0 ${board.width} ${board.height}`} onClick={onClearSelection}>
      <g transform={`translate(${board.width * (1 - zoom) / 2} ${board.height * (1 - zoom) / 2}) scale(${zoom})`}>
        <rect className="board-background" x="4" y="4" width={board.width - 8} height={board.height - 8} rx="8" />
        <g className="routing-channel-layer">{board.routing_channels.map((channel) => <rect key={channel.channel_id} className={channel.channel_type} x={channel.x} y={channel.y} width={channel.width} height={channel.height} />)}</g>
        <g className="board-item-layer">{board.items.map((item) => <BoardItemBody key={item.item_id} item={item} />)}</g>
        <g className="wire-layer readonly">{routed.map((wire) => {
          const points = wire.points.map((point) => `${point.x},${point.y}`).join(' ')
          return <g key={`${wire.from}|${wire.to}`} className="board-wire readonly"><polyline className="wire-depth" points={points} /><polyline className="wire-visible" points={points} style={{ stroke: WIRE_COLORS[wire.wire_color] }} /></g>
        })}</g>
        <g className="board-pin-layer readonly">{board.items.map((item) => <StaticPins key={item.item_id} item={item} />)}</g>
        <g className="board-label-layer">{board.items.map((item) => <g key={item.item_id}><rect x={item.label_area.x} y={item.label_area.y} width={item.label_area.width} height={item.label_area.height} rx="5" /><text x={item.label_area.x + item.label_area.width / 2} y={item.label_area.y + item.label_area.height / 2 + 6} textAnchor="middle">{item.label}</text></g>)}</g>
        <g className="mount-target-layer">{targets.map((target) => {
          const item = itemMap.get(target.socket_id)
          if (!item) return null
          const placement = placementBySocket.get(target.socket_id)
          const device = placement ? deviceMap.get(placement.mount_device_id) : undefined
          const selected = Boolean(device && device.mount_device_id === selectedDeviceId)
          const status = resultClass(target, placement, result)
          return <g
            key={target.socket_id}
            className={`mount-target${selected ? ' selected' : ''}${target.enabled ? '' : ' disabled'}${status}`}
            role="button" tabIndex={target.enabled ? 0 : -1}
            aria-label={device ? `${target.socket_id} 소켓에 장착된 ${device.label}` : `${target.socket_id} 빈 장착 소켓`}
            onClick={(event) => { event.stopPropagation(); if (target.enabled) onTargetClick(target.socket_id) }}
            onKeyDown={(event) => { if (target.enabled && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onTargetClick(target.socket_id) } }}
            onDragOver={(event) => { if (target.enabled) event.preventDefault() }}
            onDrop={(event) => { event.preventDefault(); event.stopPropagation(); const deviceId = event.dataTransfer.getData('text/plain'); if (deviceId && target.enabled) onDropDevice(deviceId, target.socket_id) }}
          >
            <rect className="mount-target-focus" x={item.x + 8} y={item.y + 8} width={item.width - 16} height={item.height - 16} rx="10" />
            {device ? <MountedDeviceGraphic item={item} device={device} /> : <g className="empty-mount-target"><rect x={item.label_area.x - 4} y={item.label_area.y - 4} width={item.label_area.width + 8} height={item.label_area.height + 8} rx="7" /><text x={item.x + item.width / 2} y={item.y + item.height / 2 + 5} textAnchor="middle">장착 위치</text></g>}
          </g>
        })}</g>
      </g>
    </svg>
  </div>
}
