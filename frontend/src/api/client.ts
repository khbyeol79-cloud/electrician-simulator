import { authHeaders, currentAuthSession } from '../features/user/authSession'
import { activeUserStorageSuffix } from '../features/user/userProfile'

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
  wiring_semantics?: WiringSemantics | null
  capabilities: { board_visible: boolean; wiring_editable: boolean; wiring_gradable: boolean; operation_previewable: boolean; operation_gradable: boolean }
}

export const schematicUrl = (problemId: string) => `/api/problems/${encodeURIComponent(problemId)}/schematic`
export const layoutReferenceUrl = (problemId: string) => `/api/problems/${encodeURIComponent(problemId)}/layout-reference`
export const analysisReferenceUrl = (problemId: string, referenceId: string) => `/api/problems/${encodeURIComponent(problemId)}/analysis-reference/${encodeURIComponent(referenceId)}`

export type CircuitDevice = { device_id: string; device_type_id: string; label: string; socket_type_id: string | null; behavior_model_id?: string | null }
export type CircuitContact = { contact_id: string; owner_device_id: string; contact_type: 'NO' | 'NC' | 'CHANGEOVER'; normal_state: 'open' | 'closed'; controller_type?: 'coil' | 'timer' | 'protection' | 'flasher' | 'level'; controller_id?: string | null }
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
export type CircuitAnalysisDraft = {
  problem_id: string; problem_version: number; memo: string
  selected_device_ids: string[]; selected_socket_ids: string[]; selected_terminal_ids: string[]
  annotations: Record<string, string>; updated_at: string | null
}

export type BoardPin = { terminal_id: string; label: string; role_label?: string | null; number: number | null; side: 'top' | 'bottom'; x: number; y: number; max_connections: number; enabled: boolean; terminal_role?: 'functional' | 'free_junction' }
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
export type ExternalWiringTerminal = { terminal_id: string; label: string; terminal_role: 'external'; operation_terminal_id: string | null; max_connections: 1 | 2; wire_color: WiringConnection['wire_color'] }
export type ExternalWiringDevice = { device_id: string; label: string; placement: 'top' | 'bottom'; contact_type?: 'NO' | 'NC' | null; terminals: ExternalWiringTerminal[] }
export type WiringSemantics = { schema_version: '1.0'; extra_jumper_policy: 'ignore' | 'warning' | 'reject'; external_devices: ExternalWiringDevice[] }
export type WiringDraft = { problem_id: string; problem_version: number; mode: 'graphic' | 'summary'; connections: WiringConnection[]; updated_at: string | null }
export type PracticeSafetyIssue = { code: string; severity: 'warning' | 'blocking'; message: string }
export type StructuralWarning = PracticeSafetyIssue & { connection_indexes: number[] }
export type PracticeWiringDraft = WiringDraft & {
  workspace_id: string; workspace_name: string; source: 'user_practice_draft'; verified_answer: false; gradable: false
  created_at: string | null; latest_snapshot_id: string | null; structural_warnings: StructuralWarning[]
}
export type PracticeWiringWorkspace = {
  problem_id: string; problem_version: number; workspace_id: string; workspace_name: string
  created_at: string; updated_at: string; connection_count: number; latest_snapshot_id: string | null
}
export type PracticeWiringSnapshot = {
  snapshot_id: string; problem_id: string; problem_version: number; workspace_id: string; label: string | null
  created_at: string; connections: WiringConnection[]; structural_warnings: StructuralWarning[]
}
export type PracticeWiringExport = {
  schema_version: '1.0'; problem_id: string; problem_version: number; workspace_id: string; workspace_name: string
  snapshot_id: string | null; created_at: string | null; updated_at: string | null
  connections: WiringConnection[]; structural_warnings: StructuralWarning[]
}
export type WiringAttemptResult = {
  attempt_id: number | null; gradable: boolean; overall_correct: boolean | null; required_count: number; correct_count: number
  missing_connections: string[]; extra_connections: string[]; forbidden_connections: string[]; message: string
  electrically_equivalent?: boolean | null; used_alternative_tb_numbers?: boolean; required_net_count?: number; correct_net_count?: number
  missing_net_count?: number; merged_net_count?: number; extra_connection_count?: number; terminal_capacity_errors?: string[]; warnings?: string[]
  result_classification?: 'correct' | 'functionally_equivalent' | 'operates_but_incorrect' | 'incorrect' | 'ungradable'
  operation_requirements_passed?: boolean | null
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
  wiring_source: 'accepted_submission' | 'draft_preview' | 'practice_draft' | 'none'
  wiring_snapshot: { attempt_id: number; problem_version: number; connections: WiringConnection[] } | null
  wiring_submission: WiringProgress; wiring_exists: boolean; operation_ready: boolean
  preview_allowed: boolean; message: string; operation: OperationDefinition | null
  behavior_requirements?: {
    requirement_id: string; label: string; scenario_id?: string | null
    scenario_label?: string | null; next_action?: string | null
  }[]
}

