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
          <span>준비 중</span>
          <h3>{title}</h3>
          <p>{description}</p>
          <div className="coming-soon">이 기능은 다음 개발 단계에서 구현됩니다.</div>
        </div>
      </div>
    </section>
  )
}
