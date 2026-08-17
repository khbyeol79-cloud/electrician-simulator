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
  device_layout: DeviceLayoutDefinition | null
  operation: OperationDefinition | null
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

export type BoardPin = { terminal_id: string; label: string; role_label?: string | null; number: number | null; side: 'top' | 'bottom'; x: number; y: number; max_connections: number; enabled: boolean }
export type BoardRect = { x: number; y: number; width: number; height: number }
export type BoardItem = {
  item_id: string; label: string; item_type: 'socket_8p' | 'socket_12p' | 'terminal_block' | 'component'
  socket_type_id: string | null; row: number; x: number; y: number; width: number; height: number
  pins: BoardPin[]; label_area: BoardRect
}
export type BoardDefinition = {
  schema_version: '1.0'; board_id: string; layout_mode?: 'auto_rows' | 'fixed'; width: number; height: number; routing_margin: number
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
export type WiringProgress = { problem_id: string; attempt_count: number; last_submitted_at: string | null; last_overall_correct: boolean | null; last_gradable: boolean | null; last_correct_count: number; required_count: number }

export type MountDevice = {
  mount_device_id: string; label: string; device_type_id: string
  graphic_type: 'relay' | 'timer' | 'contactor'; compatible_socket_type_ids: string[]
}
export type MountTarget = {
  socket_id: string; socket_type_id: string; enabled: boolean; allowed_device_type_ids: string[]
}
export type MountingDefinition = {
  schema_version: '1.0'; available_devices: MountDevice[]; mount_targets: MountTarget[]
}
export type MountingPlacement = { mount_device_id: string; socket_id: string }
export type MountingDraft = {
  problem_id: string; problem_version: number; placements: MountingPlacement[]; updated_at: string | null
}
export type WrongMountingPlacement = { mount_device_id: string; submitted_socket_id: string }
export type MountingAttemptResult = {
  attempt_id: number | null; gradable: boolean; overall_correct: boolean | null
  required_count: number; correct_count: number; correct_device_ids: string[]
  missing_device_ids: string[]; missing_socket_ids: string[]
  wrong_placements: WrongMountingPlacement[]; extra_device_ids: string[]; message: string
}
export type MountingProgress = {
  problem_id: string; attempt_count: number; last_submitted_at: string | null
  last_overall_correct: boolean | null; last_correct_count: number; required_count: number
}

export type FixedDevicePlacement = {
  mount_device_id: string; label: string; device_type_id: string
  graphic_type: 'relay' | 'timer' | 'contactor'; socket_id: string; socket_type_id: string
}
export type DeviceLayoutDefinition = {
  schema_version: '1.0'; fixed_placements: FixedDevicePlacement[]
}
export type OperationSetup = {
  problem_id: string; problem_version: number; board: BoardDefinition
  device_layout: DeviceLayoutDefinition | null; wiring_draft: WiringDraft | null
  wiring_source: 'accepted_submission' | 'draft_preview' | 'none'
  wiring_snapshot: { attempt_id: number; problem_version: number; connections: WiringConnection[] } | null
  wiring_submission: WiringProgress; wiring_exists: boolean; operation_ready: boolean
  preview_allowed: boolean; message: string; operation: OperationDefinition | null
}

export type OperationDefinition = {
  schema_version: '1.0'; simulation_status: 'preview' | 'functional'
  power: { line_terminal_id: string; return_terminal_id: string; phase_terminal_ids: string[] }
  controls: { control_id: string; label: string; control_type: 'pushbutton' | 'limit_switch' | 'selector'; mode: 'momentary' | 'maintained'; contact_type: 'NO' | 'NC'; terminal_a_id: string; terminal_b_id: string; initial_active: boolean }[]
  timers: { timer_id: string; label: string; coil_id: string; mode: 'on_delay'; delay_ms: number; timed_contact_ids: string[]; retentive: boolean }[]
  indicators: { indicator_id: string; label: string; display_color: 'red' | 'green' | 'yellow' | 'white'; terminal_a_id: string; terminal_b_id: string }[]
  motors: { motor_id: string; label: string; forward_coil_id: string | null; reverse_coil_id: string | null; phase_terminal_ids: string[]; phase_source_terminal_ids: string[]; forward_phase_order: number[] }[]
  contactors: { contactor_id: string; label: string; coil_id: string; role: 'forward' | 'reverse' | 'general'; start_control_id: string | null; motor_id: string | null }[]
  interlocks: { interlock_id: string; label: string; type: 'electrical' | 'mechanical'; contactor_ids: string[]; contact_ids: string[]; policy: 'prevent_simultaneous_activation' }[]
  protection_devices: { protection_device_id: string; label: string; protection_type: 'eocr'; protected_coil_ids: string[]; protected_motor_ids: string[]; reset_mode: 'manual' | 'automatic' | 'restart_required'; allowed_fault_types: 'overload'[] }[]
  direction_change_policy: 'current_direction_first' | 'first_input_first' | 'block_both' | 'stop_before_reverse'
  internal_connections: { from: string; to: string }[]
}
export type OperationControlState = { label: string; control_type: string; mode: string; contact_type: string; active: boolean }
export type OperationTimerState = { status: 'stopped' | 'timing' | 'completed' | 'reset'; elapsed_ms: number; delay_ms: number }
export type OperationFault = { code: string; message: string; severity: 'warning' | 'error' | 'danger'; trip_required: boolean }
export type OperationProtectionState = { label: string; protection_type: string; status: 'normal' | 'tripped' | 'reset_required'; reset_mode: string }
export type OperationInterlockState = { label: string; type: 'electrical' | 'mechanical'; status: 'ready' | 'blocking' | 'fault'; blocked_contactor_id: string | null }
export type OperationSessionState = {
  session_id: string; problem_id: string; wiring_attempt_id: number; powered: boolean; power_state: 'off' | 'on' | 'tripped'
  controls: Record<string, OperationControlState>; coils: Record<string, boolean>; contacts: Record<string, 'open' | 'closed'>
  timers: Record<string, OperationTimerState>; indicators: Record<string, 'off' | 'on' | 'error'>
  motors: Record<string, 'stopped' | 'forward' | 'reverse' | 'phase_loss' | 'phase_sequence_error' | 'simultaneous_fault' | 'connection_error' | 'power_off' | 'protection_trip' | 'undetermined'>
  protections: Record<string, OperationProtectionState>; interlocks: Record<string, OperationInterlockState>; active_faults: string[]
  faults: OperationFault[]; stable: boolean; elapsed_ms: number; events: string[]
}
export type OperationCheckResult = {
  gradable: boolean; overall_passed: boolean | null; passed_count: number; total_count: number
  results: { test_id: string; label: string; passed: boolean; message: string }[]; message: string
}
export type OperationProgress = { problem_id: string; attempt_count: number; last_submitted_at: string | null; last_overall_passed: boolean | null; last_gradable: boolean | null; last_passed_count: number; total_count: number; manual_run_count: number; last_run_at: string | null; forward_seen: boolean; reverse_seen: boolean; interlock_seen: boolean; protection_trip_seen: boolean }

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

export function getMounting(problemId: string, signal?: AbortSignal) {
  return getJson<MountingDefinition | null>(`/api/problems/${encodeURIComponent(problemId)}/mounting`, signal)
}

export function getMountingDraft(problemId: string, signal?: AbortSignal) {
  return getJson<MountingDraft | null>(`/api/problems/${encodeURIComponent(problemId)}/mounting-draft`, signal)
}

export function getMountingProgress(problemId: string, signal?: AbortSignal) {
  return getJson<MountingProgress>(`/api/problems/${encodeURIComponent(problemId)}/mounting-progress`, signal)
}

export function getOperationSetup(problemId: string, signal?: AbortSignal) {
  return getJson<OperationSetup>(`/api/problems/${encodeURIComponent(problemId)}/operation-setup`, signal)
}

export function getOperationProgress(problemId: string, signal?: AbortSignal) {
  return getJson<OperationProgress>(`/api/problems/${encodeURIComponent(problemId)}/operation-progress`, signal)
}

export function createOperationSession(problemId: string, problemVersion: number, wiringAttemptId?: number) {
  return mutationJson<OperationSessionState>(`/api/problems/${encodeURIComponent(problemId)}/operation-sessions`, 'POST', { problem_version: problemVersion, wiring_attempt_id: wiringAttemptId })
}

export function applyOperationAction(sessionId: string, action: Record<string, unknown>) {
  return mutationJson<OperationSessionState>(`/api/operation-sessions/${encodeURIComponent(sessionId)}/actions`, 'POST', action)
}

export function resetOperationSession(sessionId: string) {
  return mutationJson<OperationSessionState>(`/api/operation-sessions/${encodeURIComponent(sessionId)}/reset`, 'POST')
}

export function runOperationCheck(sessionId: string) {
  return mutationJson<OperationCheckResult>(`/api/operation-sessions/${encodeURIComponent(sessionId)}/run-check`, 'POST')
}

export function deleteOperationSession(sessionId: string) {
  return mutationJson<void>(`/api/operation-sessions/${encodeURIComponent(sessionId)}`, 'DELETE')
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

export function saveMountingDraft(problemId: string, problemVersion: number, placements: MountingPlacement[]) {
  return mutationJson<MountingDraft>(`/api/problems/${encodeURIComponent(problemId)}/mounting-draft`, 'PUT', { problem_version: problemVersion, placements })
}

export function deleteMountingDraft(problemId: string) {
  return mutationJson<void>(`/api/problems/${encodeURIComponent(problemId)}/mounting-draft`, 'DELETE')
}

export function submitMountingAttempt(problemId: string, problemVersion: number, placements: MountingPlacement[]) {
  return mutationJson<MountingAttemptResult>(`/api/problems/${encodeURIComponent(problemId)}/mounting-attempts/submit`, 'POST', { problem_version: problemVersion, placements })
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