export type OperationDefinition = {
  schema_version: '1.0'; simulation_status: 'preview' | 'functional'
  simulation_mode?: 'legacy_assisted' | 'actual_wiring'
  power: { line_terminal_id: string; return_terminal_id: string; phase_terminal_ids: string[] }
  controls: { control_id: string; label: string; control_type: 'pushbutton' | 'limit_switch' | 'selector'; mode: 'momentary' | 'maintained'; contact_type: 'NO' | 'NC'; terminal_a_id: string; terminal_b_id: string; alternate_terminal_a_id?: string | null; alternate_terminal_b_id?: string | null; initial_active: boolean }[]
  timers: { timer_id: string; label: string; coil_id: string; mode: 'on_delay'; delay_ms: number; timed_contact_ids: string[]; retentive: boolean }[]
  flashers?: { flasher_id: string; label: string; coil_id: string; interval_ms: number; contact_ids: string[] }[]
  level_relays?: { level_relay_id: string; label: string; supply_terminal_a_id: string; supply_terminal_b_id: string; electrode_terminal_ids: string[]; external_electrode_terminal_ids: string[]; contact_ids: string[] }[]
  indicators: { indicator_id: string; label: string; display_color: 'red' | 'green' | 'yellow' | 'white'; terminal_a_id: string; terminal_b_id: string }[]
  audible_outputs?: { output_id: string; label: string; terminal_a_id: string; terminal_b_id: string }[]
  motors: { motor_id: string; label: string; forward_coil_id: string | null; reverse_coil_id: string | null; phase_terminal_ids: string[]; phase_source_terminal_ids: string[]; forward_phase_order: number[] }[]
  contactors: { contactor_id: string; label: string; coil_id: string; role: 'forward' | 'reverse' | 'general'; start_control_id: string | null; motor_id: string | null }[]
  interlocks: { interlock_id: string; label: string; type: 'electrical' | 'mechanical'; contactor_ids: string[]; contact_ids: string[]; policy: 'prevent_simultaneous_activation' }[]
  protection_devices: { protection_device_id: string; label: string; protection_type: 'eocr'; protected_coil_ids: string[]; protected_motor_ids: string[]; protection_contact_ids?: string[]; supply_terminal_a_id?: string | null; supply_terminal_b_id?: string | null; reset_mode: 'manual' | 'automatic' | 'restart_required'; allowed_fault_types: 'overload'[] }[]
  fuse_channels?: { channel_id: string; label: string; terminal_a_id: string; terminal_b_id: string; initially_closed: boolean }[]
  direction_change_policy: 'current_direction_first' | 'first_input_first' | 'block_both' | 'stop_before_reverse'
  internal_connections: { from: string; to: string }[]
}
export type OperationControlState = { label: string; control_type: string; mode: string; contact_type: 'NO' | 'NC'; active: boolean }
export type OperationTimerState = { status: 'stopped' | 'timing' | 'completed' | 'reset'; elapsed_ms: number; delay_ms: number }
export type OperationFlasherState = { label: string; status: 'stopped' | 'off' | 'on'; elapsed_ms: number; interval_ms: number }
export type OperationLevelState = { label: string; requested: boolean; powered: boolean; wiring_ready: boolean; detected: boolean }
export type OperationFault = { code: string; message: string; severity: 'warning' | 'error' | 'danger'; trip_required: boolean }
export type OperationProtectionState = { label: string; protection_type: string; status: 'normal' | 'tripped' | 'reset_required'; reset_mode: string; powered?: boolean; operating_state?: 'unpowered' | 'powered_normal' | 'tripped' }
export type OperationFuseState = { label: string; status: 'normal' | 'open'; terminal_a_id: string; terminal_b_id: string }
export type OperationInterlockState = { label: string; type: 'electrical' | 'mechanical'; status: 'ready' | 'blocking' | 'fault'; blocked_contactor_id: string | null }
export type OperationSessionState = {
  session_id: string; problem_id: string; wiring_attempt_id: number; powered: boolean; power_state: 'off' | 'on' | 'tripped'
  simulation_mode?: 'legacy_assisted' | 'actual_wiring'; catalog_composed?: boolean
  controls: Record<string, OperationControlState>; coils: Record<string, boolean>; contacts: Record<string, 'open' | 'closed'>
  changeover_positions?: Record<string, 'nc' | 'no'>
  timers: Record<string, OperationTimerState>; flashers?: Record<string, OperationFlasherState>; level_relays?: Record<string, OperationLevelState>
  indicators: Record<string, 'off' | 'on' | 'error'>; audible_outputs?: Record<string, 'off' | 'on' | 'error'>
  motors: Record<string, 'stopped' | 'forward' | 'reverse' | 'phase_loss' | 'phase_sequence_error' | 'simultaneous_fault' | 'connection_error' | 'power_off' | 'protection_trip' | 'undetermined'>
  protections: Record<string, OperationProtectionState>; interlocks: Record<string, OperationInterlockState>; active_faults: string[]
  fuses?: Record<string, OperationFuseState>
  faults: OperationFault[]; stable: boolean; elapsed_ms: number; events: string[]
  session_type: 'verified_operation_session' | 'practice_preview_session' | 'free_circuit_session'; wiring_snapshot_id: number | null
  workspace_id: string | null; gradable: boolean; safety_status: 'not_checked' | 'safe' | 'attention' | 'blocked'
  power_permitted: boolean; safety_issues: PracticeSafetyIssue[]
}
export type OperationCheckResult = {
  gradable: boolean; overall_passed: boolean | null; passed_count: number; total_count: number
  results: { test_id: string; label: string; passed: boolean; message: string }[]; message: string
}
export type OperationProgress = { problem_id: string; attempt_count: number; last_submitted_at: string | null; last_overall_passed: boolean | null; last_gradable: boolean | null; last_passed_count: number; total_count: number; manual_run_count: number; last_run_at: string | null; forward_seen: boolean; reverse_seen: boolean; interlock_seen: boolean; protection_trip_seen: boolean }

