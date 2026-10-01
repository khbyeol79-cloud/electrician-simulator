import { useCallback, useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import {
  getProblem,
  getProblems,
  type ProblemSummary,
  type PublicProblemDetail,
} from './api/client'
import { Header } from './components/Header'
import { ProblemSelector } from './components/ProblemSelector'
import { StatusBar } from './components/StatusBar'
import { CircuitAnalysisPage } from './pages/CircuitAnalysisPage'
import { OperationTestPage } from './pages/OperationTestPage'
import { WiringPage } from './pages/WiringPage'
import { FreeCircuitPage } from './pages/FreeCircuitPage'
import { ServerAdminPage } from './pages/ServerAdminPage'
import { UserAccessDialog } from './components/UserAccessDialog'
import { loadUserProfile, saveNicknameProfile, shouldIntroduceUserAccess, useLegacyProfile } from './features/user/userProfile'
import { circuitDraftKey } from './features/circuit/circuitDraft'
import type { UserProfile } from './features/user/userProfile'
import { studyDraftStorage } from './features/user/authSession'
import { useServerStatus } from './features/system/useServerStatus'

export default function App({ account, onAccountOpen }: { account?: UserProfile; onAccountOpen?: () => void } = {}) {
  const navigate = useNavigate()
  const location = useLocation()
  const [refreshKey, setRefreshKey] = useState(0)
  const { info, connection, error } = useServerStatus(refreshKey)
  const [problems, setProblems] = useState<ProblemSummary[]>([])
  const [selectedProblem, setSelectedProblem] = useState<PublicProblemDetail>()
  const [problemDialogOpen, setProblemDialogOpen] = useState(false)
  const [problemLoading, setProblemLoading] = useState(true)
  const [problemError, setProblemError] = useState<string>()
  const [userProfile, setUserProfile] = useState(() => account ?? loadUserProfile())
  const [userDialogOpen, setUserDialogOpen] = useState(() => !account && shouldIntroduceUserAccess())
  const [userDialogCanClose, setUserDialogCanClose] = useState(!shouldIntroduceUserAccess())

  const refresh = useCallback(() => setRefreshKey((value) => value + 1), [])

  const selectProblem = useCallback(async (problemId: string, navigateToStart = false) => {
    try {
      setProblemError(undefined)
      const detail = await getProblem(problemId)
      setSelectedProblem(detail)
      window.localStorage.setItem('electrician.selectedProblemId', problemId)
      setProblemDialogOpen(false)
      if (navigateToStart) navigate('/circuit')
    } catch (reason) {
      setProblemError(reason instanceof Error ? reason.message : '문제를 불러올 수 없습니다.')
    }
  }, [navigate])

  const loadProblems = useCallback(async () => {
    setProblemLoading(true)
    setProblemError(undefined)
    try {
      const list = (await getProblems()).filter(item => item.problem_type === 'official' && item.source_type === 'official')
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

  useEffect(() => {
    void loadProblems()
  }, [loadProblems])

  return (
    <div className={`app-shell${location.pathname === '/admin' ? ' admin-shell' : ''}`}>
      <Header
        onRefresh={refresh}
        selectedProblem={selectedProblem}
        onOpenProblems={() => setProblemDialogOpen(true)}
        onReset={() => {
          if (!selectedProblem) return
          studyDraftStorage().removeItem(circuitDraftKey(selectedProblem.problem_id, selectedProblem.version))
          window.dispatchEvent(new CustomEvent('electrician:reset-circuit'))
          window.dispatchEvent(new CustomEvent('electrician:reset-wiring'))
        }}
        userProfile={userProfile}
        onOpenUser={onAccountOpen ?? (() => { setUserDialogCanClose(true); setUserDialogOpen(true) })}
      />
      <div className="app-body" key={userProfile.userId}>
        <main className="main-content">
          {error && (
            <div className="connection-alert" role="alert">
              <strong>서버 연결을 확인해 주세요.</strong>
              <span>{error}</span>
              <button type="button" onClick={refresh}>다시 연결</button>
            </div>
          )}
          <Routes>
            <Route path="/admin" element={<ServerAdminPage />} />
            <Route path="/" element={<Navigate to="/circuit" replace />} />
            <Route path="/circuit" element={<CircuitAnalysisPage problem={selectedProblem} />} />
            <Route path="/wiring" element={<WiringPage problem={selectedProblem} />} />
            <Route path="/mounting" element={<Navigate to="/operation" replace />} />
            <Route path="/operation" element={<OperationTestPage problem={selectedProblem} />} />
            <Route path="/free-circuit" element={<FreeCircuitPage />} />
            <Route path="*" element={<Navigate to="/circuit" replace />} />
          </Routes>
        </main>
      </div>
      <StatusBar info={info} connection={connection} />
      <ProblemSelector
        open={problemDialogOpen}
        problems={problems}
        selectedId={selectedProblem?.problem_id}
        loading={problemLoading}
        error={problemError}
        onClose={() => setProblemDialogOpen(false)}
        onSelect={(problemId) => void selectProblem(problemId, true)}
      />
      <UserAccessDialog
        open={userDialogOpen} current={userProfile} canClose={userDialogCanClose}
        onClose={() => setUserDialogOpen(false)}
        onNickname={(nickname) => {
          try {
            const next = saveNicknameProfile(nickname)
            setUserProfile(next)
            setUserDialogOpen(false)
            setUserDialogCanClose(true)
            setSelectedProblem(undefined)
            refresh()
            void loadProblems()
            return undefined
          } catch (reason) { return reason instanceof Error ? reason.message : '닉네임을 확인해 주세요.' }
        }}
        onLegacy={() => { setUserProfile(useLegacyProfile()); setUserDialogOpen(false); setUserDialogCanClose(true); setSelectedProblem(undefined); refresh(); void loadProblems() }}
      />
    </div>
  )
}
