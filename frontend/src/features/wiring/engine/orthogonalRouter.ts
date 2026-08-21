import type {
  BoardDefinition,
  BoardItem,
  BoardPin,
  BoardRect,
  DiagramPoint,
  WiringConnection,
} from '../../../api/client'

export type RoutedWire = WiringConnection & { points: DiagramPoint[] }
export type ConnectionEndpointOffset = { from: number; to: number }

type HorizontalLane = BoardRect & {
  channel_id: string
  channel_type: 'horizontal'
  routeY: number
}

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

function intervalOverlap(startA: number, endA: number, startB: number, endB: number) {
  return Math.min(Math.max(startA, endA), Math.max(startB, endB)) - Math.max(Math.min(startA, endA), Math.min(startB, endB))
}

export function pathHasSelfOverlap(points: DiagramPoint[]) {
  const segments = points.slice(1).map((end, index) => ({ start: points[index], end }))
  for (let firstIndex = 0; firstIndex < segments.length; firstIndex += 1) {
    for (let secondIndex = firstIndex + 2; secondIndex < segments.length; secondIndex += 1) {
      const first = segments[firstIndex]
      const second = segments[secondIndex]
      const firstVertical = first.start.x === first.end.x
      const secondVertical = second.start.x === second.end.x
      if (firstVertical && secondVertical && first.start.x === second.start.x && intervalOverlap(first.start.y, first.end.y, second.start.y, second.end.y) > 0) return true
      if (!firstVertical && !secondVertical && first.start.y === second.start.y && intervalOverlap(first.start.x, first.end.x, second.start.x, second.end.x) > 0) return true
      if (firstVertical !== secondVertical) {
        const vertical = firstVertical ? first : second
        const horizontal = firstVertical ? second : first
        const crossesX = vertical.start.x >= Math.min(horizontal.start.x, horizontal.end.x) && vertical.start.x <= Math.max(horizontal.start.x, horizontal.end.x)
        const crossesY = horizontal.start.y >= Math.min(vertical.start.y, vertical.end.y) && horizontal.start.y <= Math.max(vertical.start.y, vertical.end.y)
        if (crossesX && crossesY) return true
      }
    }
  }
  return false
}

function horizontalLanes(board: BoardDefinition): HorizontalLane[] {
  const pins = board.items.flatMap((item) => item.pins)
  return board.routing_channels
    .filter((channel): channel is BoardDefinition['routing_channels'][number] & { channel_type: 'horizontal' } => channel.channel_type === 'horizontal')
    .map((channel) => {
      const center = channel.y + channel.height / 2
      const above = pins.filter((pin) => pin.side === 'bottom' && pin.y < center).map((pin) => pin.y).sort((left, right) => right - left)[0]
      const below = pins.filter((pin) => pin.side === 'top' && pin.y > center).map((pin) => pin.y).sort((left, right) => left - right)[0]
      return { ...channel, routeY: above !== undefined && below !== undefined ? (above + below) / 2 : center }
    })
    .sort((left, right) => left.routeY - right.routeY)
}

function laneForPin(lanes: HorizontalLane[], pin: BoardPin) {
  return lanes
    .filter((lane) => pin.side === 'bottom' ? lane.routeY > pin.y : lane.routeY < pin.y)
    .sort((left, right) => Math.abs(left.routeY - pin.y) - Math.abs(right.routeY - pin.y))[0]
}

function laneY(lane: HorizontalLane, laneIndex: number) {
  const bundleOffsets = [0, -3, 3, -6, 6]
  return lane.routeY + bundleOffsets[laneIndex % bundleOffsets.length]
}

function outerXs(board: BoardDefinition, laneIndex: number) {
  const leftChannel = board.routing_channels.find((channel) => channel.channel_type === 'left_outer')
  const rightChannel = board.routing_channels.find((channel) => channel.channel_type === 'right_outer')
  const leftBase = leftChannel ? leftChannel.x + leftChannel.width + 8 : board.routing_margin + 24
  const rightBase = rightChannel ? rightChannel.x - 8 : board.width - board.routing_margin - 24
  const clearance = 12
  const leftLimit = Math.min(...board.forbidden_areas.map((area) => area.x), board.width / 2) - clearance
  const rightLimit = Math.max(...board.forbidden_areas.map((area) => area.x + area.width), board.width / 2) + clearance
  const spread = laneIndex * 7
  return {
    left: Math.min(leftBase + spread, leftLimit),
    right: Math.max(rightBase - spread, rightLimit),
  }
}

