import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import App from '../App'

afterEach(() => vi.restoreAllMocks())

it('switches between all four stages', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      status: 'ok', app_name: 'test', version: '0.1.0', mode: 'web',
      database_ready: true, problems_path_ready: true,
    }),
  }))
  const user = userEvent.setup()
  render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)

  for (const label of ['제어함 결선', '기구 장착', '동작시험', '회로도 분석']) {
    await user.click(screen.getByRole('link', { name: new RegExp(label) }))
    expect(screen.getByRole('heading', { name: label, level: 2 })).toBeInTheDocument()
  }
})
