import type { BoardDefinition, BoardItem, WiringConnection } from '../../../api/client'

export const WIRE_COLORS = { brown: '#7a3f25', black: '#171b22', gray: '#77808a', yellow: '#e0a500' }

export type ExternalWireLayout = {
  connection: WiringConnection
  connectionIndex: number
  externalTerminalId: string
  boardTerminalId: string
  points: string
  labelX: number
  labelY: number
  labelAnchor: 'start' | 'middle' | 'end'
}

export function boardItemLabelArea(item: BoardItem) {
  if (item.item_type !== 'terminal_block') return item.label_area
  const width = Math.min(item.label_area.width, 220)
  const height = Math.min(item.label_area.height, 24)
  const topPinCount = item.pins.filter((pin) => pin.side === 'top').length
  const y = topPinCount > item.pins.length / 2
    ? item.y + item.height - height - 3
    : item.y + 3
  return { x: item.x + (item.width - width) / 2, y, width, height }
}

export function buildExternalWireLayouts(
  board: BoardDefinition,
  connections: WiringConnection[],
  externalTerminalIds?: ReadonlySet<string>,
): ExternalWireLayout[] {
  const terminalOwners = new Map<string, { item: BoardItem; pinX: number }>()
  board.items.forEach((item) => item.pins.forEach((pin) => {
    terminalOwners.set(pin.terminal_id, { item, pinX: pin.x })
  }))

  const candidates = connections.flatMap((connection, connectionIndex) => {
    const fromOnBoard = terminalOwners.has(connection.from)
    const toOnBoard = terminalOwners.has(connection.to)
    let externalTerminalId: string | undefined
    let boardTerminalId: string | undefined

    if (externalTerminalIds) {
      if (externalTerminalIds.has(connection.from) && toOnBoard) {
        externalTerminalId = connection.from
        boardTerminalId = connection.to
      } else if (externalTerminalIds.has(connection.to) && fromOnBoard) {
        externalTerminalId = connection.to
        boardTerminalId = connection.from
      }
    } else if (fromOnBoard !== toOnBoard) {
      boardTerminalId = fromOnBoard ? connection.from : connection.to
      externalTerminalId = fromOnBoard ? connection.to : connection.from
    }

    if (!externalTerminalId || !boardTerminalId) return []
    const owner = terminalOwners.get(boardTerminalId)
    if (!owner || owner.item.item_type !== 'terminal_block') return []
    return [{ connection, connectionIndex, externalTerminalId, boardTerminalId, ...owner }]
  })

  const groups = new Map<string, typeof candidates>()
  candidates.forEach((candidate) => groups.set(candidate.boardTerminalId, [
    ...(groups.get(candidate.boardTerminalId) ?? []), candidate,
  ]))

  const layouts: ExternalWireLayout[] = []
  groups.forEach((group) => {
    const ordered = [...group].sort((left, right) => (
      left.externalTerminalId.localeCompare(right.externalTerminalId, 'en')
      || left.connectionIndex - right.connectionIndex
    ))
    ordered.forEach((candidate, index) => {
      const offset = ordered.length === 1 ? 0 : (index - (ordered.length - 1) / 2) * 14
      const exitsTop = candidate.item.item_id === 'TB5'
        ? true
        : candidate.item.item_id === 'TB6'
          ? false
          : candidate.item.pins.some((pin) => pin.terminal_id === candidate.boardTerminalId && pin.side === 'bottom')
      const edgeY = exitsTop ? candidate.item.y : candidate.item.y + candidate.item.height
      const endY = exitsTop ? Math.max(10, edgeY - 34) : Math.min(board.height - 10, edgeY + 34)
      const wireX = candidate.pinX + offset
      const labelAnchor = offset < 0 ? 'end' : offset > 0 ? 'start' : 'middle'
      const labelX = wireX + (offset < 0 ? -3 : offset > 0 ? 3 : 0)
      layouts.push({
        connection: candidate.connection,
        connectionIndex: candidate.connectionIndex,
        externalTerminalId: candidate.externalTerminalId,
        boardTerminalId: candidate.boardTerminalId,
        points: `${wireX},${edgeY} ${wireX},${endY}`,
        labelX,
        labelY: exitsTop ? endY - 3 : endY + 12,
        labelAnchor,
      })
    })
  })
  return layouts.sort((left, right) => left.connectionIndex - right.connectionIndex)
}
