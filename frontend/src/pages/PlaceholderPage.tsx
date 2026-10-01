type PlaceholderPageProps = {
  stage: string
  title: string
  description: string
  icon: string
}

export function PlaceholderPage({ stage, title, description, icon }: PlaceholderPageProps) {
  return (
    <section className="workspace-page">
      <div className="workspace-toolbar">
        <div>
          <span>{stage}</span>
          <h2>{title}</h2>
        </div>
      </div>
      <div className="workspace-canvas">
        <div className="placeholder-card">
          <div className="placeholder-icon" aria-hidden="true">{icon}</div>
          <span>문제 선택 대기</span>
          <h3>{title}</h3>
          <p>{description}</p>
          <div className="coming-soon">상단의 현재 문제 메뉴에서 공개문제를 선택하면 학습을 시작할 수 있습니다.</div>
        </div>
      </div>
    </section>
  )
}
