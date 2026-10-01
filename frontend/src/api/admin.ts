import { authHeaders } from '../features/user/authSession'

export type NetworkOptions = { host: string; port: number }
export type ManagedAccount = {
  user_id: string; username: string; nickname: string; created_at: number
  is_admin: boolean; active_sessions: number; last_seen: number | null
}
export type ServerStatus = {
  version: string; uptime_seconds: number; database_ready: boolean
  service_managed: boolean; current_network: NetworkOptions | null; saved_network: NetworkOptions | null
  restart_required: boolean; lan_addresses: string[]; registration_open: boolean
  account_count: number; active_sessions: number; data_directory: string
  disk_free_bytes: number; disk_total_bytes: number; secure_cookie: boolean
  audit: { actor: string; action: string; target: string; created_at: number }[]
}

export async function adminRequest<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(`/api/admin/${path}`, {
    method, credentials: 'same-origin', cache: 'no-store',
    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  })
  if (response.status === 401) window.dispatchEvent(new Event('electrician:auth-expired'))
  const result = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : '설정값 또는 관리자 권한을 확인하세요.')
  return result as T
}
