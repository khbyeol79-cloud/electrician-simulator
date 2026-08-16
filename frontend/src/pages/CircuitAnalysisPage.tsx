import { PlaceholderPage } from './PlaceholderPage'
import type { PublicProblemDetail } from '../api/client'

export function CircuitAnalysisPage({ problem }: { problem?: PublicProblemDetail }) {
  if (!problem) {
    return <PlaceholderPage stage="1단계" title="회로도 분석" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="⌁" />
  }
  return (
    <PlaceholderPage
      stage="1단계"
      title="회로도 분석"
      description={`‘${problem.title}’ 문제 데이터가 정상적으로 불러와졌습니다. 회로도 상호작용은 다음 개발 단계에서 구현됩니다.`}
      icon="✓"
    />
  )
}
