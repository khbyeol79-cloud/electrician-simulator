import type { BoardDefinition, BoardItem, BoardPin, DiagramPoint, WiringConnection } from '../../../api/client'

export type RoutedWire = WiringConnection & { points: DiagramPoint[] }

function compact(points: DiagramPoint[]) {
  return points.filter((point, index) => index === 0 || point.x !== points[index - 1].x || point.y !== points[index - 1].y)
}

export function findPin(board: BoardDefinition, terminalId: string): { item: BoardItem; pin: BoardPin } | undefined {
  for (const item of board.items) {
    const pin = item.pins.find((candidate) => candidate.terminal_id === terminalId)
    if (pin) return { item, pin }
  }
}

export function isOrthogonal(points: DiagramPoint[]) {
  return points.slice(1).every((point, index) => point.x === points[index].x || point.y === points[index].y)
}

export function routeConnection(board: BoardDefinition, connection: WiringConnection, laneIndex = 0): RoutedWire {
  const start = findPin(board, connection.from)
  const end = findPin(board, connection.to)
  if (!start || !end) throw new Error('연결 단자의 좌표를 찾을 수 없습니다.')
  const lane = laneIndex * 7
  const escape = (pin: BoardPin) => ({ x: pin.x, y: pin.y + (pin.side === 'top' ? -(32 + lane) : 32 + lane) })
  const startExit = escape(start.pin)
  const endExit = escape(end.pin)
  let points: DiagramPoint[]
  if (start.item.row === end.item.row && start.pin.side === end.pin.side) {
    const channelY = start.pin.side === 'top' ? Math.min(startExit.y, endExit.y) : Math.max(startExit.y, endExit.y)
    points = [{ x: start.pin.x, y: start.pin.y }, startExit, { x: startExit.x, y: channelY }, { x: endExit.x, y: channelY }, endExit, { x: end.pin.x, y: end.pin.y }]
  } else {
    const leftX = board.routing_margin
    const rightX = board.width - board.routing_margin
    const leftCost = Math.abs(startExit.x - leftX) + Math.abs(endExit.x - leftX)
    const rightCost = Math.abs(startExit.x - rightX) + Math.abs(endExit.x - rightX)
    const outerX = leftCost <= rightCost ? leftX - lane : rightX + lane
    points = [{ x: start.pin.x, y: start.pin.y }, startExit, { x: outerX, y: startExit.y }, { x: outerX, y: endExit.y }, endExit, { x: end.pin.x, y: end.pin.y }]
  }
  const compacted = compact(points)
  if (!isOrthogonal(compacted)) throw new Error('직교 배선 경로를 만들 수 없습니다.')
  return { ...connection, points: compacted }
}

export function routeConnections(board: BoardDefinition, connections: WiringConnection[]) {
  return connections.map((connection, index) => routeConnection(board, connection, index % 5))
}
