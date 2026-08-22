import { useCallback, useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { getCircuitProgress, getOperationProgress, getWiringProgress, type PublicProblemDetail } from '../api/client'

const stages = [
  { number: 1, path: '/circuit', label: '회로도 분석', detail: '접점과 소켓번호 확인' },
  { number: 2, path: '/wiring', label: '제어함 결선', detail: '단자 및 전선 연결' },
  { number: 3, path: '/operation', label: '동작시험', detail: '완성 회로 작동 확인' },
]

const statusLabels = { draft: '작성 중', reviewed: '검토됨', verified: '검증 완료' }
const difficultyLabels = { beginner: '초급', intermediate: '중급', advanced: '고급' }

export function StageNavigation({ problem }: { problem?: PublicProblemDetail }) {
  const [completed, setCompleted] = useState(0)
  const refreshProgress = useCallback(async () => {
    if (!problem) { setCompleted(0); return }
    try {
      const [circuit, wiring, operation] = await Promise.all([
        getCircuitProgress(problem.problem_id), getWiringProgress(problem.problem_id), getOperationProgress(problem.problem_id),
      ])
      setCompleted(Number(circuit.last_overall_correct === true) + Number(wiring.last_overall_correct === true) + Number(operation.last_overall_passed === true))
    } catch { setCompleted(0) }
  }, [problem])

  useEffect(() => { void refreshProgress() }, [refreshProgress])
  useEffect(() => {
    const refresh = () => void refreshProgress()
    window.addEventListener('electrician:progress-changed', refresh)
    return () => window.removeEventListener('electrician:progress-changed', refresh)
  }, [refreshProgress])

  return (
    <aside className="stage-sidebar" aria-label="실습 단계">
      <div className="stage-title">
        <span>진행 단계</span>
        <strong>{completed} / 3 완료</strong>
      </div>
      <nav>
        {stages.map((stage) => (
          <NavLink
            key={stage.path}
            to={stage.path}
            className={({ isActive }) => `stage-link${isActive ? ' active' : ''}`}
          >
            <span className="stage-number">{stage.number}</span>
            <span className="stage-copy">
              <strong>{stage.label}</strong>
              <small>{stage.detail}</small>
            </span>
          </NavLink>
        ))}
        <NavLink to="/free-circuit" className={({ isActive }) => `stage-link free-stage${isActive ? ' active' : ''}`}>
          <span className="stage-number">∞</span><span className="stage-copy"><strong>자유회로 실험</strong><small>정답 없이 실제 결선 계산</small></span>
        </NavLink>
      </nav>
      <div className="problem-summary">
        <span>문제 정보</span>
        <strong>{problem?.title ?? '선택된 문제가 없습니다'}</strong>
        {problem ? (
          <dl>
            <div><dt>ID</dt><dd>{problem.problem_id}</dd></div>
            <div><dt>상태</dt><dd>{statusLabels[problem.status]}</dd></div>
            <div><dt>난이도</dt><dd>{difficultyLabels[problem.difficulty]}</dd></div>
            <div><dt>시간</dt><dd>{problem.estimated_minutes}분</dd></div>
            <div><dt>전원</dt><dd>{problem.power_supply.system}</dd></div>
          </dl>
        ) : (
          <p>상단의 현재 문제 영역에서 문제를 선택하세요.</p>
        )}
      </div>
    </aside>
  )
}
