import type {
  BoardDefinition,
  BoardItem,
  BoardPin,
  BoardRect,
  DiagramPoint,
  WiringConnection,
} from '../../../api/client'

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

function segmentIntersectsRect(start: DiagramPoint, end: DiagramPoint, rect: BoardRect) {
  if (start.y === end.y) {
    const minX = Math.min(start.x, end.x)
    const maxX = Math.max(start.x, end.x)
    return start.y > rect.y && start.y < rect.y + rect.height && maxX > rect.x && minX < rect.x + rect.width
  }
  if (start.x === end.x) {
    const minY = Math.min(start.y, end.y)
    const maxY = Math.max(start.y, end.y)
    return start.x > rect.x && start.x < rect.x + rect.width && maxY > rect.y && minY < rect.y + rect.height
  }
  return true
}

function pathIsClear(board: BoardDefinition, points: DiagramPoint[]) {
  return points.slice(1).every((point, index) =>
    board.forbidden_areas.every((area) => !segmentIntersectsRect(points[index], point, area)),
  )
}

function pathCost(points: DiagramPoint[]) {
  const distance = points.slice(1).reduce((total, point, index) =>
    total + Math.abs(point.x - points[index].x) + Math.abs(point.y - points[index].y), 0)
  return distance + Math.max(0, points.length - 2) * 12
}

function isFacingAcrossRows(start: BoardPin, end: BoardPin) {
  if (start.y < end.y) return start.side === 'bottom' && end.side === 'top'
  if (start.y > end.y) return start.side === 'top' && end.side === 'bottom'
  return false
}

function directChannelY(board: BoardDefinition, start: BoardPin, end: BoardPin) {
  const minY = Math.min(start.y, end.y)
  const maxY = Math.max(start.y, end.y)
  const midpoint = (minY + maxY) / 2
  const channels = board.routing_channels
    .filter((channel) => channel.channel_type === 'horizontal')
    .map((channel) => ({ channel, center: channel.y + channel.height / 2 }))
    .filter(({ center }) => center > minY && center < maxY)
    .sort((left, right) => Math.abs(left.center - midpoint) - Math.abs(right.center - midpoint))
  if (!channels.length) return midpoint
  const { channel } = channels[0]
  const safeTop = channel.y + 4
  const safeBottom = channel.y + channel.height - 4
  return Math.max(safeTop, Math.min(midpoint, safeBottom))
}

function outerRoute(board: BoardDefinition, start: BoardPin, end: BoardPin, startExit: DiagramPoint, endExit: DiagramPoint, lane: number) {
  const leftX = board.routing_margin
  const rightX = board.width - board.routing_margin
  const leftCost = Math.abs(startExit.x - leftX) + Math.abs(endExit.x - leftX)
  const rightCost = Math.abs(startExit.x - rightX) + Math.abs(endExit.x - rightX)
  const outerX = leftCost <= rightCost ? leftX - lane : rightX + lane
  return compact([
    { x: start.x, y: start.y }, startExit,
    { x: outerX, y: startExit.y }, { x: outerX, y: endExit.y },
    endExit, { x: end.x, y: end.y },
  ])
}

export function routeConnection(board: BoardDefinition, connection: WiringConnection, laneIndex = 0): RoutedWire {
  const start = findPin(board, connection.from)
  const end = findPin(board, connection.to)
  if (!start || !end) throw new Error('연결 단자의 좌표를 찾을 수 없습니다.')

  const lane = laneIndex * 7
  const escape = (pin: BoardPin) => ({ x: pin.x, y: pin.y + (pin.side === 'top' ? -(32 + lane) : 32 + lane) })
  const startPoint = { x: start.pin.x, y: start.pin.y }
  const endPoint = { x: end.pin.x, y: end.pin.y }
  const startExit = escape(start.pin)
  const endExit = escape(end.pin)

  const candidates: DiagramPoint[][] = []

  // 마주 보는 단자 사이에 빈 행간 통로가 있으면 가장 짧은 직각 경로를 우선한다.
  const facingAcrossRows = isFacingAcrossRows(start.pin, end.pin)
  if (facingAcrossRows) {
    const channelY = directChannelY(board, start.pin, end.pin)
    candidates.push(compact([startPoint, { x: start.pin.x, y: channelY }, { x: end.pin.x, y: channelY }, endPoint]))
  }

  // 같은 행의 같은 방향 단자는 해당 행의 위·아래 통로를 사용한다.
  if (start.item.row === end.item.row && start.pin.side === end.pin.side) {
    const channelY = start.pin.side === 'top' ? Math.min(startExit.y, endExit.y) : Math.max(startExit.y, endExit.y)
    candidates.push(compact([startPoint, startExit, { x: endExit.x, y: channelY }, endExit, endPoint]))
  }

  // 일반적인 두 직각 후보도 검사한다. 소켓 본체를 통과하지 않는 후보만 사용할 수 있다.
  if (!facingAcrossRows) {
    candidates.push(
      compact([startPoint, startExit, { x: endExit.x, y: startExit.y }, endExit, endPoint]),
      compact([startPoint, startExit, { x: startExit.x, y: endExit.y }, endExit, endPoint]),
    )
  }

  const directRoute = candidates
    .filter((points) => isOrthogonal(points) && pathIsClear(board, points))
    .sort((left, right) => pathCost(left) - pathCost(right))[0]
  const points = directRoute ?? outerRoute(board, start.pin, end.pin, startExit, endExit, lane)

  if (!isOrthogonal(points)) throw new Error('직교 배선 경로를 만들 수 없습니다.')
  return { ...connection, points }
}

export function routeConnections(board: BoardDefinition, connections: WiringConnection[]) {
  return connections.map((connection, index) => routeConnection(board, connection, index % 5))
}