export type FreeCircuitEditorState = { schema_version: '1.0'; mode: 'graphic' | 'summary'; template_id: string | null }
export type FreeCircuitDevicePlacement = { zone: 'internal_upper' | 'internal_lower' | 'external_top' | 'external_bottom'; row: number; column: number }
export type FreeCircuitInstalledDevice = { instance_id: string; palette_id: string; model_id: string; label: string; placement: FreeCircuitDevicePlacement; properties: Record<string, string | number | boolean> }
export type FreeCircuitAssembly = { schema_version: '1.0'; mode: 'editable' | 'fixed'; installed_devices: FreeCircuitInstalledDevice[] }
export type FreeCircuitMountingSlot = FreeCircuitDevicePlacement & { slot_id: string; x: number; y: number; width: number; height: number }
export type FreeCircuitPaletteItem = {
  palette_id: string; model_id: string; device_type_id: string; name: string; category: string
  mounting_kind: 'internal' | 'external'; default_zone: FreeCircuitDevicePlacement['zone']; socket_type_id: string | null
  definition_status: string; capabilities: string[]; default_properties: Record<string, string | number | boolean>
  max_instances: number | null; enabled: boolean; disabled_reason: string | null
}
export type FreeCircuitPalette = { items: FreeCircuitPaletteItem[]; slots: FreeCircuitMountingSlot[] }
export type FreeCircuitWorkspace = {
  workspace_id: string; schema_version: '1.0'; name: string
  circuit: CircuitDefinition; operation: OperationDefinition; connections: WiringConnection[]
  board: BoardDefinition | null; device_layout: DeviceLayoutDefinition | null
  wiring_semantics: WiringSemantics | null; assembly: FreeCircuitAssembly | null; editor: FreeCircuitEditorState; updated_at: string | null
}
export type FreeCircuitWorkspaceSummary = {
  workspace_id: string; name: string; schema_version: string; template_id: string | null
  connection_count: number; updated_at: string | null
}
export type FreeCircuitTemplate = {
  template_id: string; name: string; description: string; board: BoardDefinition
  circuit: CircuitDefinition; operation: OperationDefinition; device_layout: DeviceLayoutDefinition | null
  wiring_semantics: WiringSemantics | null; assembly: FreeCircuitAssembly | null
}
export type FreeCircuitDiagnostic = { severity: 'info' | 'warning' | 'error' | 'danger'; code: string; message: string }
export type FreeCircuitDiagnostics = { status: 'normal' | 'attention'; diagnostics: FreeCircuitDiagnostic[] }

