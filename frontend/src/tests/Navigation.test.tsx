import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import App from '../App'
import { installApiMock } from './mockApi'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  window.localStorage.clear()
})

it('switches between the three exam stages', async () => {
  installApiMock()
  const user = userEvent.setup()
  render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)

  expect(screen.queryByText('0 / 3 완료')).not.toBeInTheDocument()
  expect(screen.getByRole('navigation', { name: '실습 단계' }).closest('header')).not.toBeNull()
  expect(screen.getByText('해당 프로그램은 동작 여부만 판별합니다')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: '설정' })).not.toBeInTheDocument()
  expect(screen.queryByRole('link', { name: /기구 장착/ })).not.toBeInTheDocument()
  for (const label of ['제어함 결선', '동작시험', '회로도 분석']) {
    await user.click(screen.getByRole('link', { name: new RegExp(label) }))
    expect(screen.getByRole('heading', { name: label, level: 2 })).toBeInTheDocument()
  }
})

it('redirects the old mounting route to operation', async () => {
  installApiMock()
  render(<MemoryRouter initialEntries={['/mounting']}><App /></MemoryRouter>)
  expect(screen.getByRole('heading', { name: '동작시험', level: 2 })).toBeInTheDocument()
})
