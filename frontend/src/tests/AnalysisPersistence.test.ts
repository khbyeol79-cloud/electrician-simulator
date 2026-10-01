import { afterEach, expect, it, vi } from 'vitest'
import { getCircuitAnalysisDraft, saveCircuitAnalysisDraft } from '../api/client'
import { USER_ID_STORAGE_KEY } from '../features/user/userProfile'

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear() })

it('serializes analysis writes, captures the original user and waits before reading the reference', async () => {
  const draft = { problem_version: 1, memo: '', selected_device_ids: [], selected_socket_ids: [], selected_terminal_ids: [], annotations: {} }
  let releaseFirst!: () => void
  const firstResponse = new Promise<void>(resolve => { releaseFirst = resolve })
  let writes = 0
  const fetchMock = vi.fn(async (_url: unknown, init?: RequestInit) => {
    if (init?.method === 'PUT' && ++writes === 1) await firstResponse
    return { ok: true, status: 200, json: async () => ({ ...draft, memo: 'second' }) } as Response
  })
  vi.stubGlobal('fetch', fetchMock)
  localStorage.setItem(USER_ID_STORAGE_KEY, 'analysis-user-a')
  const first = saveCircuitAnalysisDraft('qnet-test', { ...draft, memo: 'first' })
  const second = saveCircuitAnalysisDraft('qnet-test', { ...draft, memo: 'second' })
  const read = getCircuitAnalysisDraft('qnet-test')
  localStorage.setItem(USER_ID_STORAGE_KEY, 'analysis-user-b')
  await Promise.resolve()
  await Promise.resolve()
  expect(fetchMock).toHaveBeenCalledTimes(1)
  releaseFirst()
  await Promise.all([first, second, read])
  expect(fetchMock.mock.calls.map(([, init]) => init?.method ?? 'GET')).toEqual(['PUT', 'PUT', 'GET'])
  for (const [, init] of fetchMock.mock.calls) expect(init?.headers).toMatchObject({ 'X-User-Id': 'analysis-user-a' })
})
