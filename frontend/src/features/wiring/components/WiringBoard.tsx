import type { BoardDefinition, BoardItem, BoardPin, ExternalWiringDevice, FreeCircuitMountingSlot, WiringConnection } from '../../../api/client'
import { boardItemLabelArea, buildExternalWireLayouts, WIRE_COLORS } from '../engine/boardGeometry'
import { routeConnections } from '../engine/orthogonalRouter'
import { isFreeJunction, terminalBlockUsage, type TerminalBlockUsage } from '../engine/terminalCapacity'

export { boardItemLabelArea, buildExternalWireLayouts, WIRE_COLORS } from '../engine/boardGeometry'

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

export function isDualFuseBoardItem(item: BoardItem) {
  if (item.item_type !== 'component') return false
  const suffixes = new Set(item.pins.map((pin) => terminalSlotLabel(pin.terminal_id)))
  return item.pins.length === 4 && ['1', '2', '3', '4'].every((suffix) => suffixes.has(suffix))
    && (item.item_id === 'F' || /^F\d*$/.test(item.item_id) || /FUSE/i.test(item.label))
}

function DualFuseBody({ item }: { item: BoardItem }) {
  const bySuffix = new Map(item.pins.map((pin) => [terminalSlotLabel(pin.terminal_id), pin]))
  const leftTop = bySuffix.get('1')
  const leftBottom = bySuffix.get('2')
  const rightTop = bySuffix.get('3')
  const rightBottom = bySuffix.get('4')
  if (!leftTop || !leftBottom || !rightTop || !rightBottom) return null

  const cartridgeTop = item.y + item.height * .28
  const cartridgeBottom = item.y + item.height * .72
  const cartridgeHeight = cartridgeBottom - cartridgeTop
  const cartridgeWidth = Math.min(26, item.width * .22)
  const channel = (key: string, x: number, topPinY: number, bottomPinY: number) => <g key={key} className="dual-fuse-channel">
    <line className="dual-fuse-lead" x1={x} y1={topPinY} x2={x} y2={cartridgeTop} />
    <rect className="dual-fuse-clip" x={x - cartridgeWidth * .42} y={cartridgeTop - 5} width={cartridgeWidth * .84} height="9" rx="2" />
    <rect className="dual-fuse-cartridge" x={x - cartridgeWidth / 2} y={cartridgeTop} width={cartridgeWidth} height={cartridgeHeight} rx={cartridgeWidth / 2} />
    <rect className="dual-fuse-cartridge-core" x={x - cartridgeWidth * .28} y={cartridgeTop + 7} width={cartridgeWidth * .56} height={Math.max(10, cartridgeHeight - 14)} rx={cartridgeWidth * .28} />
    <rect className="dual-fuse-clip" x={x - cartridgeWidth * .42} y={cartridgeBottom - 4} width={cartridgeWidth * .84} height="9" rx="2" />
    <line className="dual-fuse-lead" x1={x} y1={cartridgeBottom} x2={x} y2={bottomPinY} />
  </g>

  return <g className="board-item-body dual-fuse-body">
    <rect className="dual-fuse-holder" x={item.x} y={item.y} width={item.width} height={item.height} rx="7" />
    <rect className="dual-fuse-recess" x={item.x + 10} y={item.y + 14} width={item.width - 20} height={item.height - 28} rx="6" />
    {channel('left', leftTop.x, leftTop.y, leftBottom.y)}
    {channel('right', rightTop.x, rightTop.y, rightBottom.y)}
  </g>
}

export function BoardItemBody({ item }: { item: BoardItem }) {
  if (isDualFuseBoardItem(item)) return <DualFuseBody item={item} />
  if (item.item_type === 'terminal_block') {
    return <g className="board-item-body terminal-block-body"><rect x={item.x} y={item.y} width={item.width} height={item.height} rx="5" />{item.pins.map((pin) => <rect key={pin.terminal_id} x={pin.x - 16} y={item.y + 8} width="32" height={item.height - 16} rx="2" />)}</g>
  }
  if (item.item_type === 'socket_8p' || item.item_type === 'socket_12p') {
    const circular = item.item_type === 'socket_12p'
    return <g className="board-item-body socket-body-svg"><rect x={item.x} y={item.y} width={item.width} height={item.height} rx="6" /><circle cx={item.x + item.width / 2} cy={item.y + item.height / 2} r={Math.min(item.width, item.height) * .25} className={circular ? 'circular-center' : 'octal-center'} /><circle cx={item.x + item.width / 2} cy={item.y + item.height / 2} r="13" /><circle cx={item.x + 18} cy={item.y + item.height / 2} r="7" /><circle cx={item.x + item.width - 18} cy={item.y + item.height / 2} r="7" /></g>
  }
  return <g className="board-item-body component-body"><rect x={item.x} y={item.y} width={item.width} height={item.height} rx="5" /><line x1={item.x + 15} y1={item.y + item.height / 2} x2={item.x + item.width - 15} y2={item.y + item.height / 2} /></g>
}

