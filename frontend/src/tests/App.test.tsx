import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

const health = {
  status: 'ok',
  app_name: '전기기능사 시퀀스 결선 시뮬레이터',
  version: '0.1.0',
}
const appInfo = {
  app_name: health.app_name,
  version: '0.1.0',
  mode: 'web',
  database_ready: true,
  problems_path_ready: true,
}

afterEach(() => vi.restoreAllMocks())

describe('App', () => {
  it('renders Korean shell and server status', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => health })
      .mockResolvedValueOnce({ ok: true, json: async () => appInfo }))

    render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: '전기기능사 시퀀스 결선 시뮬레이터' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '회로도 분석', level: 2 })).toBeInTheDocument()
    await waitFor(() => expect(screen.getAllByText('준비됨')).toHaveLength(2))
  })

  it('shows a recoverable API error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('연결 실패')))
    render(<MemoryRouter initialEntries={['/circuit']}><App /></MemoryRouter>)
    expect(await screen.findByRole('alert')).toHaveTextContent('서버 연결을 확인해 주세요.')
    expect(screen.getByRole('button', { name: '다시 연결' })).toBeEnabled()
  })
})
