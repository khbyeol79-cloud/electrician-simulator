import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CircuitAnalysisPage } from '../pages/CircuitAnalysisPage'
import userEvent from '@testing-library/user-event'
import { installApiMock, problemDetail, trainingDetail } from './mockApi'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

describe('회로 데이터 진단', () => {
  it('edits and saves upper/lower terminals on the lower EOCR coil and square BZ symbol', async () => {
    const fetchMock = installApiMock()
    const user = userEvent.setup()
    const qnet = { ...problemDetail, problem_id: 'qnet_electrician_practical_001', problem_type: 'official' as const,
      capabilities: { ...problemDetail.capabilities, operation_gradable: false } }
    const { container, unmount } = render(<CircuitAnalysisPage problem={qnet} />)
    await user.click(await screen.findByRole('button', { name: '코일·표시등·부저 기호 25 번호 입력' }))
    await user.type(screen.getByLabelText('위쪽 단자'), '6')
    await user.type(screen.getByLabelText('아래쪽 단자'), '12')
    await user.click(screen.getByRole('button', { name: '코일·표시등·부저 기호 28 번호 입력' }))
    await user.type(screen.getByLabelText('위쪽 단자'), '1')
    await user.type(screen.getByLabelText('아래쪽 단자'), '2')
    const marker = container.querySelectorAll('.paired-annotation')[1]
    expect(marker.querySelectorAll('text')[0]).toHaveAttribute('y', '-38')
    expect(marker.querySelectorAll('text')[1]).toHaveAttribute('y', '54')
    unmount()
    await waitFor(() => {
      const saves = fetchMock.mock.calls.filter(([url, init]) => String(url).endsWith('/analysis-draft') && init?.method === 'PUT')
      const values = Object.values(JSON.parse(String(saves.at(-1)?.[1]?.body)).annotations).map(value => JSON.parse(String(value)))
      expect(values).toEqual(expect.arrayContaining([expect.objectContaining({kind:'body',label:'6',second:'12'}),expect.objectContaining({kind:'body',label:'1',second:'2'})]))
    })
  })
  it('opens horizontal and vertical contacts with two three-character fields and flushes on exit', async () => {
    const fetchMock = installApiMock()
    const user = userEvent.setup()
    const qnet = { ...problemDetail, problem_id: 'qnet_electrician_practical_001', problem_type: 'official' as const,
      capabilities: { ...problemDetail.capabilities, operation_gradable: false } }
    const { container, unmount } = render(<CircuitAnalysisPage problem={qnet} />)
    await user.click(await screen.findByRole('button', { name: '가로 접점 1 번호 입력' }))
    await user.type(screen.getByLabelText('왼쪽 단자'), 'A123')
    await user.type(screen.getByLabelText('오른쪽 단자'), '4')
    expect(screen.getByLabelText('왼쪽 단자')).toHaveValue('A12')
    const horizontal = container.querySelector('.paired-annotation')!
    expect(horizontal.querySelectorAll('text')[0]).toHaveAttribute('x', '-38')
    expect(horizontal.querySelectorAll('text')[1]).toHaveAttribute('x', '38')
    await user.click(screen.getByRole('button', { name: '세로 접점 8 번호 입력' }))
    await user.type(screen.getByLabelText('위쪽 단자'), '4')
    await user.type(screen.getByLabelText('아래쪽 단자'), '10')
    const vertical = container.querySelectorAll('.paired-annotation')[1]
    expect(vertical.querySelectorAll('text')[0]).toHaveAttribute('y', '-15')
    expect(vertical.querySelectorAll('text')[1]).toHaveAttribute('y', '29')
    await user.click(screen.getByRole('button', { name: '번호 왼쪽 이동' }))
    expect(vertical.querySelector('.annotation-labels')).toHaveAttribute('transform', 'translate(-8 0)')
    unmount()
    await waitFor(() => {
      const saves = fetchMock.mock.calls.filter(([url, init]) => String(url).endsWith('/analysis-draft') && init?.method === 'PUT')
      const body = JSON.parse(String(saves.at(-1)?.[1]?.body))
      const markers = Object.values(body.annotations).map(value => JSON.parse(String(value)))
      expect(markers).toEqual(expect.arrayContaining([
        expect.objectContaining({ orientation: 'horizontal', label: 'A12', second: '4' }),
        expect.objectContaining({ orientation: 'vertical', label: '4', second: '10', offsetX: -8 }),
      ]))
    })
  })

  it('renders the official PDF schematic background for an audited draft', async () => {
    installApiMock()
    const official = { ...problemDetail, problem_type: 'official' as const, source_type: 'official', status: 'draft' as const, socket_questions: [] }
    const { container } = render(<CircuitAnalysisPage problem={official} />)
    await screen.findByRole('img', { name: '시퀀스 회로도' })
    expect(container.querySelector('image')?.getAttribute('href')).toBe('/api/problems/practice_001/schematic')
  })

  it('shows the unselected state without requesting circuit data', () => {
    const fetchMock = installApiMock()
    render(<CircuitAnalysisPage />)
    expect(screen.getByText('상단에서 연습할 문제를 먼저 선택해 주세요.')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('renders exact 8P and 12P base arrangements', async () => {
    installApiMock()
    render(<CircuitAnalysisPage problem={problemDetail} />)
    expect(await screen.findByRole('region', { name: '회로 데이터 요약' })).toBeInTheDocument()
    expect(screen.getByText('상단 6 5 4 3')).toBeInTheDocument()
    expect(screen.getByText('하단 7 8 1 2')).toBeInTheDocument()
    expect(screen.getByText('상단 1 2 3 4 5 6')).toBeInTheDocument()
    expect(screen.getByText('하단 7 8 9 10 11 12')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: '시퀀스 회로도' })).toBeInTheDocument()
  })

  it('shows a recoverable catalog API error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 500, json: async () => ({}) } as Response)))
    render(<CircuitAnalysisPage problem={problemDetail} />)
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('회로도를 표시할 수 없습니다'))
  })

  it('selects a contact, restricts 8P pins, restores draft and grades', async () => {
    installApiMock()
    const user = userEvent.setup()
    const { container } = render(<CircuitAnalysisPage problem={trainingDetail} />)
    await screen.findByRole('img', { name: '시퀀스 회로도' })
    expect(container.querySelectorAll('.selection-box')).toHaveLength(0)
    expect(screen.getAllByRole('button', { name: /선택$/ })).toHaveLength(1)
    await user.click(await screen.findByRole('button', { name: 'VR1 VR1-C1 선택' }))
    expect(container.querySelectorAll('.selection-box')).toHaveLength(1)
    expect(screen.getByText('VR1-C1')).toBeInTheDocument()
    const upper = screen.getByLabelText('upper 소켓번호')
    expect(upper.querySelectorAll('option')).toHaveLength(9)
    await user.selectOptions(upper, '6')
    await user.selectOptions(screen.getByLabelText('lower 소켓번호'), '3')
    expect(screen.getByText('VR1-6')).toBeInTheDocument()
    expect(window.localStorage.getItem('electrician.circuitDraft.training_socket_demo_001.v1')).toContain('upper')
    await user.click(screen.getByRole('button', { name: '소켓번호 제출' }))
    expect(await screen.findByText('정답 ✓')).toBeInTheDocument()
  })

  it('selects VR1 by mouse even when the pointer moves inside its hit area', async () => {
    installApiMock()
    render(<CircuitAnalysisPage problem={trainingDetail} />)
    const hitbox = await screen.findByRole('button', { name: 'VR1 VR1-C1 선택' })
    const svg = screen.getByRole('img', { name: '시퀀스 회로도' })
    fireEvent.pointerDown(hitbox, { pointerId: 1, clientX: 100, clientY: 100 })
    fireEvent.pointerMove(svg, { pointerId: 1, clientX: 102, clientY: 101 })
    fireEvent.pointerUp(svg, { pointerId: 1, clientX: 102, clientY: 101 })
    fireEvent.click(hitbox)
    expect(screen.getByText('VR1-C1')).toBeInTheDocument()
  })

  it('supports zoom controls and incomplete submission warning', async () => {
    installApiMock()
    const user = userEvent.setup()
    render(<CircuitAnalysisPage problem={trainingDetail} />)
    await screen.findByRole('img', { name: '시퀀스 회로도' })
    await user.click(screen.getByRole('button', { name: '확대' }))
    expect(screen.getByText('115%')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '소켓번호 제출' }))
    expect(screen.getByRole('alert')).toHaveTextContent('아직 입력하지 않은')
  })

  it('keeps annotation autosave but hides obsolete analysis fields', async () => {
    const fetchMock = installApiMock()
    const qnet = {
      ...problemDetail,
      problem_id: 'qnet_electrician_practical_010', problem_type: 'official' as const,
      capabilities: { ...problemDetail.capabilities, operation_gradable: false },
      circuit: { ...problemDetail.circuit, devices: [{ device_id: 'X1', device_type_id: 'auxiliary_relay_8p', label: 'X1', socket_type_id: 'socket_8p_base' }] },
    }
    render(<CircuitAnalysisPage problem={qnet} />)
    await screen.findByRole('img', { name: '시퀀스 회로도' })
    expect(screen.getByRole('heading', { name: '회로도 분석', level: 2 })).toBeInTheDocument()
    expect(screen.queryByLabelText('회로 분석 메모')).not.toBeInTheDocument()
    expect(screen.queryByText('관찰 기구')).not.toBeInTheDocument()
    expect(screen.queryByText('확인 단자')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '소켓번호 제출' })).not.toBeInTheDocument()
    await waitFor(() => expect(fetchMock.mock.calls.some(([url, init]) => String(url).endsWith('/analysis-draft') && init?.method === 'PUT')).toBe(true), { timeout: 2000 })
  })

  it('restores editable slot-number marks and exposes the PDF page-5 layout', async () => {
    const markerId = 'marker:known-contact'
    const fetchMock = installApiMock({ analysisDraft: {
      problem_id: 'qnet_electrician_practical_010', problem_version: 1, memo: '',
      selected_device_ids: [], selected_socket_ids: [], selected_terminal_ids: [],
      annotations: { [markerId]: JSON.stringify({ x: 320, y: 240, label: '8' }) }, updated_at: '2026-09-17T00:00:00',
    } })
    const user = userEvent.setup()
    const qnet = {
      ...problemDetail,
      problem_id: 'qnet_electrician_practical_010', problem_type: 'official' as const,
      capabilities: { ...problemDetail.capabilities, operation_gradable: false },
    }
    render(<CircuitAnalysisPage problem={qnet} />)
    await user.click(await screen.findByRole('button', { name: '슬롯번호 8 선택' }))
    const input = screen.getByLabelText('선택한 슬롯번호')
    await user.clear(input)
    await user.type(input, '5')
    await user.click(screen.getByRole('button', { name: '배관·배치도' }))
    expect(screen.getByRole('img', { name: /배관 및 기구 배치도/ }).querySelector('image')).toHaveAttribute('href', '/api/problems/qnet_electrician_practical_010/layout-reference')
    await waitFor(() => {
      const save = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith('/analysis-draft') && init?.method === 'PUT')
      expect(String(save?.[1]?.body)).toContain('\\"label\\":\\"5\\"')
    }, { timeout: 2000 })
  })
})
