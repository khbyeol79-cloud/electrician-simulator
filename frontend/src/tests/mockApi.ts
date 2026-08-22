import { vi } from 'vitest'
import type { BoardDefinition, BoardPin, MountingDefinition, MountingPlacement, OperationSessionState, OperationSetup, ProblemSummary, PublicProblemDetail, WiringAttemptResult, WiringConnection } from '../api/client'

export const problemSummary: ProblemSummary = {
  problem_id: 'practice_001',
  title: '기본 자기유지 회로 구조 연습',
  version: 1,
  problem_type: 'practice',
  status: 'draft',
  difficulty: 'beginner',
  estimated_minutes: 30,
  tags: ['자기유지', '구조확인용'],
  source_type: 'original',
  selectable: true,
  warning_count: 1,
}

export const problemDetail: PublicProblemDetail = {
  problem_id: problemSummary.problem_id,
  title: problemSummary.title,
  version: problemSummary.version,
  problem_type: problemSummary.problem_type,
  status: problemSummary.status,
  difficulty: problemSummary.difficulty,
  estimated_minutes: problemSummary.estimated_minutes,
  tags: problemSummary.tags,
  source_type: problemSummary.source_type,
  warning_count: problemSummary.warning_count,
  source_name: '자체 제작 구조 확인용 예제',
  description: '구조 확인용 예제입니다.',
  instructions: ['문제 정보를 확인하세요.'],
  learning_objectives: ['문제 선택 확인'],
  power_supply: {
    system: '3P3W_AC_220V',
    voltage: 220,
    frequency: 60,
    wire_colors: { L1: 'brown', L2: 'black', L3: 'gray', control: 'yellow' },
  },
  schematic: { file: 'schematic.svg', format: 'svg', view_box: '0 0 1200 700' },
  board: { layout_id: 'standard_two_motor_v1' },
  available_devices: [],
  circuit: { schema_version: '1.0', definition_status: 'structure_only', devices: [], terminals: [], contacts: [], coils: [] },
  socket_questions: [],
  device_layout: null,
  operation: null,
}

export const trainingDetail: PublicProblemDetail = {
  ...problemDetail,
  problem_id: 'training_socket_demo_001', title: '가상 소켓번호 입력 기능 확인', version: 1,
  status: 'reviewed', warning_count: 0,
  description: '실제 시험 정답이 아닌 프로그램 기능 확인용 가상 회로입니다.',
  circuit: {
    schema_version: '1.0', definition_status: 'structure_only',
    devices: [{ device_id: 'VR1', device_type_id: 'auxiliary_relay_8p', label: 'VR1 (가상)', socket_type_id: 'socket_8p_base' }],
    terminals: [], contacts: [{ contact_id: 'VR1-C1', owner_device_id: 'VR1', contact_type: 'NO', normal_state: 'open' }],
    coils: [{ coil_id: 'VR1-COIL', owner_device_id: 'VR1' }],
  },
  socket_questions: [{ question_id: 'SQ-VR1-C1', target_element_type: 'contact', target_element_id: 'VR1-C1', display_label: 'VR1 (가상)', answer_slots: [{ slot_id: 'upper', position: 'above' }, { slot_id: 'lower', position: 'below' }] }],
  device_layout: {
    schema_version: '1.0',
    fixed_placements: [
      { mount_device_id: 'DEVICE-X1', label: 'X1 보조릴레이', device_type_id: 'auxiliary_relay_8p', graphic_type: 'relay', socket_id: 'X1', socket_type_id: 'socket_8p_base' },
      { mount_device_id: 'DEVICE-MC1', label: 'MC1 12P 릴레이', device_type_id: 'auxiliary_relay_12p', graphic_type: 'contactor', socket_id: 'MC1', socket_type_id: 'socket_12p_base' },
    ],
  },
}

const pins8: BoardPin[] = [
  ...[6, 5, 4, 3].map((number, index) => ({ terminal_id: `X1-${number}`, label: String(number), number, side: 'top' as const, x: 130 + index * 35, y: 180, max_connections: 2, enabled: true })),
  ...[7, 8, 1, 2].map((number, index) => ({ terminal_id: `X1-${number}`, label: String(number), number, side: 'bottom' as const, x: 130 + index * 35, y: 340, max_connections: 2, enabled: true })),
]
const pins12: BoardPin[] = [
  ...[1, 2, 3, 4, 5, 6].map((number, index) => ({ terminal_id: `MC1-${number}`, label: String(number), number, side: 'top' as const, x: 480 + index * 32, y: 500, max_connections: 2, enabled: true })),
  ...[7, 8, 9, 10, 11, 12].map((number, index) => ({ terminal_id: `MC1-${number}`, label: String(number), number, side: 'bottom' as const, x: 480 + index * 32, y: 680, max_connections: 2, enabled: true })),
]

