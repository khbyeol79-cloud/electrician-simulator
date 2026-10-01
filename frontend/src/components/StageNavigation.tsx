import { NavLink } from 'react-router-dom'

export function StageNavigation() {
  return <nav className="header-stages" aria-label="실습 단계">
    {[
      ['/circuit', '회로도 분석'], ['/wiring', '제어함 결선'], ['/operation', '동작시험'],
    ].map(([path, label]) => <NavLink key={path} to={path} className={({ isActive }) => isActive ? 'active' : ''}>{label}</NavLink>)}
  </nav>
}