function viaOuter(start: BoardPin, end: BoardPin, startY: number, endY: number, outerX: number) {
  return compact([
    { x: start.x, y: start.y }, { x: start.x, y: startY },
    { x: outerX, y: startY }, { x: outerX, y: endY },
    { x: end.x, y: endY }, { x: end.x, y: end.y },
  ])
}

function routeCost(points: DiagramPoint[]) {
  return points.slice(1).reduce((total, point, index) =>
    total + Math.abs(point.x - points[index].x) + Math.abs(point.y - points[index].y), 0)
}

export function routeConnection(
  board: BoardDefinition,
  connection: WiringConnection,
  laneIndex = 0,
  endpointOffset: ConnectionEndpointOffset = { from: 0, to: 0 },
): RoutedWire {
  const start = findPin(board, connection.from)
  const end = findPin(board, connection.to)
  if (!start || !end) throw new Error('연결 단자의 좌표를 찾을 수 없습니다.')
  const startPin = { ...start.pin, x: start.pin.x + endpointOffset.from }
  const endPin = { ...end.pin, x: end.pin.x + endpointOffset.to }

  const lanes = horizontalLanes(board)
  const startLane = laneForPin(lanes, startPin)
  const endLane = laneForPin(lanes, endPin)
  if (!startLane || !endLane) throw new Error('단자와 연결할 배선 통로를 찾을 수 없습니다.')
  const startY = laneY(startLane, laneIndex)
  const endY = laneY(endLane, laneIndex)

  let candidates: DiagramPoint[][]
  if (startLane.channel_id === endLane.channel_id) {
    candidates = [compact([
      { x: startPin.x, y: startPin.y }, { x: startPin.x, y: startY },
      { x: endPin.x, y: endY }, { x: endPin.x, y: endPin.y },
    ])]
  } else {
    const outer = outerXs(board, laneIndex)
    candidates = [
      viaOuter(startPin, endPin, startY, endY, outer.left),
      viaOuter(startPin, endPin, startY, endY, outer.right),
    ].sort((left, right) => routeCost(left) - routeCost(right))
  }

  const points = candidates.find((candidate) => isOrthogonal(candidate) && pathIsClear(board, candidate) && !pathHasSelfOverlap(candidate))
  if (!points) throw new Error('겹치지 않는 직교 배선 경로를 만들 수 없습니다.')
  return { ...connection, points }
}

export function buildConnectionEndpointOffsets(connections: WiringConnection[]) {
  const offsets: ConnectionEndpointOffset[] = connections.map(() => ({ from: 0, to: 0 }))
  const terminalUses = new Map<string, { connectionIndex: number; endpoint: 'from' | 'to' }[]>()
  connections.forEach((connection, connectionIndex) => {
    const fromUses = terminalUses.get(connection.from) ?? []
    fromUses.push({ connectionIndex, endpoint: 'from' })
    terminalUses.set(connection.from, fromUses)
    const toUses = terminalUses.get(connection.to) ?? []
    toUses.push({ connectionIndex, endpoint: 'to' })
    terminalUses.set(connection.to, toUses)
  })
  terminalUses.forEach((uses) => {
    if (uses.length < 2) return
    const halfSpan = Math.min(8, 5 + Math.max(0, uses.length - 2))
    const step = (halfSpan * 2) / (uses.length - 1)
    uses.forEach((use, index) => {
      offsets[use.connectionIndex][use.endpoint] = -halfSpan + step * index
    })
  })
  return offsets
}

export function routeConnections(board: BoardDefinition, connections: WiringConnection[]) {
  const routable = connections.filter((connection) => findPin(board, connection.from) && findPin(board, connection.to))
  const offsets = buildConnectionEndpointOffsets(routable)
  return routable.map((connection, index) => routeConnection(board, connection, index % 5, offsets[index]))
}
