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
  circuit: CircuitDefinition
  socket_questions: SocketQuestion[]
}

export type CircuitDevice = { device_id: string; device_type_id: string; label: string; socket_type_id: string | null }
export type CircuitContact = { contact_id: string; owner_device_id: string; contact_type: 'NO' | 'NC' | 'CHANGEOVER'; normal_state: 'open' | 'closed' }
export type CircuitCoil = { coil_id: string; owner_device_id: string }
export type CircuitDefinition = {
  schema_version: '1.0'; definition_status: 'structure_only' | 'functional'
  devices: CircuitDevice[]; terminals: Record<string, unknown>[]; contacts: CircuitContact[]; coils: CircuitCoil[]
}
export type SocketQuestion = {
  question_id: string; target_element_type: 'contact' | 'coil'; target_element_id: string; display_label: string
  answer_slots: { slot_id: string; position: 'above' | 'below' | 'left' | 'right' }[]
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

export type DiagramPoint = { x: number; y: number }
export type DiagramElement = {
  element_id: string; element_type: string; section_id: string
  circuit_ref_type: 'device' | 'terminal' | 'contact' | 'coil' | null
  circuit_ref_id: string | null; question_id: string | null
  x: number; y: number; width: number; height: number
  orientation: 'horizontal' | 'vertical'; label: string; interactive: boolean
}
export type SchematicDiagram = {
  schema_version: '1.0'
  view_box: { x: number; y: number; width: number; height: number }
  sections: { section_id: string; label: string; bounds: { x: number; y: number; width: number; height: number } }[]
  elements: DiagramElement[]
  conductors: { conductor_id: string; section_id: string; points: DiagramPoint[]; line_style: string; junctions: DiagramPoint[] }[]
}
export type CircuitAttemptResult = {
  attempt_id: number | null; gradable: boolean; overall_correct: boolean | null
  answered_count: number; total_count: number; correct_count: number; message: string
  results: { question_id: string; correct: boolean; slot_results: Record<string, boolean> }[]
}
export type CircuitProgress = {
  problem_id: string; attempt_count: number; last_submitted_at: string | null
  last_overall_correct: boolean | null; last_correct_count: number; total_count: number
}

export type BoardPin = { terminal_id: string; label: string; number: number | null; side: 'top' | 'bottom'; x: number; y: number; max_connections: number; enabled: boolean }
export type BoardRect = { x: number; y: number; width: number; height: number }
export type BoardItem = {
  item_id: string; label: string; item_type: 'socket_8p' | 'socket_12p' | 'terminal_block' | 'component'
  socket_type_id: string | null; row: number; x: number; y: number; width: number; height: number
  pins: BoardPin[]; label_area: BoardRect
}
export type BoardDefinition = {
  schema_version: '1.0'; board_id: string; width: number; height: number; routing_margin: number
  items: BoardItem[]
  routing_channels: (BoardRect & { channel_id: string; channel_type: 'horizontal' | 'left_outer' | 'right_outer' })[]
  forbidden_areas: (BoardRect & { area_id: string })[]
}
export type WiringConnection = { from: string; to: string; wire_color: 'brown' | 'black' | 'gray' | 'yellow'; pair_display_color: string }
export type WiringDraft = { problem_id: string; problem_version: number; mode: 'graphic' | 'summary'; connections: WiringConnection[]; updated_at: string | null }
export type WiringAttemptResult = {
  attempt_id: number | null; gradable: boolean; overall_correct: boolean | null; required_count: number; correct_count: number
  missing_connections: string[]; extra_connections: string[]; forbidden_connections: string[]; message: string
}
export type WiringProgress = { problem_id: string; attempt_count: number; last_submitted_at: string | null; last_overall_correct: boolean | null; last_correct_count: number; required_count: number }

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

export function getDiagram(problemId: string, signal?: AbortSignal) {
  return getJson<SchematicDiagram>(`/api/problems/${encodeURIComponent(problemId)}/diagram`, signal)
}

export function getCircuitProgress(problemId: string, signal?: AbortSignal) {
  return getJson<CircuitProgress>(`/api/problems/${encodeURIComponent(problemId)}/circuit-progress`, signal)
}

export function getBoard(problemId: string, signal?: AbortSignal) {
  return getJson<BoardDefinition>(`/api/problems/${encodeURIComponent(problemId)}/board`, signal)
}

export function getWiringDraft(problemId: string, signal?: AbortSignal) {
  return getJson<WiringDraft | null>(`/api/problems/${encodeURIComponent(problemId)}/wiring-draft`, signal)
}

export function getWiringProgress(problemId: string, signal?: AbortSignal) {
  return getJson<WiringProgress>(`/api/problems/${encodeURIComponent(problemId)}/wiring-progress`, signal)
}

async function mutationJson<T>(url: string, method: string, body?: unknown): Promise<T> {
  const response = await fetch(url, { method, headers: body === undefined ? undefined : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) })
  if (!response.ok) {
    const payload = await response.json().catch(() => undefined) as { detail?: { message?: string } | string } | undefined
    const message = typeof payload?.detail === 'object' ? payload.detail.message : payload?.detail
    throw new Error(message || `서버 응답 오류 (${response.status})`)
  }
  return (response.status === 204 ? undefined : await response.json()) as T
}

export function saveWiringDraft(problemId: string, problemVersion: number, mode: 'graphic' | 'summary', connections: WiringConnection[]) {
  return mutationJson<WiringDraft>(`/api/problems/${encodeURIComponent(problemId)}/wiring-draft`, 'PUT', { problem_version: problemVersion, mode, connections })
}

export function deleteWiringDraft(problemId: string) {
  return mutationJson<void>(`/api/problems/${encodeURIComponent(problemId)}/wiring-draft`, 'DELETE')
}

export function submitWiringAttempt(problemId: string, problemVersion: number, connections: WiringConnection[]) {
  return mutationJson<WiringAttemptResult>(`/api/problems/${encodeURIComponent(problemId)}/wiring-attempts/submit`, 'POST', { problem_version: problemVersion, connections })
}

export async function submitCircuitAttempt(problemId: string, problemVersion: number, responses: Record<string, Record<string, number>>) {
  const response = await fetch(`/api/problems/${encodeURIComponent(problemId)}/circuit-attempts/submit`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ problem_version: problemVersion, responses }),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => undefined) as { detail?: { message?: string } | string } | undefined
    const message = typeof payload?.detail === 'object' ? payload.detail.message : payload?.detail
    throw new Error(message || `채점 서버 오류 (${response.status})`)
  }
  return response.json() as Promise<CircuitAttemptResult>
}

export async function reloadProblemCatalog() {
  const response = await fetch('/api/problems/reload', { method: 'POST' })
  if (!response.ok) {
    throw new Error(`문제 새로고침 오류 (${response.status})`)
  }
  return response.json() as Promise<ReloadStatistics>
}
