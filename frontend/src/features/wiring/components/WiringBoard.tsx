import type { BoardDefinition, BoardItem, BoardPin, ExternalWiringDevice, WiringConnection } from '../../../api/client'
import { routeConnections } from '../engine/orthogonalRouter'

export const WIRE_COLORS = { brown: '#7a3f25', black: '#171b22', gray: '#77808a', yellow: '#e0a500' }

export const DEVICE_SUMMARY_COLORS: Record<string, string> = {
  MCCB: '#dc2626',
  EOCR: '#f97316',
  F: '#eab308',
  FUSE: '#eab308',
  X1: '#16a34a',
  X2: '#0891b2',
  T2: '#2563eb',
  MC1: '#7c3aed',
  MC2: '#db2777',
  T1: '#334155',
  TB5: '#0f766e',
  TB6: '#92400e',
}

export function deviceSummaryColor(itemId: string) {
  return DEVICE_SUMMARY_COLORS[itemId] ?? '#64748b'
}

export function terminalSlotLabel(terminalId: string) {
  const value = terminalId.split('-').at(-1) ?? terminalId
  return value.replace(/^0+(?=\d)/, '')
}

function pinSlotLabel(pin: BoardPin | undefined, terminalId: string) {
  // 보드 슬롯만 접두어를 제거한다. 외부 기구선은 PB0-1, M1-U처럼 ID를 유지한다.
  if (!pin) return terminalId
  const label = pin.label?.trim()
  if (label && label !== terminalId) return terminalSlotLabel(label)
  return pin.number == null ? terminalSlotLabel(terminalId) : String(pin.number)
}

export function buildTerminalSummary(board: BoardDefinition, connections: WiringConnection[]) {
  const ownerByTerminal = new Map<string, BoardItem>()
  const pinByTerminal = new Map<string, BoardPin>()
  board.items.forEach((item) => item.pins.forEach((pin) => { ownerByTerminal.set(pin.terminal_id, item); pinByTerminal.set(pin.terminal_id, pin) }))
  const summary = new Map<string, { other: string; slot: string; color: string; connectionIndex: number }[]>()
  connections.forEach((connection, connectionIndex) => {
    const fromOwner = ownerByTerminal.get(connection.from)
    const toOwner = ownerByTerminal.get(connection.to)
    summary.set(connection.from, [...(summary.get(connection.from) ?? []), { other: connection.to, slot: pinSlotLabel(pinByTerminal.get(connection.to), connection.to), color: deviceSummaryColor(toOwner?.item_id ?? connection.to.split('-')[0]), connectionIndex }])
    summary.set(connection.to, [...(summary.get(connection.to) ?? []), { other: connection.from, slot: pinSlotLabel(pinByTerminal.get(connection.from), connection.from), color: deviceSummaryColor(fromOwner?.item_id ?? connection.from.split('-')[0]), connectionIndex }])
  })
  return summary
}

export function summaryLabelY(pin: BoardPin) {
  return pin.side === 'top' ? pin.y - 18 : pin.y + 31
}

export function BoardItemBody({ item }: { item: BoardItem }) {
  if (item.item_type === 'terminal_block') {
    return <g className="board-item-body terminal-block-body"><rect x={item.x} y={item.y} width={item.width} height={item.height} rx="5" />{item.pins.map((pin) => <rect key={pin.terminal_id} x={pin.x - 16} y={item.y + 8} width="32" height={item.height - 16} rx="2" />)}</g>
  }
  if (item.item_type === 'socket_8p' || item.item_type === 'socket_12p') {
    const circular = item.item_type === 'socket_12p'
    return <g className="board-item-body socket-body-svg"><rect x={item.x} y={item.y} width={item.width} height={item.height} rx="6" /><circle cx={item.x + item.width / 2} cy={item.y + item.height / 2} r={Math.min(item.width, item.height) * .25} className={circular ? 'circular-center' : 'octal-center'} /><circle cx={item.x + item.width / 2} cy={item.y + item.height / 2} r="13" /><circle cx={item.x + 18} cy={item.y + item.height / 2} r="7" /><circle cx={item.x + item.width - 18} cy={item.y + item.height / 2} r="7" /></g>
  }
  return <g className="board-item-body component-body"><rect x={item.x} y={item.y} width={item.width} height={item.height} rx="5" /><line x1={item.x + 15} y1={item.y + item.height / 2} x2={item.x + item.width - 15} y2={item.y + item.height / 2} /></g>
}

