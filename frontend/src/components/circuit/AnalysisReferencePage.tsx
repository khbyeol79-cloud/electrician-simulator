import { analysisReferenceUrl } from '../../api/client'
import { layoutReferenceDiagram } from '../../features/circuit/analysisAnnotations'
import { CircuitDiagram } from './CircuitDiagram'

export function AnalysisReferencePage({ problemId, kind }: { problemId: string; kind: 'operation' | 'internal' }) {
  const title = kind === 'operation' ? '제어회로 동작사항' : '기구 내부결선도'
  return <section className="layout-reference-stage" aria-label={title}>
    <header><strong>{title}</strong><span>공개문제 원본 · {kind === 'operation' ? 8 : 9}쪽</span></header>
    <CircuitDiagram key={`${problemId}-${kind}`} diagram={layoutReferenceDiagram} questions={[]} selectedQuestionId={null} draft={{}}
      readOnly ariaLabel={title} backgroundHref={analysisReferenceUrl(problemId, kind)} onSelect={() => undefined} onClear={() => undefined} />
  </section>
}
