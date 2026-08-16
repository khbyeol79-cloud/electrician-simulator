import { useCallback, useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import {
  getProblem,
  getProblems,
  getSystemStatus,
  reloadProblemCatalog,
  type AppInfoResponse,
  type ProblemSummary,
  type PublicProblemDetail,
} from './api/client'
import { Header } from './components/Header'
import { ProblemSelector } from './components/ProblemSelector'
import { StageNavigation } from './components/StageNavigation'
import { StatusBar } from './components/StatusBar'
import { CircuitAnalysisPage } from './pages/CircuitAnalysisPage'
import { OperationTestPage } from './pages/OperationTestPage'
import { WiringPage } from './pages/WiringPage'

export default function App() {
  const [info, setInfo] = useState<AppInfoResponse>()
  const [error, setError] = useState<string>()
  const [refreshKey, setRefreshKey] = useState(0)
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [selectedProblem, setSelectedProblem] = useState<PublicProblemDetail>()
  const [problemDialogOpen, setProblemDialogOpen] = useState(false)
  const [problemLoading, setProblemLoading] = useState(true)
  const [problemError, setProblemError] = useState<string>()

  const refresh = useCallback(() => setRefreshKey((value) => value + 1), [])

  const selectProblem = useCallback(async (problemId: string) => {
    try {
      setProblemError(undefined)
      const detail = await getProblem(problemId)
      setSelectedProblem(detail)
      window.localStorage.setItem('electrician.selectedProblemId', problemId)
      setProblemDialogOpen(false)
    } catch (reason) {
      setProblemError(reason instanceof Error ? reason.message : '문제를 불러올 수 없습니다.')
    }
  }, [])

  const loadProblems = useCallback(async () => {
    setProblemLoading(true)
    setProblemError(undefined)
    try {
      const list = await getProblems()
      setProblems(list)
      const storedId = window.localStorage.getItem('electrician.selectedProblemId')
      if (storedId && list.some((problem) => problem.problem_id === storedId && problem.selectable)) {
        await selectProblem(storedId)
      } else if (storedId) {
        window.localStorage.removeItem('electrician.selectedProblemId')
        setSelectedProblem(undefined)
      }
    } catch (reason) {
      const detail = reason instanceof Error ? ` ${reason.message}` : ''
      setProblemError(`문제 목록을 불러올 수 없습니다.${detail}`)
    } finally {
      setProblemLoading(false)
    }
  }, [selectProblem])

  const reloadProblems = useCallback(async () => {
    setProblemLoading(true)
    setProblemError(undefined)
    try {
      await reloadProblemCatalog()
      await loadProblems()
    } catch (reason) {
      const detail = reason instanceof Error ? ` ${reason.message}` : ''
      setProblemError(`문제 목록을 새로고침할 수 없습니다.${detail}`)
      setProblemLoading(false)
    }
  }, [loadProblems])

  useEffect(() => {
    const controller = new AbortController()
    setError(undefined)
    getSystemStatus(controller.signal)
      .then(({ appInfo }) => setInfo(appInfo))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : '서버에 연결할 수 없습니다.')
        }
      })
    return () => controller.abort()
  }, [refreshKey])

  useEffect(() => {
    void loadProblems()
  }, [loadProblems])

  return (
    <div className="app-shell">
      <Header
        mode={info?.mode}
        onRefresh={refresh}
        selectedProblem={selectedProblem}
        onOpenProblems={() => setProblemDialogOpen(true)}
        onReset={() => {
          if (!selectedProblem) return
          window.localStorage.removeItem(`electrician.circuitDraft.${selectedProblem.problem_id}.v${selectedProblem.version}`)
          window.dispatchEvent(new CustomEvent('electrician:reset-circuit'))
          window.dispatchEvent(new CustomEvent('electrician:reset-wiring'))
        }}
      />
      <div className="app-body">
        <StageNavigation problem={selectedProblem} />
        <main className="main-content">
          {error && (
            <div className="connection-alert" role="alert">
              <strong>서버 연결을 확인해 주세요.</strong>
              <span>{error}</span>
              <button type="button" onClick={refresh}>다시 연결</button>
            </div>
          )}
          <Routes>
            <Route path="/" element={<Navigate to="/circuit" replace />} />
            <Route path="/circuit" element={<CircuitAnalysisPage problem={selectedProblem} />} />
            <Route path="/wiring" element={<WiringPage problem={selectedProblem} />} />
            <Route path="/mounting" element={<Navigate to="/operation" replace />} />
            <Route path="/operation" element={<OperationTestPage problem={selectedProblem} />} />
            <Route path="*" element={<Navigate to="/circuit" replace />} />
          </Routes>
        </main>
      </div>
      <StatusBar info={info} error={error} />
      <ProblemSelector
        open={problemDialogOpen}
        problems={problems}
        selectedId={selectedProblem?.problem_id}
        loading={problemLoading}
        error={problemError}
        onClose={() => setProblemDialogOpen(false)}
        onSelect={(problemId) => void selectProblem(problemId)}
        onReload={() => void reloadProblems()}
      />
    </div>
  )
}
