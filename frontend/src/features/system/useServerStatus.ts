import { useEffect, useState } from 'react'
import { getSystemStatus, type AppInfoResponse } from '../../api/client'

export type ServerConnection = 'checking' | 'connected' | 'disconnected'
export const STATUS_POLL_MS = 5000
export const STATUS_TIMEOUT_MS = 3000

export function useServerStatus(refreshKey: number) {
  const [info, setInfo] = useState<AppInfoResponse>()
  const [connection, setConnection] = useState<ServerConnection>('checking')
  const [error, setError] = useState<string>()

  useEffect(() => {
    let stopped = false
    let pending: AbortController | undefined
    let timeout: number | undefined
    setConnection('checking')
    setError(undefined)

    const disconnected = (message: string) => {
      setConnection('disconnected')
      setError(message)
    }
    const cancel = () => {
      const previous = pending
      pending = undefined
      window.clearTimeout(timeout)
      previous?.abort()
    }
    const check = () => {
      if (stopped || pending) return
      // Internet connectivity hints can be false while the institution LAN is
      // reachable. A fresh response from our own server is authoritative.
      const controller = new AbortController()
      pending = controller
      timeout = window.setTimeout(() => {
        if (stopped || pending !== controller) return
        cancel()
        disconnected('서버가 응답하지 않습니다. 연결이 복구되면 자동으로 다시 확인합니다.')
      }, STATUS_TIMEOUT_MS)
      void getSystemStatus(controller.signal).then(({ health, appInfo }) => {
        // Ignore a late response from a timed-out, superseded or unmounted check.
        if (stopped || controller.signal.aborted || pending !== controller) return
        if (health.status !== 'ok') throw new Error('서버 상태 확인 실패')
        setInfo(appInfo)
        setConnection('connected')
        setError(undefined)
      }).catch(() => {
        if (stopped || controller.signal.aborted || pending !== controller) return
        disconnected('서버와 연결이 끊겼습니다. 서버가 켜지면 자동으로 다시 확인합니다.')
        controller.abort()
      }).finally(() => {
        if (pending === controller) {
          window.clearTimeout(timeout)
          pending = undefined
        }
      })
    }
    const offline = () => {
      cancel()
      disconnected('네트워크 연결이 끊겼습니다. 연결이 복구되면 자동으로 다시 확인합니다.')
    }
    const visible = () => { if (!document.hidden) check() }
    check()
    const timer = window.setInterval(check, STATUS_POLL_MS)
    window.addEventListener('offline', offline)
    window.addEventListener('online', check)
    window.addEventListener('focus', check)
    document.addEventListener('visibilitychange', visible)
    return () => {
      stopped = true
      cancel()
      window.clearInterval(timer)
      window.removeEventListener('offline', offline)
      window.removeEventListener('online', check)
      window.removeEventListener('focus', check)
      document.removeEventListener('visibilitychange', visible)
    }
  }, [refreshKey])

  return { info, connection, error }
}