export const wiringBoard = {
  schema_version: '1.0', board_id: 'test_board', width: 900, height: 760, routing_margin: 35,
  items: [
    { item_id: 'X1', label: 'X1', item_type: 'socket_8p', socket_type_id: 'socket_8p_base', row: 1, x: 100, y: 180, width: 150, height: 160, pins: pins8, label_area: { x: 135, y: 235, width: 80, height: 50 } },
    { item_id: 'MC1', label: 'MC1', item_type: 'socket_12p', socket_type_id: 'socket_12p_base', row: 2, x: 450, y: 500, width: 200, height: 180, pins: pins12, label_area: { x: 500, y: 560, width: 100, height: 55 } },
  ],
  routing_channels: [
    { channel_id: 'top', channel_type: 'horizontal', x: 45, y: 120, width: 810, height: 40 },
    { channel_id: 'middle', channel_type: 'horizontal', x: 45, y: 400, width: 810, height: 40 },
    { channel_id: 'bottom', channel_type: 'horizontal', x: 45, y: 700, width: 810, height: 40 },
    { channel_id: 'left', channel_type: 'left_outer', x: 20, y: 20, width: 30, height: 700 },
    { channel_id: 'right', channel_type: 'right_outer', x: 850, y: 20, width: 30, height: 700 },
  ], forbidden_areas: [],
} satisfies BoardDefinition

export const mountingDefinition = {
  schema_version: '1.0',
  available_devices: [
    { mount_device_id: 'DEVICE-X1', label: 'X1 보조릴레이', device_type_id: 'auxiliary_relay_8p', graphic_type: 'relay', compatible_socket_type_ids: ['socket_8p_base'] },
    { mount_device_id: 'DEVICE-T1', label: 'T1 타이머', device_type_id: 'timer_8p', graphic_type: 'timer', compatible_socket_type_ids: ['socket_8p_base'] },
    { mount_device_id: 'DEVICE-MC1', label: 'MC1 12P 릴레이', device_type_id: 'auxiliary_relay_12p', graphic_type: 'contactor', compatible_socket_type_ids: ['socket_12p_base'] },
  ],
  mount_targets: [
    { socket_id: 'X1', socket_type_id: 'socket_8p_base', enabled: true, allowed_device_type_ids: ['auxiliary_relay_8p'] },
    { socket_id: 'MC1', socket_type_id: 'socket_12p_base', enabled: true, allowed_device_type_ids: ['auxiliary_relay_12p'] },
  ],
} satisfies MountingDefinition

const health = {
  status: 'ok',
  app_name: '전기기능사 시퀀스 결선 시뮬레이터',
  version: '0.11.3',
}

const appInfo = {
  app_name: health.app_name,
  version: '0.11.3',
  mode: 'web',
  database_ready: true,
  problems_path_ready: true,
}

function response(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  } as Response
}

