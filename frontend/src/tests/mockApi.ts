import { vi } from 'vitest'
import type { BoardDefinition, BoardPin, ProblemSummary, PublicProblemDetail } from '../api/client'

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
  routing_channels: [{ channel_id: 'left', channel_type: 'left_outer', x: 20, y: 20, width: 30, height: 700 }], forbidden_areas: [],
} satisfies BoardDefinition

const health = {
  status: 'ok',
  app_name: '전기기능사 시퀀스 결선 시뮬레이터',
  version: '0.5.3',
}

const appInfo = {
  app_name: health.app_name,
  version: '0.5.3',
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

export function installApiMock(options?: { problems?: ProblemSummary[]; failProblems?: boolean }) {
  const problems = options?.problems ?? [problemSummary]
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    if (url === '/api/health') return response(health)
    if (url === '/api/app-info') return response(appInfo)
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
    if (url.endsWith('/board')) return response(wiringBoard)
    if (url.endsWith('/wiring-draft') && (!init?.method || init.method === 'GET')) return response(null)
    if (url.endsWith('/wiring-draft') && init?.method === 'PUT') {
      const body = JSON.parse(String(init.body))
      return response({ problem_id: url.includes('training_socket') ? 'training_socket_demo_001' : 'practice_001', ...body, updated_at: '2026-08-16T00:00:00' })
    }
    if (url.endsWith('/wiring-draft') && init?.method === 'DELETE') return response(undefined, 204)
    if (url.endsWith('/wiring-progress')) return response({ problem_id: 'training_socket_demo_001', attempt_count: 0, last_submitted_at: null, last_overall_correct: null, last_correct_count: 0, required_count: 8 })
    if (url.endsWith('/wiring-attempts/submit') && init?.method === 'POST') return response({ attempt_id: 1, gradable: true, overall_correct: false, required_count: 8, correct_count: 1, missing_connections: ['X1-6|MC1-5'], extra_connections: [], forbidden_connections: [], message: '누락 또는 잘못 연결된 단자를 확인해 주세요.' })
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
