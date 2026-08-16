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

export type ProblemStatus = 'draft' | 'reviewed' | 'verified'
export type Difficulty = 'beginner' | 'intermediate' | 'advanced'

export type ProblemSummary = {
  problem_id: string
  title: string
  version: number
  problem_type: 'official' | 'reconstructed' | 'variant' | 'practice' | 'original'
  status: ProblemStatus
  difficulty: Difficulty
  estimated_minutes: number
  tags: string[]
  source_type: string
  selectable: boolean
  warning_count: number
}

export type PublicProblemDetail = Omit<ProblemSummary, 'selectable'> & {
  source_name: string
  description: string
  instructions: string[]
  learning_objectives: string[]
  power_supply: {
    system: string
    voltage: number
    frequency: number
    wire_colors: Record<string, string>
  }
  schematic: { file: string; format: string; view_box: string }
  board: { layout_id: string }
  available_devices: Record<string, unknown>[]
  circuit: Record<string, unknown>
  socket_questions: Record<string, unknown>[]
}

export type SocketType = {
  socket_type_id: string
  name: string
  pin_count: 8 | 12
  view_side: 'wiring_base_front'
  rows: { row_id: 'top' | 'bottom'; pins: number[] }[]
  center: { shape: 'octal' | 'circular'; symmetric: boolean; label_area: boolean }
}

export type CircuitSummary = {
  problem_id: string
  problem_title: string
  device_count: number
  terminal_count: number
  contact_count: number
  coil_count: number
  socket_type_ids: string[]
  reference_integrity: 'valid'
  warning_count: number
  definition_status: 'structure_only' | 'functional'
}

export type ReloadStatistics = {
  loaded: number
  excluded: number
  warnings: number
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

export function getProblems(signal?: AbortSignal) {
  return getJson<ProblemSummary[]>('/api/problems', signal)
}

export function getProblem(problemId: string, signal?: AbortSignal) {
  return getJson<PublicProblemDetail>(`/api/problems/${encodeURIComponent(problemId)}`, signal)
}

export function getSocketTypes(signal?: AbortSignal) {
  return getJson<SocketType[]>('/api/catalog/socket-types', signal)
}

export function getCircuitSummary(problemId: string, signal?: AbortSignal) {
  return getJson<CircuitSummary>(`/api/problems/${encodeURIComponent(problemId)}/circuit-summary`, signal)
}

export async function reloadProblemCatalog() {
  const response = await fetch('/api/problems/reload', { method: 'POST' })
  if (!response.ok) {
    throw new Error(`문제 새로고침 오류 (${response.status})`)
  }
  return response.json() as Promise<ReloadStatistics>
}
