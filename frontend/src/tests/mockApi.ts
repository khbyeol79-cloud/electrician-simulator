import { vi } from 'vitest'
import type { ProblemSummary, PublicProblemDetail } from '../api/client'

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
    wire_colors: { L1: 'brown', L2: 'black', L3: 'gray', PE: 'green', control: 'yellow' },
  },
  schematic: { file: 'schematic.svg', format: 'svg', view_box: '0 0 1200 700' },
  board: { layout_id: 'standard_two_motor_v1' },
  available_devices: [],
  circuit: { devices: [], terminals: [], contacts: [], coils: [] },
  socket_questions: [],
}

const health = {
  status: 'ok',
  app_name: '전기기능사 시퀀스 결선 시뮬레이터',
  version: '0.3.0',
}

const appInfo = {
  app_name: health.app_name,
  version: '0.3.0',
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
    if (url === '/api/problems/practice_001') return response(problemDetail)
    return response({ detail: '찾을 수 없음' }, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