function Pin({ pin, selected, summary, summarySelected, connectionCount, onClick, onPointerDown, onPointerUp, onExternalDrop, onSummarySelect }: { pin: BoardPin; selected: boolean; summary?: { other: string; slot: string; color: string; connectionIndex: number }[]; summarySelected: boolean; connectionCount: number; onClick: () => void; onPointerDown: () => void; onPointerUp: () => void; onExternalDrop: (externalId: string) => void; onSummarySelect: (terminalId: string, connectionIndices: number[]) => void }) {
  const labelY = pin.side === 'top' ? pin.y + 25 : pin.y - 16
  const roleY = pin.side === 'top' ? pin.y + 39 : pin.y - 31
  const summaryY = summaryLabelY(pin)
  const primary = summary?.[0]
  const summaryWidth = (primary?.slot.length ?? 0) > 3 ? 58 : 32
  const extraCount = Math.max(0, (summary?.length ?? 0) - 1)
  const summaryAriaLabel = summary?.length === 1
    ? `${pin.terminal_id}에서 ${primary?.other}로 연결된 요약 표시`
    : `${pin.terminal_id}에서 ${summary?.map((item) => item.other).join(', ')}로 연결된 요약 표시`
  return <g className={`board-pin${selected ? ' selected' : ''}${pin.enabled ? '' : ' disabled'}`} role="button" tabIndex={pin.enabled ? 0 : -1} aria-label={`${pin.terminal_id} 단자`} aria-description={`${connectionCount} / ${pin.max_connections} 연결`} onClick={(event) => { event.stopPropagation(); if (pin.enabled) onClick() }} onPointerDown={(event) => { event.stopPropagation(); if (pin.enabled) onPointerDown() }} onPointerUp={(event) => { event.stopPropagation(); if (pin.enabled) onPointerUp() }} onDragOver={(event) => { if (pin.terminal_role === 'free_junction' || pin.terminal_id.startsWith('TB5-') || pin.terminal_id.startsWith('TB6-')) event.preventDefault() }} onDrop={(event) => { event.preventDefault(); event.stopPropagation(); const id = event.dataTransfer.getData('application/x-electrician-terminal'); if (id) onExternalDrop(id) }} onKeyDown={(event) => { if (pin.enabled && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onClick() } }}>
    <circle cx={pin.x} cy={pin.y} r="13" /><circle cx={pin.x} cy={pin.y} r="5" />
    <text x={pin.x} y={labelY} textAnchor="middle">{pin.label}</text>
    {pin.role_label && <text className="board-pin-role" x={pin.x} y={roleY} textAnchor="middle">{pin.role_label}</text>}
    {(selected || connectionCount >= 2) && <g className="pin-capacity" transform={`translate(${pin.x + 16} ${pin.y - 15})`}><rect x="0" y="-10" width="30" height="15" rx="7" /><text x="15" y="1" textAnchor="middle">{connectionCount}/{pin.max_connections}</text></g>}
    {primary && summary && <g className={`pin-summary${summarySelected ? ' selected' : ''}`} role="button" tabIndex={0} aria-label={summaryAriaLabel} transform={`translate(${pin.x} ${summaryY})`} onClick={(event) => { event.stopPropagation(); onSummarySelect(pin.terminal_id, summary.map((item) => item.connectionIndex)) }} onPointerDown={(event) => event.stopPropagation()} onPointerUp={(event) => event.stopPropagation()} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.stopPropagation(); onSummarySelect(pin.terminal_id, summary.map((item) => item.connectionIndex)) } }}><rect x={-summaryWidth / 2} y="-10" width={summaryWidth} height="20" rx="4" style={{ stroke: primary.color }} /><circle cx={-summaryWidth / 2 + 6} cy="0" r="3.5" style={{ fill: primary.color }} /><text x="3" y="3.5" textAnchor="middle">{primary.slot}</text>{extraCount > 0 && <g className="pin-summary-count"><rect x={summaryWidth / 2 - 8} y="-19" width="24" height="13" rx="6" style={{ stroke: summary[1]?.color ?? primary.color }} /><text x={summaryWidth / 2 + 4} y="-9.5" textAnchor="middle">+{extraCount}</text></g>}</g>}
  </g>
}

