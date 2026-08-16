import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }
type State = { failed: boolean }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('화면 렌더링 오류', error, info)
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="fatal-error">
          <h1>화면을 표시할 수 없습니다</h1>
          <p>프로그램을 다시 실행해 주세요. 문제가 계속되면 app.log를 확인해 주세요.</p>
          <button type="button" onClick={() => window.location.reload()}>다시 불러오기</button>
        </main>
      )
    }
    return this.props.children
  }
}

