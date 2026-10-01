import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { CircuitAnalysisPage } from '../pages/CircuitAnalysisPage'
import { DeviceInternalReference } from '../components/circuit/DeviceInternalReference'
import { Header } from '../components/Header'
import { contactTargets } from '../features/circuit/analysisAnnotations'
import { installApiMock, problemDetail } from './mockApi'

const qnet = { ...problemDetail, problem_id: 'qnet_electrician_practical_001', problem_type: 'official' as const,
  available_devices: ['EOCR', 'MC1', 'MC2', 'X', 'T', 'FR', 'FLS'].map(device_id => ({ device_id })),
  capabilities: { ...problemDetail.capabilities, operation_gradable: false } }

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); window.localStorage.clear() })

it.each(Array.from({ length: 18 }, (_, index) => index + 1))('opens the correct original 8/9-page references for problem %i', async number => {
  installApiMock()
  const user = userEvent.setup()
  const id = `qnet_electrician_practical_${String(number).padStart(3, '0')}`
  render(<CircuitAnalysisPage problem={{ ...qnet, problem_id: id }} />)
  await user.click(await screen.findByRole('button', { name: '동작사항' }))
  expect(screen.getByRole('img', { name: '제어회로 동작사항' }).querySelector('image')).toHaveAttribute('href', `/api/problems/${id}/analysis-reference/operation`)
  expect(screen.queryByRole('img', { name: '시퀀스 회로도' })).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: '기구 내부결선도' }))
  expect(screen.getByRole('img', { name: '기구 내부결선도' }).querySelector('image')).toHaveAttribute('href', `/api/problems/${id}/analysis-reference/internal`)
  await user.click(screen.getByRole('button', { name: '확대' }))
  expect(screen.getByText('115%')).toBeInTheDocument()
  expect(contactTargets(id).every(target => Boolean(target.deviceId))).toBe(true)
})

it('auto-selects EOCR, relay and timer; keeps entered numbers when switching references and restores old marks', async () => {
  const target = contactTargets(qnet.problem_id)[0]
  const fetchMock = installApiMock({ analysisDraft: {
    problem_id: qnet.problem_id, problem_version: 1, memo: '', selected_device_ids: [], selected_socket_ids: [], selected_terminal_ids: [],
    annotations: { [target.id]: JSON.stringify({ ...target, deviceId: undefined, label: '10', second: '4' }) }, updated_at: '2026-09-21T00:00:00',
  } })
  const user = userEvent.setup()
  const { unmount } = render(<CircuitAnalysisPage problem={qnet} />)
  await user.click(await screen.findByRole('button', { name: '슬롯번호 10 / 4 선택' }))
  expect(screen.getByRole('combobox', { name: '내부결선도 기구 선택' })).toHaveValue('EOCR')
  expect(screen.getByRole('img', { name: 'EOCR 내부결선도 · 공개문제 9쪽 원본' })).toHaveAttribute('src', expect.stringContaining('/eocr'))
  await user.click(screen.getByRole('button', { name: '동작사항' }))
  expect(screen.getByLabelText('왼쪽 단자')).toHaveValue('10')
  await user.click(screen.getByRole('button', { name: '시퀀스 회로도' }))
  await user.click(screen.getByRole('button', { name: '세로 접점 7 번호 입력' }))
  expect(screen.getByRole('combobox', { name: '내부결선도 기구 선택' })).toHaveValue('X')
  await user.type(screen.getByLabelText('위쪽 단자'), '8')
  await user.type(screen.getByLabelText('아래쪽 단자'), '6')
  await user.click(screen.getByRole('button', { name: '코일·표시등·부저 기호 31 번호 입력' }))
  expect(screen.getByRole('combobox', { name: '내부결선도 기구 선택' })).toHaveValue('T')
  await user.click(screen.getByRole('button', { name: 'T 내부결선도 확대' }))
  const dialog = screen.getByRole('dialog', { name: 'T 내부결선도' })
  expect(within(dialog).getByRole('img')).toHaveAttribute('src', expect.stringContaining('/timer'))
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  unmount()
  await waitFor(() => {
    const saves = fetchMock.mock.calls.filter(([url, init]) => String(url).endsWith('/analysis-draft') && init?.method === 'PUT')
    const annotations = JSON.parse(String(saves.at(-1)?.[1]?.body)).annotations
    const values = Object.values(annotations).map(value => JSON.parse(String(value)))
    expect(values).toEqual(expect.arrayContaining([expect.objectContaining({ label: '8', second: '6', deviceId: 'X' }), expect.objectContaining({ label: '10', second: '4' })]))
  })
})

it('does not show invented drawings for BZ and recovers from a missing image when another device is selected', () => {
  const { rerender } = render(<DeviceInternalReference problem={qnet} deviceId="BZ" onSelect={() => undefined} />)
  expect(screen.getByText(/BZ의 별도 내부결선도는 이 PDF에 없습니다/)).toBeInTheDocument()
  expect(screen.queryByRole('img')).not.toBeInTheDocument()
  rerender(<DeviceInternalReference problem={qnet} deviceId="EOCR" onSelect={() => undefined} />)
  fireEvent.error(screen.getByRole('img'))
  expect(screen.getByText(/그림을 불러오지 못했습니다/)).toBeInTheDocument()
  rerender(<DeviceInternalReference problem={qnet} deviceId="MC1" onSelect={() => undefined} />)
  expect(screen.getByRole('img')).toHaveAttribute('src', expect.stringContaining('/mc'))
})

it('lets the learner choose a reference for a manually added mark', async () => {
  installApiMock({ analysisDraft: { problem_id: qnet.problem_id, problem_version: 1, memo: '', selected_device_ids: [], selected_socket_ids: [], selected_terminal_ids: [], annotations: { 'marker:custom': JSON.stringify({ x: 10, y: 10, label: 'A1' }) }, updated_at: '' } })
  const user = userEvent.setup()
  render(<CircuitAnalysisPage problem={qnet} />)
  await user.click(await screen.findByRole('button', { name: '슬롯번호 A1 선택' }))
  await user.selectOptions(screen.getByRole('combobox', { name: '내부결선도 기구 선택' }), 'MC1')
  expect(screen.getByRole('img', { name: /MC1 내부결선도 ·/ })).toBeInTheDocument()
  expect(screen.getByLabelText('선택한 슬롯번호')).toHaveValue('A1')
})

it('opens help after reset, traps focus, closes with Escape and restores focus', async () => {
  const user = userEvent.setup()
  render(<MemoryRouter><Header onRefresh={() => undefined} onReset={() => undefined} onOpenProblems={() => undefined} onOpenUser={() => undefined} userProfile={{ nickname: '학생', userId: 'test', isLegacy: false }} /></MemoryRouter>)
  const help = screen.getByRole('button', { name: '사용법' })
  expect(help.previousElementSibling).toHaveTextContent('초기화')
  await user.click(help)
  const dialog = screen.getByRole('dialog', { name: '사용법' })
  expect(within(dialog).getAllByRole('heading', { level: 3 })).toHaveLength(6)
  await user.tab({ shift: true })
  expect(within(dialog).getByRole('button', { name: '사용법 닫기' })).toHaveFocus()
  await user.tab()
  expect(within(dialog).getByRole('button', { name: '사용법 닫기' })).toHaveFocus()
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(help).toHaveFocus()
})
