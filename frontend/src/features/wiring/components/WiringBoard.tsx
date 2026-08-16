import type { BoardDefinition, BoardItem, BoardPin, WiringConnection } from '../../../api/client'
import { routeConnections } from '../engine/orthogonalRouter'

const wireColors = { brown: '#7a3f25', black: '#171b22', gray: '#77808a', yellow: '#e0a500' }

function ItemBody({ item }: { item: BoardItem }) {
  if (item.item_type === 'terminal_block') {
    return <g className="board-item-body terminal-block-body"><rect x={item.x} y={item.y} width={item.width} height={item.height} rx="5" />{item.pins.map((pin) => <rect key={pin.terminal_id} x={pin.x - 16} y={item.y + 8} width="32" height={item.height - 16} rx="2" />)}</g>
  }
  if (item.item_type === 'socket_8p' || item.item_type === 'socket_12p') {
    const circular = item.item_type === 'socket_12p'
    return <g className="board-item-body socket-body-svg"><rect x={item.x} y={item.y} width={item.width} height={item.height} rx="6" /><circle cx={item.x + item.width / 2} cy={item.y + item.height / 2} r={Math.min(item.width, item.height) * .25} className={circular ? 'circular-center' : 'octal-center'} /><circle cx={item.x + item.width / 2} cy={item.y + item.height / 2} r="13" /><circle cx={item.x + 18} cy={item.y + item.height / 2} r="7" /><circle cx={item.x + item.width - 18} cy={item.y + item.height / 2} r="7" /></g>
  }
  return <g className="board-item-body component-body"><rect x={item.x} y={item.y} width={item.width} height={item.height} rx="5" /><line x1={item.x + 15} y1={item.y + item.height / 2} x2={item.x + item.width - 15} y2={item.y + item.height / 2} /></g>
}

function Pin({ pin, selected, summary, onClick, onPointerDown, onPointerUp }: { pin: BoardPin; selected: boolean; summary?: { other: string; color: string }; onClick: () => void; onPointerDown: () => void; onPointerUp: () => void }) {
  const labelY = pin.side === 'top' ? pin.y + 25 : pin.y - 16
  const summaryY = pin.side === 'top' ? pin.y - 18 : pin.y + 31
  return <g className={`board-pin${selected ? ' selected' : ''}${pin.enabled ? '' : ' disabled'}`} role="button" tabIndex={pin.enabled ? 0 : -1} aria-label={`${pin.terminal_id} 단자`} onClick={(event) => { event.stopPropagation(); if (pin.enabled) onClick() }} onPointerDown={(event) => { event.stopPropagation(); if (pin.enabled) onPointerDown() }} onPointerUp={(event) => { event.stopPropagation(); if (pin.enabled) onPointerUp() }} onKeyDown={(event) => { if (pin.enabled && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onClick() } }}>
    <circle cx={pin.x} cy={pin.y} r="13" /><circle cx={pin.x} cy={pin.y} r="5" />
    <text x={pin.x} y={labelY} textAnchor="middle">{pin.label}</text>
    {summary && <g className="pin-summary" transform={`translate(${pin.x} ${summaryY})`}><rect x="-39" y="-12" width="78" height="23" rx="4" style={{ stroke: summary.color }} /><circle cx="-28" cy="0" r="5" style={{ fill: summary.color }} /><text x="-18" y="4">{summary.other}</text></g>}
  </g>
}

export function WiringBoard({ board, connections, mode, selectedPin, selectedWire, zoom, onPinClick, onPinPointerDown, onPinPointerUp, onWireSelect, onClearSelection }: {
  board: BoardDefinition; connections: WiringConnection[]; mode: 'graphic' | 'summary'; selectedPin: string | null; selectedWire: number | null; zoom: number
  onPinClick: (id: string) => void; onPinPointerDown: (id: string) => void; onPinPointerUp: (id: string) => void; onWireSelect: (index: number) => void; onClearSelection: () => void
}) {
  const routed = routeConnections(board, connections)
  const summary = new Map<string, { other: string; color: string }>()
  connections.forEach((connection) => { summary.set(connection.from, { other: connection.to, color: connection.pair_display_color }); summary.set(connection.to, { other: connection.from, color: connection.pair_display_color }) })
  return <div className="wiring-board-scroll">
    <svg className="wiring-board" role="img" aria-label="제어함 결선판" viewBox={`0 0 ${board.width} ${board.height}`} onClick={onClearSelection}>
      <g transform={`translate(${board.width * (1 - zoom) / 2} ${board.height * (1 - zoom) / 2}) scale(${zoom})`}>
        <rect className="board-background" x="4" y="4" width={board.width - 8} height={board.height - 8} rx="8" />
        <g className="routing-channel-layer">{board.routing_channels.map((channel) => <rect key={channel.channel_id} className={channel.channel_type} x={channel.x} y={channel.y} width={channel.width} height={channel.height} />)}</g>
        <g className="board-item-layer">{board.items.map((item) => <ItemBody key={item.item_id} item={item} />)}</g>
        {mode === 'graphic' && <g className="wire-layer">{routed.map((wire, index) => <g key={`${wire.from}|${wire.to}`} className={`board-wire${selectedWire === index ? ' selected' : ''}`} role="button" tabIndex={0} aria-label={`${wire.from}에서 ${wire.to}로 연결된 전선`} onClick={(event) => { event.stopPropagation(); onWireSelect(index) }} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onWireSelect(index) } }}><polyline points={wire.points.map((point) => `${point.x},${point.y}`).join(' ')} style={{ stroke: wireColors[wire.wire_color] }} /><polyline className="wire-hit" points={wire.points.map((point) => `${point.x},${point.y}`).join(' ')} /></g>)}</g>}
        <g className="board-pin-layer">{board.items.flatMap((item) => item.pins.map((pin) => <Pin key={pin.terminal_id} pin={pin} selected={selectedPin === pin.terminal_id} summary={mode === 'summary' ? summary.get(pin.terminal_id) : undefined} onClick={() => onPinClick(pin.terminal_id)} onPointerDown={() => onPinPointerDown(pin.terminal_id)} onPointerUp={() => onPinPointerUp(pin.terminal_id)} />))}</g>
        <g className="board-label-layer">{board.items.map((item) => <g key={item.item_id}><rect x={item.label_area.x} y={item.label_area.y} width={item.label_area.width} height={item.label_area.height} rx="5" /><text x={item.label_area.x + item.label_area.width / 2} y={item.label_area.y + item.label_area.height / 2 + 6} textAnchor="middle">{item.label}</text></g>)}</g>
      </g>
    </svg>
  </div>
}
