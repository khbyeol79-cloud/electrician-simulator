import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import type { FreeCircuitWorkspace, WiringConnection } from '../api/client'
import { useFreeCircuitAutosave } from '../features/free-circuit/useFreeCircuitAutosave'

afterEach(() => { cleanup(); vi.restoreAllMocks() })

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej })
  return { promise, resolve, reject }
}

const workspace = {
  workspace_id: 'race-test', schema_version: '1.0', name: '경합 시험', connections: [], updated_at: null,
  editor: { schema_version: '1.0', mode: 'graphic', template_id: 'basic_board_001' },
} as unknown as FreeCircuitWorkspace

const wireA: WiringConnection = { from: 'X1-1', to: 'MC1-4', wire_color: 'yellow', pair_display_color: '#64748b' }
const wireB: WiringConnection = { from: 'X1-2', to: 'MC1-5', wire_color: 'yellow', pair_display_color: '#64748b' }

function Harness({ saveWorkspace }: { saveWorkspace: (value: FreeCircuitWorkspace) => Promise<FreeCircuitWorkspace> }) {
  const [connections, setConnections] = useState<WiringConnection[]>([])
  const autosave = useFreeCircuitAutosave({
    workspace, connections, mode: 'graphic', delay: 10, saveWorkspace,
    onSaved: () => undefined, onError: () => undefined,
  })
  const edit = (next: WiringConnection[]) => { setConnections(next); autosave.schedule({ connections: next }) }
  return <div><button onClick={() => edit([wireA])}>첫 편집</button><button onClick={() => edit([wireA, wireB])}>최신 편집</button><span role="status">{autosave.status}</span></div>
}

it('serializes overlapping saves and finishes with the newest revision', async () => {
  const first = deferred<FreeCircuitWorkspace>()
  const second = deferred<FreeCircuitWorkspace>()
  const saveWorkspace = vi.fn()
    .mockImplementationOnce(() => first.promise)
    .mockImplementationOnce(() => second.promise)
  const user = userEvent.setup()
  render(<Harness saveWorkspace={saveWorkspace} />)

  await user.click(screen.getByRole('button', { name: '첫 편집' }))
  await waitFor(() => expect(saveWorkspace).toHaveBeenCalledTimes(1))
  await user.click(screen.getByRole('button', { name: '최신 편집' }))
  await new Promise((resolve) => window.setTimeout(resolve, 30))
  expect(saveWorkspace).toHaveBeenCalledTimes(1)

  first.resolve({ ...workspace, connections: [wireA] })
  await waitFor(() => expect(saveWorkspace).toHaveBeenCalledTimes(2))
  expect(saveWorkspace.mock.calls[1][0].connections).toEqual([wireA, wireB])
  second.resolve({ ...workspace, connections: [wireA, wireB] })
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('saved'))
})