export type ReloadStatistics = {
  loaded: number
  excluded: number
  warnings: number
}

const USER_ID_STORAGE_KEY = 'electrician.webUserId'

function requestHeaders(json = false): HeadersInit {
  const headers: Record<string, string> = authHeaders()
  if (json) headers['Content-Type'] = 'application/json'
  const userId = window.localStorage.getItem(USER_ID_STORAGE_KEY)
  if (userId && !currentAuthSession()?.required) {
    headers['X-User-Id'] = userId
  }
  return headers
}

async function getJson<T>(url: string, signal?: AbortSignal, headers = requestHeaders(), cache?: RequestCache): Promise<T> {
  const response = await fetch(url, { signal, headers, cache })
  if (!response.ok) {
    if (response.status === 401 && currentAuthSession()?.required) window.dispatchEvent(new Event('electrician:auth-expired'))
    throw new Error(`서버 응답 오류 (${response.status})`)
  }
  return response.json() as Promise<T>
}

export async function getSystemStatus(signal?: AbortSignal) {
  const [health, appInfo] = await Promise.all([
    getJson<HealthResponse>('/api/health', signal, undefined, 'no-store'),
    getJson<AppInfoResponse>('/api/app-info', signal, undefined, 'no-store'),
  ])
  return { health, appInfo }
}

export function getProblems(signal?: AbortSignal) {
  return getJson<ProblemSummary[]>('/api/problems', signal)
}

export function getFreeCircuitWorkspaces(signal?: AbortSignal) {
  return getJson<FreeCircuitWorkspaceSummary[]>('/api/free-circuits', signal)
}

export function getFreeCircuitTemplates(signal?: AbortSignal) {
  return getJson<FreeCircuitTemplate[]>('/api/free-circuits/templates', signal)
}

export function getFreeCircuitPalette(signal?: AbortSignal) {
  return getJson<FreeCircuitPalette>('/api/free-circuits/palette', signal)
}

export function getFreeCircuitWorkspace(workspaceId: string, signal?: AbortSignal) {
  return getJson<FreeCircuitWorkspace>(`/api/free-circuits/${encodeURIComponent(workspaceId)}`, signal)
}

export function createFreeCircuitWorkspace(name: string, templateId = 'basic_board_001') {
  return mutationJson<FreeCircuitWorkspace>('/api/free-circuits/workspaces', 'POST', { name, template_id: templateId })
}

export function addFreeCircuitDevice(workspaceId: string, paletteId: string, placement: FreeCircuitDevicePlacement) {
  return mutationJson<FreeCircuitWorkspace>(`/api/free-circuits/${encodeURIComponent(workspaceId)}/devices`, 'POST', { palette_id: paletteId, placement })
}

export function moveFreeCircuitDevice(workspaceId: string, instanceId: string, placement?: FreeCircuitDevicePlacement, properties?: Record<string, string | number | boolean>, label?: string) {
  return mutationJson<FreeCircuitWorkspace>(`/api/free-circuits/${encodeURIComponent(workspaceId)}/devices/${encodeURIComponent(instanceId)}`, 'PUT', { placement, properties, label })
}

export function deleteFreeCircuitDevice(workspaceId: string, instanceId: string, removeConnectedWires = false) {
  const suffix = removeConnectedWires ? '?remove_connected_wires=true' : ''
  return mutationJson<FreeCircuitWorkspace>(`/api/free-circuits/${encodeURIComponent(workspaceId)}/devices/${encodeURIComponent(instanceId)}${suffix}`, 'DELETE')
}

