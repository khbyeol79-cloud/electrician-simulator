import { useCallback, useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { getSystemStatus, type AppInfoResponse } from './api/client'
import { Header } from './components/Header'
import { StageNavigation } from './components/StageNavigation'
import { StatusBar } from './components/StatusBar'
import { CircuitAnalysisPage } from './pages/CircuitAnalysisPage'
import { DeviceMountingPage } from './pages/DeviceMountingPage'
import { OperationTestPage } from './pages/OperationTestPage'
import { WiringPage } from './pages/WiringPage'

export default function App() {
  const [info, setInfo] = useState<AppInfoResponse>()
  const [error, setError] = useState<string>()
  const [refreshKey, setRefreshKey] = useState(0)

  const refresh = useCallback(() => setRefreshKey((value) => value + 1), [])

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

  return (
    <div className="app-shell">
      <Header mode={info?.mode} onRefresh={refresh} />
      <div className="app-body">
        <StageNavigation />
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
            <Route path="/circuit" element={<CircuitAnalysisPage />} />
            <Route path="/wiring" element={<WiringPage />} />
            <Route path="/mounting" element={<DeviceMountingPage />} />
            <Route path="/operation" element={<OperationTestPage />} />
            <Route path="*" element={<Navigate to="/circuit" replace />} />
          </Routes>
        </main>
      </div>
      <StatusBar info={info} error={error} />
    </div>
  )
}