function Pin({ pin, selected, summary, summarySelected, connectionCount, terminalBlockConnectionUsage, onClick, onPointerDown, onPointerUp, onExternalDrop, onSummarySelect }: { pin: BoardPin; selected: boolean; summary?: { other: string; slot: string; color: string; connectionIndex: number }[]; summarySelected: boolean; connectionCount: number; terminalBlockConnectionUsage?: TerminalBlockUsage; onClick: () => void; onPointerDown: () => void; onPointerUp: () => void; onExternalDrop: (externalId: string) => void; onSummarySelect: (terminalId: string, connectionIndices: number[]) => void }) {
  const labelY = pin.side === 'top' ? pin.y + 25 : pin.y - 16
  const roleY = pin.side === 'top' ? pin.y + 39 : pin.y - 31
  const summaryY = summaryLabelY(pin)
  const primary = summary?.[0]
  const summaryWidth = (primary?.slot.length ?? 0) > 3 ? 58 : 32
  const extraCount = Math.max(0, (summary?.length ?? 0) - 1)
  const summaryAriaLabel = summary?.length === 1
    ? `${pin.terminal_id}에서 ${primary?.other}로 연결된 요약 표시`
    : `${pin.terminal_id}에서 ${summary?.map((item) => item.other).join(', ')}로 연결된 요약 표시`
  const full = terminalBlockConnectionUsage
    ? terminalBlockConnectionUsage.external >= pin.max_connections || terminalBlockConnectionUsage.internal >= pin.max_connections
    : connectionCount >= pin.max_connections
  return <g className={`board-pin${selected ? ' selected' : ''}${pin.enabled ? '' : ' disabled'}`} role="button" tabIndex={pin.enabled ? 0 : -1} aria-label={`${pin.terminal_id} 단자`} aria-description={terminalBlockConnectionUsage ? `외부측 ${terminalBlockConnectionUsage.external} / ${pin.max_connections}, 내부측 ${terminalBlockConnectionUsage.internal} / ${pin.max_connections} 연결` : `${connectionCount} / ${pin.max_connections} 연결`} onClick={(event) => { event.stopPropagation(); if (pin.enabled) onClick() }} onPointerDown={(event) => { event.stopPropagation(); if (pin.enabled) onPointerDown() }} onPointerUp={(event) => { event.stopPropagation(); if (pin.enabled) onPointerUp() }} onDragOver={(event) => { if (pin.terminal_role === 'free_junction' || pin.terminal_id.startsWith('TB5-') || pin.terminal_id.startsWith('TB6-')) event.preventDefault() }} onDrop={(event) => { event.preventDefault(); event.stopPropagation(); const id = event.dataTransfer.getData('application/x-electrician-terminal'); if (id) onExternalDrop(id) }} onKeyDown={(event) => { if (pin.enabled && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onClick() } }}>
    <circle cx={pin.x} cy={pin.y} r="13" /><circle cx={pin.x} cy={pin.y} r="5" />
    <text x={pin.x} y={labelY} textAnchor="middle">{pin.label}</text>
    {pin.role_label && <text className="board-pin-role" x={pin.x} y={roleY} textAnchor="middle">{pin.role_label}</text>}
    {(selected || connectionCount >= 2 || full) && (terminalBlockConnectionUsage
      ? <g className="pin-capacity terminal-bank-capacity" transform={`translate(${pin.x + 16} ${pin.y - 21})`}><g><rect x="0" y="-10" width="34" height="14" rx="7" /><text x="17" y="0" textAnchor="middle">외{terminalBlockConnectionUsage.external}/{pin.max_connections}</text></g><g transform="translate(0 15)"><rect x="0" y="-10" width="34" height="14" rx="7" /><text x="17" y="0" textAnchor="middle">내{terminalBlockConnectionUsage.internal}/{pin.max_connections}</text></g></g>
      : <g className="pin-capacity" transform={`translate(${pin.x + 16} ${pin.y - 15})`}><rect x="0" y="-10" width="30" height="15" rx="7" /><text x="15" y="1" textAnchor="middle">{connectionCount}/{pin.max_connections}</text></g>)}
    {primary && summary && <g className={`pin-summary${summarySelected ? ' selected' : ''}`} role="button" tabIndex={0} aria-label={summaryAriaLabel} transform={`translate(${pin.x} ${summaryY})`} onClick={(event) => { event.stopPropagation(); onSummarySelect(pin.terminal_id, summary.map((item) => item.connectionIndex)) }} onPointerDown={(event) => event.stopPropagation()} onPointerUp={(event) => event.stopPropagation()} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); event.stopPropagation(); onSummarySelect(pin.terminal_id, summary.map((item) => item.connectionIndex)) } }}><rect x={-summaryWidth / 2} y="-10" width={summaryWidth} height="20" rx="4" style={{ stroke: primary.color }} /><circle cx={-summaryWidth / 2 + 6} cy="0" r="3.5" style={{ fill: primary.color }} /><text x="3" y="3.5" textAnchor="middle">{primary.slot}</text>{extraCount > 0 && <g className="pin-summary-count"><rect x={summaryWidth / 2 - 8} y="-19" width="24" height="13" rx="6" style={{ stroke: summary[1]?.color ?? primary.color }} /><text x={summaryWidth / 2 + 4} y="-9.5" textAnchor="middle">+{extraCount}</text></g>}</g>}
  </g>
}