export function saveFreeCircuitWorkspace(workspace: FreeCircuitWorkspace) {
  const { workspace_id, updated_at: _updatedAt, ...payload } = workspace
  return mutationJson<FreeCircuitWorkspace>(`/api/free-circuits/${encodeURIComponent(workspace_id)}`, 'PUT', payload)
}

export function deleteFreeCircuitWorkspace(workspaceId: string) {
  return mutationJson<void>(`/api/free-circuits/${encodeURIComponent(workspaceId)}`, 'DELETE')
}

export function createFreeCircuitSession(workspaceId: string) {
  return mutationJson<OperationSessionState>(`/api/free-circuits/${encodeURIComponent(workspaceId)}/sessions`, 'POST')
}

export function getFreeCircuitDiagnostics(workspaceId: string) {
  return getJson<FreeCircuitDiagnostics>(`/api/free-circuits/${encodeURIComponent(workspaceId)}/diagnostics`)
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

const analysisSaves = new Map<string, Promise<CircuitAnalysisDraft>>()

export async function getCircuitAnalysisDraft(problemId: string, signal?: AbortSignal) {
  const headers = requestHeaders()
  const key = `${activeUserStorageSuffix()}:${problemId}`
  await analysisSaves.get(key)
  return getJson<CircuitAnalysisDraft | null>(`/api/problems/${encodeURIComponent(problemId)}/analysis-draft`, signal, headers)
}

export function saveCircuitAnalysisDraft(problemId: string, draft: Omit<CircuitAnalysisDraft, 'problem_id' | 'updated_at'>, userId = activeUserStorageSuffix()) {
  const key = `${userId}:${problemId}`
  const headers = { ...requestHeaders(true), ...(currentAuthSession()?.required ? { 'X-Session-User': userId } : { 'X-User-Id': userId }) }
  const save = (analysisSaves.get(key) ?? Promise.resolve()).catch(() => undefined).then(() =>
    mutationJson<CircuitAnalysisDraft>(`/api/problems/${encodeURIComponent(problemId)}/analysis-draft`, 'PUT', draft, headers))
  analysisSaves.set(key, save)
  void save.then(() => { if (analysisSaves.get(key) === save) analysisSaves.delete(key) }, () => { if (analysisSaves.get(key) === save) analysisSaves.delete(key) })
  return save
}

export function getBoard(problemId: string, signal?: AbortSignal) {
  return getJson<BoardDefinition>(`/api/problems/${encodeURIComponent(problemId)}/board`, signal)
}

export function getWiringDraft(problemId: string, signal?: AbortSignal) {
  return getJson<WiringDraft | null>(`/api/problems/${encodeURIComponent(problemId)}/wiring-draft`, signal)
}
export type BehaviorRequirementStatus = 'not_run' | 'satisfied' | 'unsatisfied' | 'unavailable'
export type BehaviorRequirementResult = { requirement_id: string; label: string; status: BehaviorRequirementStatus; message: string }
export type BehaviorScenarioResult = {
  scenario_id: string; label: string; status: BehaviorRequirementStatus
  current_observation: string; missing_conditions: string[]; next_action: string
}
export type BehaviorRequirementSummary = { gradable: false; results: BehaviorRequirementResult[]; scenarios: BehaviorScenarioResult[]; message: string }

export function getPracticeWiringDraft(problemId: string, workspaceId = 'main', signal?: AbortSignal) {
  return getJson<PracticeWiringDraft | null>(`/api/problems/${encodeURIComponent(problemId)}/practice-drafts/${encodeURIComponent(workspaceId)}`, signal)
}

export function getPracticeWiringWorkspaces(problemId: string, signal?: AbortSignal) {
  return getJson<PracticeWiringWorkspace[]>(`/api/problems/${encodeURIComponent(problemId)}/practice-workspaces`, signal)
}

export function getPracticeWiringSnapshots(problemId: string, workspaceId: string, signal?: AbortSignal) {
  return getJson<PracticeWiringSnapshot[]>(`/api/problems/${encodeURIComponent(problemId)}/practice-drafts/${encodeURIComponent(workspaceId)}/snapshots`, signal)
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

export function getOperationSetup(problemId: string, signal?: AbortSignal, workspaceId?: string) {
  const query = workspaceId && workspaceId !== 'main' ? `?workspace_id=${encodeURIComponent(workspaceId)}` : ''
  return getJson<OperationSetup>(`/api/problems/${encodeURIComponent(problemId)}/operation-setup${query}`, signal)
}

export function getOperationProgress(problemId: string, signal?: AbortSignal) {
  return getJson<OperationProgress>(`/api/problems/${encodeURIComponent(problemId)}/operation-progress`, signal)
}

export function createOperationSession(problemId: string, problemVersion: number, wiringAttemptId?: number) {
  return mutationJson<OperationSessionState>(`/api/problems/${encodeURIComponent(problemId)}/operation-sessions`, 'POST', { problem_version: problemVersion, wiring_attempt_id: wiringAttemptId })
}

export function createPracticeOperationSession(problemId: string, problemVersion: number, workspaceId = 'main') {
  return mutationJson<OperationSessionState>(`/api/problems/${encodeURIComponent(problemId)}/practice-sessions`, 'POST', { problem_version: problemVersion, workspace_id: workspaceId })
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

export function runOperationRequirements(sessionId: string) {
  return mutationJson<BehaviorRequirementSummary>(`/api/operation-sessions/${encodeURIComponent(sessionId)}/run-requirements`, 'POST')
}

export function deleteOperationSession(sessionId: string) {
  return mutationJson<void>(`/api/operation-sessions/${encodeURIComponent(sessionId)}`, 'DELETE')
}

async function mutationJson<T>(url: string, method: string, body?: unknown, headers = requestHeaders(body !== undefined)): Promise<T> {
  const response = await fetch(url, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
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

export function savePracticeWiringDraft(problemId: string, problemVersion: number, mode: 'graphic' | 'summary', connections: WiringConnection[], workspaceId = 'main', workspaceName?: string) {
  return mutationJson<PracticeWiringDraft>(`/api/problems/${encodeURIComponent(problemId)}/practice-drafts/${encodeURIComponent(workspaceId)}`, 'PUT', { problem_version: problemVersion, mode, connections, workspace_name: workspaceName })
}

export function createPracticeWiringWorkspace(problemId: string, problemVersion: number, workspaceName: string) {
  return mutationJson<PracticeWiringDraft>(`/api/problems/${encodeURIComponent(problemId)}/practice-workspaces`, 'POST', { problem_version: problemVersion, workspace_name: workspaceName })
}

export function createPracticeWiringSnapshot(problemId: string, workspaceId: string, label?: string) {
  return mutationJson<PracticeWiringSnapshot>(`/api/problems/${encodeURIComponent(problemId)}/practice-drafts/${encodeURIComponent(workspaceId)}/snapshots`, 'POST', { label })
}

export function clonePracticeWiringSnapshot(problemId: string, workspaceId: string, snapshotId: string) {
  return mutationJson<PracticeWiringDraft>(`/api/problems/${encodeURIComponent(problemId)}/practice-drafts/${encodeURIComponent(workspaceId)}/snapshots/${encodeURIComponent(snapshotId)}/clone`, 'POST')
}

export async function exportPracticeWiring(problemId: string, workspaceId: string): Promise<Blob> {
  const response = await fetch(`/api/problems/${encodeURIComponent(problemId)}/practice-drafts/${encodeURIComponent(workspaceId)}/export`, { headers: requestHeaders() })
  if (!response.ok) throw new Error('검증용 JSON을 내보낼 수 없습니다.')
  return response.blob()
}

export function importPracticeWiring(problemId: string, payload: PracticeWiringExport) {
  return mutationJson<PracticeWiringDraft>(`/api/problems/${encodeURIComponent(problemId)}/practice-imports`, 'POST', payload)
}

export function deletePracticeWiringDraft(problemId: string, workspaceId = 'main') {
  return mutationJson<void>(`/api/problems/${encodeURIComponent(problemId)}/practice-drafts/${encodeURIComponent(workspaceId)}`, 'DELETE')
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
    method: 'POST', headers: requestHeaders(true),
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
  const response = await fetch('/api/problems/reload', { method: 'POST', headers: requestHeaders() })
  if (!response.ok) {
    throw new Error(`문제 새로고침 오류 (${response.status})`)
  }
  return response.json() as Promise<ReloadStatistics>
}
