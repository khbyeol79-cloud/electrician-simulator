import { act, cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import * as api from '../api/client'
import { StatusBar } from '../components/StatusBar'
import { STATUS_POLL_MS, STATUS_TIMEOUT_MS, useServerStatus } from '../features/system/useServerStatus'
import { installApiMock } from './mockApi'

const healthy = {
  health: { status: 'ok' as const, app_name: '시험', version: '0.13.0' },
  appInfo: { app_name: '시험', version: '0.13.0', mode: 'web' as const, database_ready: true, problems_path_ready: true },
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

beforeEach(() => { vi.useFakeTimers(); vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(true) })
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers() })

it('starts in checking, not connected, and does not reuse readiness while disconnected', () => {
  const { rerender, container } = render(<StatusBar info={healthy.appInfo} connection="checking" />)
  expect(screen.getByText('확인 중')).toBeInTheDocument()
  expect(screen.getAllByText('대기 중')).toHaveLength(2)
  expect(container.querySelectorAll('.status-dot.ready')).toHaveLength(0)
  rerender(<StatusBar info={healthy.appInfo} connection="connected" />)
  expect(screen.getByText('연결됨')).toBeInTheDocument()
  expect(screen.getAllByText('준비됨')).toHaveLength(2)
  rerender(<StatusBar info={healthy.appInfo} connection="disconnected" />)
  expect(screen.getByText('연결 끊김')).toBeInTheDocument()
  expect(screen.getAllByText('대기 중')).toHaveLength(2)
  expect(container.querySelectorAll('.status-dot.ready')).toHaveLength(0)
  expect(container.querySelectorAll('.status-dot.error')).toHaveLength(1)
})

it('polls and recovers without clearing user edits or reloading the page', async () => {
  const status = vi.spyOn(api, 'getSystemStatus').mockResolvedValue(healthy)
  const Probe = () => {
    const state = useServerStatus(0)
    return <><textarea aria-label="작성 중" defaultValue="보존할 입력" /><StatusBar {...state} /></>
  }
  render(<Probe />)
  await act(async () => { await vi.advanceTimersByTimeAsync(0) })
  expect(screen.getByText('연결됨')).toBeInTheDocument()
  status.mockRejectedValueOnce(new TypeError('Failed to fetch'))
  await act(async () => { await vi.advanceTimersByTimeAsync(STATUS_POLL_MS) })
  expect(screen.getByText('연결 끊김')).toBeInTheDocument()
  expect(screen.queryByText('준비됨')).not.toBeInTheDocument()
  await act(async () => { await vi.advanceTimersByTimeAsync(STATUS_POLL_MS) })
  expect(screen.getAllByText('준비됨')).toHaveLength(2)
  expect(screen.getByLabelText('작성 중')).toHaveValue('보존할 입력')
  expect(status).toHaveBeenCalledTimes(3)
})

it('times out hanging probes and ignores a late success after recovery', async () => {
  const late = deferred<typeof healthy>()
  const status = vi.spyOn(api, 'getSystemStatus').mockReturnValueOnce(late.promise)
    .mockResolvedValue({ ...healthy, appInfo: { ...healthy.appInfo, database_ready: false } })
  const { result } = renderHook(() => useServerStatus(0))
  const signal = status.mock.calls[0][0]!
  expect(result.current.connection).toBe('checking')
  await act(async () => { await vi.advanceTimersByTimeAsync(STATUS_TIMEOUT_MS) })
  expect(result.current.connection).toBe('disconnected')
  expect(signal.aborted).toBe(true)
  await act(async () => { await vi.advanceTimersByTimeAsync(STATUS_POLL_MS - STATUS_TIMEOUT_MS) })
  expect(result.current.connection).toBe('connected')
  expect(result.current.info?.database_ready).toBe(false)
  await act(async () => { late.resolve(healthy) })
  expect(result.current.info?.database_ready).toBe(false)
})

