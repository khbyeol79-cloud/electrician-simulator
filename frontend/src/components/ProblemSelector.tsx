import type { ProblemSummary } from '../api/client'

type Props = {
  open: boolean
  problems: ProblemSummary[]
  selectedId?: string
  loading: boolean
  error?: string
  onClose: () => void
  onSelect: (problemId: string) => void
}

const typeLabels: Record<string, string> = {
  official: '공식', reconstructed: '복원', variant: '변형', practice: '연습', original: '자체 제작',
}

export function ProblemSelector({
  open, problems, selectedId, loading, error, onClose, onSelect,
}: Props) {
  if (!open) return null
  const qnetProblems = problems.filter((problem) => problem.problem_type === 'official' && problem.source_type === 'official')

  const cards = (items: ProblemSummary[]) => items.map((problem) => (
    <button
      type="button"
      key={problem.problem_id}
      className={`problem-card${selectedId === problem.problem_id ? ' selected' : ''}`}
      onClick={() => onSelect(problem.problem_id)}
      disabled={!problem.selectable}
    >
      <div className="problem-card-heading">
        <span className="problem-type">{typeLabels[problem.problem_type]}</span>
      </div>
      <strong>{problem.title}</strong>
      <small>{problem.problem_id}</small>
      <div className="problem-tags">
        {problem.tags.filter((tag) => tag !== 'PDF대조중').map((tag) => <span key={tag}>#{tag}</span>)}
      </div>
    </button>
  ))

  return (
    <div className="problem-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="problem-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="problem-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header>
          <div>
            <span>학습 문제</span>
            <h2 id="problem-dialog-title">문제 선택</h2>
          </div>
          <div>
            <button type="button" className="close-button" onClick={onClose} aria-label="문제 선택 닫기">×</button>
          </div>
        </header>

        {error && <div className="problem-error" role="alert">{error}</div>}
        {loading && <div className="problem-empty">문제 목록을 불러오고 있습니다.</div>}
        {!loading && !error && qnetProblems.length === 0 && (
          <div className="problem-empty">
            <strong>사용할 수 있는 문제가 없습니다.</strong>
            <p>공식 Q-Net 공개문제 데이터가 준비되지 않았습니다.</p>
          </div>
        )}

        <div className="problem-catalog">
          <section className="problem-group" aria-label="Q-Net 공개문제 학습">
            <header><div><strong>Q-Net 공개문제 학습</strong><span>공식 공개문제만 사용하며 임의 추가·변형하지 않습니다.</span></div><b>{qnetProblems.length} / 18</b></header>
            {qnetProblems.length > 0 ? <div className="problem-list">{cards(qnetProblems)}</div> : <p className="problem-group-empty">현재 배포본에는 검증된 Q-Net 18문제 데이터가 아직 포함되지 않았습니다.</p>}
          </section>
        </div>
      </section>
    </div>
  )
}
