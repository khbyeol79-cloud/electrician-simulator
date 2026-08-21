import type { BoardPin, WiringConnection } from '../../../api/client'

export type TerminalBlockUsage = { external: number; internal: number }

export function isFreeJunction(pin: BoardPin | undefined) {
  return pin?.terminal_role === 'free_junction' || pin?.terminal_id.startsWith('TB5-') || pin?.terminal_id.startsWith('TB6-')
}

export function terminalBlockBank(connection: Pick<WiringConnection, 'from' | 'to'>, terminalId: string, externalIds: ReadonlySet<string>) {
  const other = connection.from === terminalId ? connection.to : connection.from
  return externalIds.has(other) ? 'external' : 'internal'
}

export function terminalBlockUsage(connections: Pick<WiringConnection, 'from' | 'to'>[], terminalId: string, externalIds: ReadonlySet<string>): TerminalBlockUsage {
  const usage: TerminalBlockUsage = { external: 0, internal: 0 }
  connections.forEach((connection) => {
    if (connection.from !== terminalId && connection.to !== terminalId) return
    usage[terminalBlockBank(connection, terminalId, externalIds)] += 1
  })
  return usage
}
