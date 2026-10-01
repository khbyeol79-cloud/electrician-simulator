import { render, screen, cleanup } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { PlaceholderPage } from '../pages/PlaceholderPage'

afterEach(cleanup)

it('guides a new account to choose a problem instead of claiming the feature is unimplemented', () => {
  render(<PlaceholderPage stage="1단계" title="회로도 분석" description="문제를 선택하세요." icon="⚡" />)
  expect(screen.getByText('상단의 현재 문제 메뉴에서 공개문제를 선택하면 학습을 시작할 수 있습니다.')).toBeInTheDocument()
  expect(screen.queryByText(/다음 개발 단계/)).not.toBeInTheDocument()
})