export function WiringBoard({ board, connections, externalDevices, mode, selectedPin, selectedWire, selectedSummaryTerminal, zoom, onPinClick, onPinPointerDown, onPinPointerUp, onExternalDrop, onWireSelect, onSummarySelect, onClearSelection }: {
  board: BoardDefinition; connections: WiringConnection[]; mode: 'graphic' | 'summary'; selectedPin: string | null; selectedWire: number | null; selectedSummaryTerminal: string | null; zoom: number
  externalDevices?: ExternalWiringDevice[]; onPinClick: (id: string) => void; onPinPointerDown: (id: string) => void; onPinPointerUp: (id: string) => void; onExternalDrop: (externalId: string, targetId: string) => void; onWireSelect: (index: number) => void; onSummarySelect: (terminalId: string, connectionIndices: number[]) => void; onClearSelection: () => void
}) {
  const boardTerminals = new Set(board.items.flatMap((item) => item.pins.map((pin) => pin.terminal_id)))
  const routed = routeConnections(board, connections.filter((item) => boardTerminals.has(item.from) && boardTerminals.has(item.to)))
  const summary = buildTerminalSummary(board, connections)
  const counts = new Map<string, number>()
  connections.forEach((item) => { counts.set(item.from, (counts.get(item.from) ?? 0) + 1); counts.set(item.to, (counts.get(item.to) ?? 0) + 1) })
  const externalIds = new Set((externalDevices ?? []).flatMap((device) => device.terminals.map((terminal) => terminal.terminal_id)))
  const externalWires = connections.flatMap((connection, connectionIndex) => {
    const externalId = externalIds.has(connection.from) ? connection.from : externalIds.has(connection.to) ? connection.to : null
    const boardId = externalId === connection.from ? connection.to : connection.from
    if (!externalId || !boardTerminals.has(boardId)) return []
    const owner = board.items.find((item) => item.pins.some((pin) => pin.terminal_id === boardId))!
    const pin = owner.pins.find((item) => item.terminal_id === boardId)!
    const isTop = owner.item_id === 'TB5'
    const edgeY = isTop ? owner.y : owner.y + owner.height
    const endY = isTop ? Math.max(10, edgeY - 34) : Math.min(board.height - 10, edgeY + 34)
    return [{ connection, connectionIndex, externalId, points: `${pin.x},${edgeY} ${pin.x},${endY}`, labelX: pin.x, labelY: isTop ? endY - 3 : endY + 12 }]
  })
  return <div className="wiring-board-scroll">
    <svg className="wiring-board" role="img" aria-label="제어함 결선판" viewBox={`0 0 ${board.width} ${board.height}`} onClick={onClearSelection}>
      <g transform={`translate(${board.width * (1 - zoom) / 2} ${board.height * (1 - zoom) / 2}) scale(${zoom})`}>
        <rect className="board-background" x="4" y="4" width={board.width - 8} height={board.height - 8} rx="8" />
        <g className="routing-channel-layer">{board.routing_channels.map((channel) => <rect key={channel.channel_id} className={channel.channel_type} x={channel.x} y={channel.y} width={channel.width} height={channel.height} />)}</g>
        <g className="board-item-layer">{board.items.map((item) => <BoardItemBody key={item.item_id} item={item} />)}</g>
        {mode === 'graphic' && <g className="wire-layer">{routed.map((wire) => { const connectionIndex = connections.findIndex((item) => [item.from, item.to].sort().join('|') === [wire.from, wire.to].sort().join('|')); const points = wire.points.map((point) => `${point.x},${point.y}`).join(' '); const selected = selectedWire === connectionIndex; return <g key={`${wire.from}|${wire.to}`} className={`board-wire editable${selected ? ' selected' : ''}`} role="button" tabIndex={0} aria-label={`${wire.from}에서 ${wire.to}로 연결된 전선`} onClick={(event) => { event.stopPropagation(); onWireSelect(connectionIndex) }} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onWireSelect(connectionIndex) } }}>{selected && <polyline className="wire-selection-halo" points={points} />}<polyline className="wire-visible" points={points} style={{ stroke: WIRE_COLORS[wire.wire_color] }} /><polyline className="wire-hit" points={points} /></g> })}{externalWires.map((wire) => { const boardId = wire.externalId === wire.connection.from ? wire.connection.to : wire.connection.from; const selected = selectedWire === wire.connectionIndex; return <g key={`${wire.externalId}-${wire.connectionIndex}`} className={`board-wire external${selected ? ' selected' : ''}`} role="button" tabIndex={0} aria-label={`${wire.externalId}에서 ${boardId}로 연결된 전선`} onClick={(event) => { event.stopPropagation(); onWireSelect(wire.connectionIndex) }} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onWireSelect(wire.connectionIndex) } }}>{selected && <polyline className="wire-selection-halo" points={wire.points} />}<polyline className="wire-visible" points={wire.points} style={{ stroke: WIRE_COLORS[wire.connection.wire_color] }} /><polyline className="wire-hit" points={wire.points} /><text className="external-wire-label" x={wire.labelX} y={wire.labelY} textAnchor="middle">{wire.externalId}</text></g> })}</g>}
        <g className="board-pin-layer">{board.items.flatMap((item) => item.pins.map((pin) => { const pinSummary = mode === 'summary' ? summary.get(pin.terminal_id) : undefined; return <Pin key={pin.terminal_id} pin={pin} selected={selectedPin === pin.terminal_id} summary={pinSummary} summarySelected={selectedSummaryTerminal === pin.terminal_id || Boolean(pinSummary?.some((item) => item.connectionIndex === selectedWire))} connectionCount={counts.get(pin.terminal_id) ?? 0} onClick={() => onPinClick(pin.terminal_id)} onPointerDown={() => onPinPointerDown(pin.terminal_id)} onPointerUp={() => onPinPointerUp(pin.terminal_id)} onExternalDrop={(externalId) => onExternalDrop(externalId, pin.terminal_id)} onSummarySelect={onSummarySelect} /> }))}</g>
        <g className="board-label-layer">{board.items.map((item) => <g key={item.item_id}><rect x={item.label_area.x} y={item.label_area.y} width={item.label_area.width} height={item.label_area.height} rx="5" style={mode === 'summary' ? { stroke: deviceSummaryColor(item.item_id) } : undefined} />{mode === 'summary' && <circle className="device-color-dot" cx={item.label_area.x + 11} cy={item.label_area.y + item.label_area.height / 2} r="5" style={{ fill: deviceSummaryColor(item.item_id) }} />}<text x={item.label_area.x + item.label_area.width / 2} y={item.label_area.y + item.label_area.height / 2 + 6} textAnchor="middle">{item.label}</text></g>)}</g>
      </g>
    </svg>
  </div>
}