export function installApiMock(options?: { problems?: ProblemSummary[]; failProblems?: boolean; board?: BoardDefinition; wiringDraft?: WiringConnection[]; wiringResult?: WiringAttemptResult; operationSetup?: Partial<OperationSetup>; mountingDraft?: MountingPlacement[]; mountingDraftVersion?: number; actualOperation?: boolean; freeCircuitSaveFailures?: number }) {
  const problems = options?.problems ?? [problemSummary]
  let operationState: OperationSessionState = {
    session_id: 'session-test', problem_id: 'training_socket_demo_001', wiring_attempt_id: 7,
    powered: false, power_state: 'off',
    simulation_mode: 'actual_wiring',
    catalog_composed: Boolean(options?.actualOperation),
    controls: {
      PB0: { label: 'PB0 정지', control_type: 'pushbutton', mode: 'momentary', contact_type: 'NC', active: false },
      PB1: { label: 'PB1 기동', control_type: 'pushbutton', mode: 'momentary', contact_type: 'NO', active: false },
      LS1: { label: 'LS1', control_type: 'limit_switch', mode: 'maintained', contact_type: 'NO', active: false },
    },
    coils: { 'MC1-COIL': false, 'T1-COIL': false }, contacts: { 'MC1-HOLD': 'open' },
    timers: { T1: { status: 'stopped', elapsed_ms: 0, delay_ms: 1000 } }, indicators: { GL: 'off' }, motors: { M1: 'stopped' },
    protections: { EOCR: { label: 'EOCR', protection_type: 'eocr', status: 'normal', reset_mode: 'manual' } },
    interlocks: { 'ELEC-MC1-MC2': { label: 'MC1·MC2 전기적 인터록', type: 'electrical', status: 'ready', blocked_contactor_id: null } },
    active_faults: [],
    faults: [], stable: true, elapsed_ms: 0, events: ['동작시험 세션 시작'],
  }
  const freeCircuit = {
    workspace_id: 'self_hold_01', schema_version: '1.0', name: '자기유지 자유회로',
    circuit: { ...trainingDetail.circuit, definition_status: 'functional' },
    operation: {
      schema_version: '1.0', simulation_status: 'functional', simulation_mode: 'actual_wiring',
      power: { line_terminal_id: 'X1-6', return_terminal_id: 'MC1-12', phase_terminal_ids: [] },
      controls: [], timers: [], indicators: [], motors: [], contactors: [], interlocks: [], protection_devices: [],
      direction_change_policy: 'block_both', internal_connections: [],
    },
    connections: [] as WiringConnection[], board: wiringBoard, device_layout: trainingDetail.device_layout,
    wiring_semantics: { schema_version: '1.0', extra_jumper_policy: 'warning', external_devices: [] },
    editor: { schema_version: '1.0', mode: 'graphic', template_id: 'basic_board_001' }, updated_at: null,
  }
  let freeCreated = false
  let freeCircuitSaveFailures = options?.freeCircuitSaveFailures ?? 0
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/health') return response(health)
    if (url === '/api/app-info') return response(appInfo)
    if (url === '/api/free-circuits/templates') return response([{ template_id: 'basic_board_001', name: '기본보드', description: '통합 기본보드', board: wiringBoard, circuit: freeCircuit.circuit, operation: freeCircuit.operation, device_layout: trainingDetail.device_layout, wiring_semantics: freeCircuit.wiring_semantics }])
    if (url === '/api/free-circuits' && (!init?.method || init.method === 'GET')) return response(freeCreated ? [{ workspace_id: freeCircuit.workspace_id, name: freeCircuit.name, schema_version: '1.0', template_id: 'basic_board_001', connection_count: freeCircuit.connections.length, updated_at: freeCircuit.updated_at }] : [])
    if (url === '/api/free-circuits/workspaces' && init?.method === 'POST') { freeCreated = true; return response(freeCircuit, 201) }
    if (url === '/api/free-circuits/self_hold_01' && (!init?.method || init.method === 'GET')) return response(freeCircuit)
    if (url === '/api/free-circuits/self_hold_01' && init?.method === 'PUT') {
      if (freeCircuitSaveFailures > 0) { freeCircuitSaveFailures -= 1; return response({ detail: '시험용 저장 실패' }, 500) }
      Object.assign(freeCircuit, JSON.parse(String(init.body))); return response(freeCircuit)
    }
    if (url === '/api/free-circuits/self_hold_01' && init?.method === 'DELETE') { freeCreated = false; return response(undefined, 204) }
    if (url === '/api/free-circuits/self_hold_01/sessions' && init?.method === 'POST') return response({ ...operationState, problem_id: 'free:self_hold_01' }, 201)
    if (url === '/api/free-circuits/self_hold_01/diagnostics') return response({ status: 'attention', diagnostics: [{ severity: 'warning', code: 'empty_wiring', message: '아직 연결된 전선이 없습니다.' }] })
    if (url === '/api/problems/reload' && init?.method === 'POST') {
      return response({ loaded: problems.length, excluded: 0, warnings: 1 })
    }
    if (url === '/api/problems') {
      if (options?.failProblems) return response({ detail: '오류' }, 500)
      return response(problems)
    }
    if (url === '/api/catalog/socket-types') return response([
      {
        socket_type_id: 'socket_8p_base', name: '8P 소켓 베이스', pin_count: 8,
        view_side: 'wiring_base_front',
        rows: [{ row_id: 'top', pins: [6, 5, 4, 3] }, { row_id: 'bottom', pins: [7, 8, 1, 2] }],
        center: { shape: 'octal', symmetric: true, label_area: true },
      },
      {
        socket_type_id: 'socket_12p_base', name: '12P 소켓 베이스', pin_count: 12,
        view_side: 'wiring_base_front',
        rows: [{ row_id: 'top', pins: [1, 2, 3, 4, 5, 6] }, { row_id: 'bottom', pins: [7, 8, 9, 10, 11, 12] }],
        center: { shape: 'circular', symmetric: true, label_area: true },
      },
    ])
    if (url === '/api/problems/practice_001/circuit-summary') return response({
      problem_id: 'practice_001', problem_title: problemDetail.title,
      device_count: 0, terminal_count: 0, contact_count: 0, coil_count: 0,
      socket_type_ids: [], reference_integrity: 'valid', warning_count: 1,
      definition_status: 'structure_only',
    })
    if (url === '/api/problems/practice_001/diagram') return response({
      schema_version: '1.0', view_box: { x: 0, y: 0, width: 1600, height: 900 },
      sections: [{ section_id: 'power', label: '주회로', bounds: { x: 20, y: 20, width: 430, height: 820 } }, { section_id: 'control', label: '제어회로', bounds: { x: 470, y: 20, width: 1110, height: 820 } }],
      elements: [], conductors: [],
    })
    if (url === '/api/problems/practice_001/circuit-progress') return response({ problem_id: 'practice_001', attempt_count: 0, last_submitted_at: null, last_overall_correct: null, last_correct_count: 0, total_count: 0 })
    if (url === '/api/problems/practice_001/circuit-attempts/submit' && init?.method === 'POST') return response({ attempt_id: 1, gradable: false, overall_correct: null, answered_count: 0, total_count: 0, correct_count: 0, message: '이 문제의 정답은 아직 검증되지 않아 채점할 수 없습니다.', results: [] })
    if (url === '/api/problems/training_socket_demo_001/diagram') return response({
      schema_version: '1.0', view_box: { x: 0, y: 0, width: 1600, height: 900 },
      sections: [{ section_id: 'power', label: '주회로', bounds: { x: 20, y: 20, width: 430, height: 820 } }, { section_id: 'control', label: '제어회로', bounds: { x: 470, y: 20, width: 1110, height: 820 } }],
      elements: [
        { element_id: 'power_title', element_type: 'power_label', section_id: 'power', circuit_ref_type: null, circuit_ref_id: null, question_id: null, x: 65, y: 80, width: 120, height: 40, orientation: 'horizontal', label: '3상 전원', interactive: false },
        { element_id: 'virtual_mccb', element_type: 'mccb', section_id: 'power', circuit_ref_type: null, circuit_ref_id: null, question_id: null, x: 140, y: 250, width: 130, height: 80, orientation: 'vertical', label: 'MCCB', interactive: false },
        { element_id: 'diagram_vr1_c1', element_type: 'contact_no', section_id: 'control', circuit_ref_type: 'contact', circuit_ref_id: 'VR1-C1', question_id: 'SQ-VR1-C1', x: 820, y: 270, width: 80, height: 100, orientation: 'vertical', label: 'VR1', interactive: true },
      ],
      conductors: [{ conductor_id: 'control_top', section_id: 'control', points: [{ x: 540, y: 150 }, { x: 1500, y: 150 }], line_style: 'control', junctions: [{ x: 860, y: 150 }] }],
    })
    if (url === '/api/problems/training_socket_demo_001/circuit-progress') return response({ problem_id: 'training_socket_demo_001', attempt_count: 0, last_submitted_at: null, last_overall_correct: null, last_correct_count: 0, total_count: 1 })
    if (url.endsWith('/board')) return response(options?.board ?? wiringBoard)
    if (url.endsWith('/wiring-draft') && (!init?.method || init.method === 'GET')) return response(options?.wiringDraft ? { problem_id: 'training_socket_demo_001', problem_version: 1, mode: 'graphic', connections: options.wiringDraft, updated_at: null } : null)
    if (url.endsWith('/wiring-draft') && init?.method === 'PUT') {
      const body = JSON.parse(String(init.body))
      return response({ problem_id: url.includes('training_socket') ? 'training_socket_demo_001' : 'practice_001', ...body, updated_at: '2026-08-16T00:00:00' })
    }
    if (url.endsWith('/wiring-draft') && init?.method === 'DELETE') return response(undefined, 204)
    if (url.endsWith('/wiring-progress')) return response({ problem_id: 'training_socket_demo_001', attempt_count: 0, last_submitted_at: null, last_overall_correct: null, last_gradable: null, last_correct_count: 0, required_count: 8 })
    if (url.endsWith('/wiring-attempts/submit') && init?.method === 'POST') return response(options?.wiringResult ?? { attempt_id: 1, gradable: true, overall_correct: false, required_count: 8, correct_count: 1, missing_connections: ['X1-6|MC1-5'], extra_connections: [], forbidden_connections: [], message: '누락 또는 잘못 연결된 단자를 확인해 주세요.' })
    if (url.endsWith('/operation-setup')) return response({
      problem_id: url.includes('training_socket') ? 'training_socket_demo_001' : 'practice_001',
      problem_version: 1,
      board: wiringBoard,
      device_layout: trainingDetail.device_layout,
      wiring_draft: options?.wiringDraft ? { problem_id: 'training_socket_demo_001', problem_version: 1, mode: 'graphic', connections: options.wiringDraft, updated_at: null } : null,
      wiring_source: 'draft_preview', wiring_snapshot: null,
      wiring_submission: { problem_id: 'training_socket_demo_001', attempt_count: 1, last_submitted_at: '2026-08-16T00:00:00', last_overall_correct: true, last_gradable: true, last_correct_count: 8, required_count: 8 },
      wiring_exists: Boolean(options?.wiringDraft?.length), operation_ready: false, preview_allowed: true,
      message: '이 문제에는 실제 동작 데이터가 없어 읽기 전용 미리보기만 제공합니다.', operation: null,
      ...options?.operationSetup,
    })
    if (url.endsWith('/operation-sessions') && init?.method === 'POST') return response(operationState, 201)
    if (url.endsWith('/actions') && init?.method === 'POST') {
      const body = JSON.parse(String(init.body)) as { action: string; value?: boolean; control_id?: string; milliseconds?: number; target_id?: string; fault_type?: string }
      if (body.action === 'set_power') operationState = { ...operationState, powered: Boolean(body.value), power_state: body.value ? 'on' : 'off', events: [...operationState.events, body.value ? '전원 ON' : '전원 OFF'] }
      if (body.action === 'press_control' && body.control_id) operationState = { ...operationState, controls: { ...operationState.controls, [body.control_id]: { ...operationState.controls[body.control_id], active: true } }, coils: body.control_id === 'PB1' ? { 'MC1-COIL': true, 'T1-COIL': true } : operationState.coils, motors: body.control_id === 'PB1' ? { M1: 'forward' } : operationState.motors, events: [...operationState.events, `${body.control_id} 작동`] }
      if (body.action === 'release_control' && body.control_id) operationState = { ...operationState, controls: { ...operationState.controls, [body.control_id]: { ...operationState.controls[body.control_id], active: false } }, events: [...operationState.events, `${body.control_id} 복귀`] }
      if (body.action === 'toggle_control' && body.control_id) operationState = { ...operationState, controls: { ...operationState.controls, [body.control_id]: { ...operationState.controls[body.control_id], active: !operationState.controls[body.control_id].active } } }
      if (body.action === 'advance_time') operationState = { ...operationState, elapsed_ms: operationState.elapsed_ms + (body.milliseconds ?? 0), timers: { T1: { status: 'completed', elapsed_ms: 1000, delay_ms: 1000 } }, indicators: { GL: 'on' } }
      if (body.action === 'trigger_fault' && body.target_id === 'EOCR') operationState = { ...operationState, coils: { 'MC1-COIL': false, 'T1-COIL': false }, motors: { M1: 'protection_trip' }, protections: { EOCR: { ...operationState.protections.EOCR, status: 'reset_required' } }, active_faults: ['EOCR'], events: [...operationState.events, 'EOCR가 과부하로 트립되었습니다.'] }
      if (body.action === 'reset_fault' && body.target_id === 'EOCR') operationState = { ...operationState, motors: { M1: 'stopped' }, protections: { EOCR: { ...operationState.protections.EOCR, status: 'normal' } }, active_faults: [], events: [...operationState.events, 'EOCR를 복귀했습니다.'] }
      return response(operationState)
    }
    if (url.endsWith('/run-check') && init?.method === 'POST') return response({ gradable: true, overall_passed: true, passed_count: 2, total_count: 2, results: [{ test_id: 'A', label: '자기유지', passed: true, message: '정상' }, { test_id: 'B', label: '타이머', passed: true, message: '정상' }], message: '모든 시험 조건이 정상적으로 작동했습니다.' })
    if (url.endsWith('/reset') && init?.method === 'POST') { operationState = { ...operationState, powered: false, power_state: 'off', coils: { 'MC1-COIL': false, 'T1-COIL': false }, indicators: { GL: 'off' }, motors: { M1: 'stopped' }, events: ['동작시험 초기화'] }; return response(operationState) }
    if (url.includes('/api/operation-sessions/') && init?.method === 'DELETE') return response(undefined, 204)
    if (url === '/api/problems/training_socket_demo_001/mounting') return response(mountingDefinition)
    if (url === '/api/problems/practice_001/mounting') return response({ schema_version: '1.0', available_devices: [], mount_targets: [] })
    if (url.endsWith('/mounting-draft') && (!init?.method || init.method === 'GET')) return response(options?.mountingDraft ? { problem_id: 'training_socket_demo_001', problem_version: options.mountingDraftVersion ?? 1, placements: options.mountingDraft, updated_at: null } : null)
    if (url.endsWith('/mounting-draft') && init?.method === 'PUT') {
      const body = JSON.parse(String(init.body))
      return response({ problem_id: 'training_socket_demo_001', ...body, updated_at: '2026-08-16T00:00:00' })
    }
    if (url.endsWith('/mounting-draft') && init?.method === 'DELETE') return response(undefined, 204)
    if (url.endsWith('/mounting-progress')) return response({ problem_id: 'training_socket_demo_001', attempt_count: 0, last_submitted_at: null, last_overall_correct: null, last_correct_count: 0, required_count: 3 })
    if (url.endsWith('/mounting-attempts/submit') && init?.method === 'POST') {
      const body = JSON.parse(String(init.body)) as { placements: MountingPlacement[] }
      const expected = new Map([['DEVICE-X1', 'X1'], ['DEVICE-MC1', 'MC1']])
      const correct = body.placements.filter((item) => expected.get(item.mount_device_id) === item.socket_id).map((item) => item.mount_device_id)
      const wrong = body.placements.filter((item) => expected.has(item.mount_device_id) && expected.get(item.mount_device_id) !== item.socket_id).map((item) => ({ mount_device_id: item.mount_device_id, submitted_socket_id: item.socket_id }))
      const missing = [...expected.keys()].filter((id) => !body.placements.some((item) => item.mount_device_id === id))
      const overall = correct.length === expected.size && wrong.length === 0 && body.placements.length === expected.size
      return response({ attempt_id: 1, gradable: true, overall_correct: overall, required_count: expected.size, correct_count: correct.length, correct_device_ids: correct, missing_device_ids: missing, missing_socket_ids: [...expected.entries()].filter(([id]) => !correct.includes(id)).map(([, socket]) => socket), wrong_placements: wrong, extra_device_ids: body.placements.filter((item) => !expected.has(item.mount_device_id)).map((item) => item.mount_device_id), message: overall ? '모든 기구의 장착 위치가 정확합니다.' : '장착 위치를 다시 확인해 주세요.' })
    }
    if (url === '/api/problems/training_socket_demo_001/circuit-attempts/submit' && init?.method === 'POST') {
      const body = JSON.parse(String(init.body)) as { responses: Record<string, Record<string, number>> }
      const correct = body.responses['SQ-VR1-C1']?.upper === 6 && body.responses['SQ-VR1-C1']?.lower === 3
      return response({ attempt_id: 1, gradable: true, overall_correct: correct, answered_count: 1, total_count: 1, correct_count: correct ? 1 : 0, message: correct ? '모든 답이 정확합니다.' : '입력한 소켓번호를 다시 확인해 주세요.', results: [{ question_id: 'SQ-VR1-C1', correct, slot_results: { upper: body.responses['SQ-VR1-C1']?.upper === 6, lower: body.responses['SQ-VR1-C1']?.lower === 3 } }] })
    }
    if (url === '/api/problems/practice_001') return response(problemDetail)
    return response({ detail: '찾을 수 없음' }, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
