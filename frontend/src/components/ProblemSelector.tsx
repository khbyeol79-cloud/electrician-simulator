import type { ProblemSummary } from '../api/client'

type Props = {
  open: boolean
  problems: ProblemSummary[]
  selectedId?: string
  loading: boolean
  error?: string
  onClose: () => void
  onSelect: (problemId: string) => void
  onReload: () => void
}

const statusLabels = { draft: '작성 중', reviewed: '검토됨', verified: '검증 완료' }
const difficultyLabels = { beginner: '초급', intermediate: '중급', advanced: '고급' }
const typeLabels: Record<string, string> = {
  official: '공식', reconstructed: '복원', variant: '변형', practice: '연습', original: '자체 제작',
}

export function ProblemSelector({
  open, problems, selectedId, loading, error, onClose, onSelect, onReload,
}: Props) {
  if (!open) return null

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
            <button type="button" className="secondary-button" onClick={onReload} disabled={loading}>새로고침</button>
            <button type="button" className="close-button" onClick={onClose} aria-label="문제 선택 닫기">×</button>
          </div>
        </header>

        {error && <div className="problem-error" role="alert">{error}</div>}
        {loading && <div className="problem-empty">문제 목록을 불러오고 있습니다.</div>}
        {!loading && !error && problems.length === 0 && (
          <div className="problem-empty">
            <strong>사용할 수 있는 문제가 없습니다.</strong>
            <p>problems 폴더에 검증된 문제 패키지를 추가한 뒤 새로고침하세요.</p>
          </div>
        )}

        <div className="problem-list">
          {problems.map((problem) => (
            <button
              type="button"
              key={problem.problem_id}
              className={`problem-card${selectedId === problem.problem_id ? ' selected' : ''}`}
              onClick={() => onSelect(problem.problem_id)}
              disabled={!problem.selectable}
            >
              <div className="problem-card-heading">
                <span className={`problem-status ${problem.status}`}>{statusLabels[problem.status]}</span>
                <span className="problem-type">{typeLabels[problem.problem_type]}</span>
                {problem.warning_count > 0 && <span className="warning-count">경고 {problem.warning_count}</span>}
              </div>
              <strong>{problem.title}</strong>
              <small>{problem.problem_id} · v{problem.version}</small>
              <div className="problem-card-meta">
                <span>{difficultyLabels[problem.difficulty]}</span>
                <span>예상 {problem.estimated_minutes}분</span>
                <span>{problem.source_type}</span>
              </div>
              <div className="problem-tags">
                {problem.tags.map((tag) => <span key={tag}>#{tag}</span>)}
              </div>
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