export function WiringBoard({ board, connections, externalDevices, mode, selectedPin, selectedWire, selectedSummaryTerminal, zoom, mountingSlots, placementMode, selectedDeviceId, onMountingSlotClick, onDeviceSelect, onPinClick, onPinPointerDown, onPinPointerUp, onExternalDrop, onWireSelect, onSummarySelect, onClearSelection }: {
  board: BoardDefinition; connections: WiringConnection[]; mode: 'graphic' | 'summary'; selectedPin: string | null; selectedWire: number | null; selectedSummaryTerminal: string | null; zoom: number
  externalDevices?: ExternalWiringDevice[]; onPinClick: (id: string) => void; onPinPointerDown: (id: string) => void; onPinPointerUp: (id: string) => void; onExternalDrop: (externalId: string, targetId: string) => void; onWireSelect: (index: number) => void; onSummarySelect: (terminalId: string, connectionIndices: number[]) => void; onClearSelection: () => void
  mountingSlots?: FreeCircuitMountingSlot[]; placementMode?: boolean; selectedDeviceId?: string | null
  onMountingSlotClick?: (slot: FreeCircuitMountingSlot) => void; onDeviceSelect?: (instanceId: string) => void
}) {
  const boardTerminals = new Set(board.items.flatMap((item) => item.pins.map((pin) => pin.terminal_id)))
  const routed = routeConnections(board, connections.filter((item) => boardTerminals.has(item.from) && boardTerminals.has(item.to)))
  const summary = buildTerminalSummary(board, connections)
  const counts = new Map<string, number>()
  connections.forEach((item) => { counts.set(item.from, (counts.get(item.from) ?? 0) + 1); counts.set(item.to, (counts.get(item.to) ?? 0) + 1) })
  const externalIds = new Set((externalDevices ?? []).flatMap((device) => device.terminals.map((terminal) => terminal.terminal_id)))
  const externalWires = buildExternalWireLayouts(board, connections, externalIds)
  return <div className="wiring-board-scroll">
    <svg className="wiring-board" role="img" aria-label="제어함 결선판" viewBox={`0 0 ${board.width} ${board.height}`} onClick={onClearSelection}>
      <g transform={`translate(${board.width * (1 - zoom) / 2} ${board.height * (1 - zoom) / 2}) scale(${zoom})`}>
        <rect className="board-background" x="4" y="4" width={board.width - 8} height={board.height - 8} rx="8" />
        <g className="routing-channel-layer">{board.routing_channels.map((channel) => <rect key={channel.channel_id} className={channel.channel_type} x={channel.x} y={channel.y} width={channel.width} height={channel.height} />)}</g>
        {mountingSlots?.filter((slot) => slot.zone.startsWith('internal')).map((slot) => <rect key={slot.slot_id} className={`free-mounting-slot${placementMode ? ' active' : ''}`} x={slot.x} y={slot.y} width={slot.width} height={slot.height} rx="8" role="button" tabIndex={placementMode ? 0 : -1} aria-label={`${slot.zone} ${slot.column + 1}번 장착칸`} onClick={(event) => { if (!placementMode) return; event.stopPropagation(); onMountingSlotClick?.(slot) }} onKeyDown={(event) => { if (placementMode && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onMountingSlotClick?.(slot) } }} />)}
        <g className="board-item-layer">{board.items.map((item) => <g key={item.item_id} className={selectedDeviceId === item.item_id ? 'free-device selected' : 'free-device'} onClick={(event) => { if (item.item_type === 'terminal_block') return; event.stopPropagation(); onDeviceSelect?.(item.item_id) }}><BoardItemBody item={item} /></g>)}</g>
        {mode === 'graphic' && <g className="wire-layer">{routed.map((wire) => { const connectionIndex = connections.findIndex((item) => [item.from, item.to].sort().join('|') === [wire.from, wire.to].sort().join('|')); const points = wire.points.map((point) => `${point.x},${point.y}`).join(' '); const selected = selectedWire === connectionIndex; return <g key={`${wire.from}|${wire.to}`} className={`board-wire editable${selected ? ' selected' : ''}`} role="button" tabIndex={0} aria-label={`${wire.from}에서 ${wire.to}로 연결된 전선`} onClick={(event) => { event.stopPropagation(); onWireSelect(connectionIndex) }} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onWireSelect(connectionIndex) } }}>{selected && <polyline className="wire-selection-halo" points={points} />}<polyline className="wire-visible" points={points} style={{ stroke: WIRE_COLORS[wire.wire_color] }} /><polyline className="wire-hit" points={points} /></g> })}{externalWires.map((wire) => { const selected = selectedWire === wire.connectionIndex; return <g key={`${wire.externalTerminalId}-${wire.connectionIndex}`} className={`board-wire external editable${selected ? ' selected' : ''}`} role="button" tabIndex={0} aria-label={`${wire.externalTerminalId}에서 ${wire.boardTerminalId}로 연결된 전선`} onClick={(event) => { event.stopPropagation(); onWireSelect(wire.connectionIndex) }} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onWireSelect(wire.connectionIndex) } }}>{selected && <polyline className="wire-selection-halo" points={wire.points} />}<polyline className="wire-visible" points={wire.points} style={{ stroke: WIRE_COLORS[wire.connection.wire_color] }} /><polyline className="wire-hit" points={wire.points} /><text className="external-wire-label" x={wire.labelX} y={wire.labelY} textAnchor={wire.labelAnchor}>{wire.externalTerminalId}</text></g> })}</g>}
        <g className="board-pin-layer">{board.items.flatMap((item) => item.pins.map((pin) => { const pinSummary = mode === 'summary' ? summary.get(pin.terminal_id) : undefined; const usage = isFreeJunction(pin) ? terminalBlockUsage(connections, pin.terminal_id, externalIds) : undefined; return <Pin key={pin.terminal_id} pin={pin} selected={selectedPin === pin.terminal_id} summary={pinSummary} summarySelected={selectedSummaryTerminal === pin.terminal_id || Boolean(pinSummary?.some((item) => item.connectionIndex === selectedWire))} connectionCount={counts.get(pin.terminal_id) ?? 0} terminalBlockConnectionUsage={usage} onClick={() => onPinClick(pin.terminal_id)} onPointerDown={() => onPinPointerDown(pin.terminal_id)} onPointerUp={() => onPinPointerUp(pin.terminal_id)} onExternalDrop={(externalId) => onExternalDrop(externalId, pin.terminal_id)} onSummarySelect={onSummarySelect} /> }))}</g>
        <g className="board-label-layer">{board.items.map((item) => { const labelArea = boardItemLabelArea(item); return <g key={item.item_id} className={item.item_type === 'terminal_block' ? 'terminal-block-label' : undefined}><rect x={labelArea.x} y={labelArea.y} width={labelArea.width} height={labelArea.height} rx="5" style={mode === 'summary' ? { stroke: deviceSummaryColor(item.item_id) } : undefined} />{mode === 'summary' && <circle className="device-color-dot" cx={labelArea.x + 11} cy={labelArea.y + labelArea.height / 2} r="5" style={{ fill: deviceSummaryColor(item.item_id) }} />}<text x={labelArea.x + labelArea.width / 2} y={labelArea.y + labelArea.height / 2 + 5} textAnchor="middle">{item.label}</text></g> })}</g>
      </g>
    </svg>
  </div>
}