it('responds immediately to offline/online and cancels the previous request', async () => {
  const late = deferred<typeof healthy>()
  const status = vi.spyOn(api, 'getSystemStatus').mockReturnValueOnce(late.promise).mockResolvedValue(healthy)
  const { result } = renderHook(() => useServerStatus(0))
  const signal = status.mock.calls[0][0]!
  act(() => { fireEvent.offline(window) })
  expect(result.current.connection).toBe('disconnected')
  expect(signal.aborted).toBe(true)
  await act(async () => { late.resolve(healthy) })
  expect(result.current.connection).toBe('disconnected')
  await act(async () => { fireEvent.online(window) })
  expect(result.current.connection).toBe('connected')
})

it('checks on focus/visibility without overlapping probes and cleans up on unmount', async () => {
  const pending = deferred<typeof healthy>()
  const status = vi.spyOn(api, 'getSystemStatus').mockReturnValue(pending.promise)
  const { unmount } = renderHook(() => useServerStatus(0))
  act(() => { fireEvent.focus(window); fireEvent(document, new Event('visibilitychange')) })
  expect(status).toHaveBeenCalledTimes(1)
  await act(async () => { pending.resolve(healthy) })
  const next = deferred<typeof healthy>()
  status.mockReturnValue(next.promise)
  await act(async () => { fireEvent.focus(window) })
  expect(status).toHaveBeenCalledTimes(2)
  const signal = status.mock.calls[1][0]!
  unmount()
  expect(signal.aborted).toBe(true)
  await act(async () => { await vi.advanceTimersByTimeAsync(STATUS_POLL_MS * 3); fireEvent.online(window); fireEvent.focus(window) })
  expect(status).toHaveBeenCalledTimes(2)
  expect(vi.getTimerCount()).toBe(0)
})

it('restarts a manual check and ignores the superseded response', async () => {
  const old = deferred<typeof healthy>()
  const status = vi.spyOn(api, 'getSystemStatus').mockReturnValueOnce(old.promise).mockRejectedValueOnce(new Error('offline'))
  const { result, rerender } = renderHook(({ key }) => useServerStatus(key), { initialProps: { key: 0 } })
  const signal = status.mock.calls[0][0]!
  await act(async () => { rerender({ key: 1 }) })
  expect(signal.aborted).toBe(true)
  expect(result.current.connection).toBe('disconnected')
  await act(async () => { old.resolve(healthy) })
  expect(result.current.connection).toBe('disconnected')
})

it('does not claim ready for unavailable database or problem folders', () => {
  render(<StatusBar connection="connected" info={{ ...healthy.appInfo, database_ready: false, problems_path_ready: false }} />)
  expect(screen.getByText('연결됨')).toBeInTheDocument()
  expect(screen.getAllByText('대기 중')).toHaveLength(2)
})

it('bypasses HTTP cache for both status requests', async () => {
  const fetchMock = installApiMock()
  const controller = new AbortController()
  await api.getSystemStatus(controller.signal)
  for (const url of ['/api/health', '/api/app-info']) {
    expect(fetchMock).toHaveBeenCalledWith(url, expect.objectContaining({ cache: 'no-store', signal: controller.signal }))
  }
})

it('still probes a reachable LAN server when the browser reports no internet', async () => {
  vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false)
  const status = vi.spyOn(api, 'getSystemStatus').mockResolvedValue(healthy)
  const { result } = renderHook(() => useServerStatus(0))
  await act(async () => { await vi.advanceTimersByTimeAsync(0) })
  expect(result.current.connection).toBe('connected')
  act(() => { fireEvent.offline(window) })
  expect(result.current.connection).toBe('disconnected')
  await act(async () => { await vi.advanceTimersByTimeAsync(STATUS_POLL_MS) })
  expect(result.current.connection).toBe('connected')
  expect(status).toHaveBeenCalledTimes(2)
})
