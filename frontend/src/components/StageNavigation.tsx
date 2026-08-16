import { NavLink } from 'react-router-dom'

const stages = [
  { number: 1, path: '/circuit', label: '회로도 분석', detail: '접점과 소켓번호 확인' },
  { number: 2, path: '/wiring', label: '제어함 결선', detail: '단자 및 전선 연결' },
  { number: 3, path: '/mounting', label: '기구 장착', detail: '릴레이·타이머 장착' },
  { number: 4, path: '/operation', label: '동작시험', detail: '완성 회로 작동 확인' },
]

export function StageNavigation() {
  return (
    <aside className="stage-sidebar" aria-label="실습 단계">
      <div className="stage-title">
        <span>진행 단계</span>
        <strong>0 / 4 완료</strong>
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
      </nav>
      <div className="problem-summary">
        <span>문제 정보</span>
        <strong>선택된 문제가 없습니다</strong>
        <p>2단계에서 문제·답안 패키지를 연결합니다.</p>
      </div>
    </aside>
  )
}

