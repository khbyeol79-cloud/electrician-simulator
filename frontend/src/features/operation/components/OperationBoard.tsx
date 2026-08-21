import type { PointerEventHandler } from 'react'
import type { BoardDefinition, BoardItem, FixedDevicePlacement, WiringConnection } from '../../../api/client'
import { MountedDeviceGraphic } from '../../mounting/components/MountingBoard'
import { BoardItemBody, WIRE_COLORS } from '../../wiring/components/WiringBoard'
import { routeConnections } from '../../wiring/engine/orthogonalRouter'

function StaticPins({ item }: { item: BoardItem }) {
  return <>{item.pins.map((pin) => {
    const labelY = pin.side === 'top' ? pin.y + 25 : pin.y - 16
    return <g key={pin.terminal_id} className={`board-pin static${pin.enabled ? '' : ' disabled'}`}>
      <circle cx={pin.x} cy={pin.y} r="13" /><circle cx={pin.x} cy={pin.y} r="5" />
      <text x={pin.x} y={labelY} textAnchor="middle">{pin.label}</text>
    </g>
  })}</>
}

export function OperationBoard({
  board, connections, placements, zoom, pan = { x: 0, y: 0 }, energizedSocketIds = new Set(), onPointerDown, onPointerMove, onPointerUp,
}: {
  board: BoardDefinition
  connections: WiringConnection[]
  placements: FixedDevicePlacement[]
  zoom: number
  pan?: { x: number; y: number }
  energizedSocketIds?: Set<string>
  onPointerDown?: PointerEventHandler<SVGSVGElement>
  onPointerMove?: PointerEventHandler<SVGSVGElement>
  onPointerUp?: PointerEventHandler<SVGSVGElement>
}) {
  const boardTerminalIds = new Set(board.items.flatMap((item) => item.pins.map((pin) => pin.terminal_id)))
  const internalConnections = connections.filter((connection) => boardTerminalIds.has(connection.from) && boardTerminalIds.has(connection.to))
  const routed = routeConnections(board, internalConnections)
  const itemMap = new Map(board.items.map((item) => [item.item_id, item]))
  const externalWires = connections.flatMap((connection, connectionIndex) => {
    const fromOnBoard = boardTerminalIds.has(connection.from)
    const toOnBoard = boardTerminalIds.has(connection.to)
    if (fromOnBoard === toOnBoard) return []
    const boardTerminalId = fromOnBoard ? connection.from : connection.to
    const externalTerminalId = fromOnBoard ? connection.to : connection.from
    const owner = board.items.find((item) => item.pins.some((pin) => pin.terminal_id === boardTerminalId))
    const pin = owner?.pins.find((candidate) => candidate.terminal_id === boardTerminalId)
    if (!owner || !pin || owner.item_type !== 'terminal_block') return []
    const exitsTop = pin.side === 'bottom'
    const edgeY = exitsTop ? owner.y : owner.y + owner.height
    const endY = exitsTop ? Math.max(10, edgeY - 34) : Math.min(board.height - 10, edgeY + 34)
    return [{ connection, connectionIndex, externalTerminalId, points: `${pin.x},${edgeY} ${pin.x},${endY}`, labelX: pin.x, labelY: exitsTop ? endY - 3 : endY + 12 }]
  })

  return <div className="wiring-board-scroll operation-board-scroll">
    <svg className="wiring-board mounting-board operation-board" role="img" aria-label="동작시험 준비 제어함" viewBox={`0 0 ${board.width} ${board.height}`} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}>
      <g transform={`translate(${board.width * (1 - zoom) / 2 + pan.x} ${board.height * (1 - zoom) / 2 + pan.y}) scale(${zoom})`}>
        <rect className="board-background" x="4" y="4" width={board.width - 8} height={board.height - 8} rx="8" />
        <g className="routing-channel-layer">{board.routing_channels.map((channel) => <rect key={channel.channel_id} className={channel.channel_type} x={channel.x} y={channel.y} width={channel.width} height={channel.height} />)}</g>
        <g className="board-item-layer">{board.items.map((item) => <BoardItemBody key={item.item_id} item={item} />)}</g>
        <g className="wire-layer readonly">{routed.map((wire) => {
          const points = wire.points.map((point) => `${point.x},${point.y}`).join(' ')
          return <g key={`${wire.from}|${wire.to}`} className="board-wire readonly"><polyline className="wire-depth" points={points} /><polyline className="wire-visible" points={points} style={{ stroke: WIRE_COLORS[wire.wire_color] }} /></g>
        })}{externalWires.map((wire) => <g key={`external-${wire.connectionIndex}`} className="board-wire readonly external"><polyline className="wire-depth" points={wire.points} /><polyline className="wire-visible" points={wire.points} style={{ stroke: WIRE_COLORS[wire.connection.wire_color] }} /><text className="external-wire-label" x={wire.labelX} y={wire.labelY} textAnchor="middle">{wire.externalTerminalId}</text></g>)}</g>
        <g className="board-pin-layer readonly">{board.items.map((item) => <StaticPins key={item.item_id} item={item} />)}</g>
        <g className="board-label-layer">{board.items.map((item) => <g key={item.item_id}><rect x={item.label_area.x} y={item.label_area.y} width={item.label_area.width} height={item.label_area.height} rx="5" /><text x={item.label_area.x + item.label_area.width / 2} y={item.label_area.y + item.label_area.height / 2 + 6} textAnchor="middle">{item.label}</text></g>)}</g>
        <g className="fixed-device-layer">{placements.map((placement) => {
          const item = itemMap.get(placement.socket_id)
          return item ? <g key={placement.mount_device_id} className={energizedSocketIds.has(placement.socket_id) ? 'fixed-device energized' : 'fixed-device'} aria-label={`${placement.label} 자동 삽입`}><MountedDeviceGraphic item={item} device={placement} />{energizedSocketIds.has(placement.socket_id) && <text className="device-on-badge" x={item.x + item.width - 18} y={item.y + 28}>ON</text>}</g> : null
        })}</g>
      </g>
    </svg>
  </div>
}
