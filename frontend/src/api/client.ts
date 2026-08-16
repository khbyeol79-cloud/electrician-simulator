export type HealthResponse = {
  status: 'ok'
  app_name: string
  version: string
}

export type AppInfoResponse = {
  app_name: string
  version: string
  mode: 'desktop' | 'web'
  database_ready: boolean
  problems_path_ready: boolean
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal })
  if (!response.ok) {
    throw new Error(`서버 응답 오류 (${response.status})`)
  }
  return response.json() as Promise<T>
}

export async function getSystemStatus(signal?: AbortSignal) {
  const [health, appInfo] = await Promise.all([
    getJson<HealthResponse>('/api/health', signal),
    getJson<AppInfoResponse>('/api/app-info', signal),
  ])
  return { health, appInfo }
}

