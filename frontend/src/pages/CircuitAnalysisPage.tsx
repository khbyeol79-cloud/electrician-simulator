import { useEffect, useMemo, useState } from 'react'
import {
  getCircuitProgress, getDiagram, getSocketTypes, submitCircuitAttempt,
  type CircuitAttemptResult, type CircuitProgress, type PublicProblemDetail,
  type SchematicDiagram, type SocketType,
} from '../api/client'
import { CircuitDiagram } from '../components/circuit/CircuitDiagram'
import { CircuitQuestionPanel } from '../components/circuit/CircuitQuestionPanel'
import { PlaceholderPage } from './PlaceholderPage'

type Draft = Record<string, Record<string, number>>

function draftKey(problem: PublicProblemDetail) {
  return `electrician.circuitDraft.${problem.problem_id}.v${problem.version}`
}

function restoreDraft(problem: PublicProblemDetail): Draft {
  try {
    const raw = window.localStorage.getItem(draftKey(problem))
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    return parsed && typeof parsed === 'object' ? parsed as Draft : {}
  } catch {
    window.localStorage.removeItem(draftKey(problem))
    return {}
  }
}

export function CircuitAnalysisPage({ problem }: { problem?: PublicProblemDetail }) {
  const [diagram, setDiagram] = useState<SchematicDiagram>()
  const [sockets, setSockets] = useState<SocketType[]>([])
  const [progress, setProgress] = useState<CircuitProgress>()
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null)
  const [draft, setDraft] = useState<Draft>({})
  const [result, setResult] = useState<CircuitAttemptResult>()
  const [error, setError] = useState<string>()
  const [notice, setNotice] = useState<string>()
  const [loading, setLoading] = useState(false)
  const selectedQuestion = useMemo(
    () => problem?.socket_questions.find((item) => item.question_id === selectedQuestionId),
    [problem, selectedQuestionId],
  )

  useEffect(() => {
    if (!problem) return
    const controller = new AbortController()
    setLoading(true)
    setError(undefined)
    setNotice(undefined)
    setResult(undefined)
    setSelectedQuestionId(null)
    setDraft(restoreDraft(problem))
    Promise.all([
      getDiagram(problem.problem_id, controller.signal),
      getSocketTypes(controller.signal),
      getCircuitProgress(problem.problem_id, controller.signal),
    ]).then(([nextDiagram, nextSockets, nextProgress]) => {
      setDiagram(nextDiagram)
      setSockets(nextSockets)
      setProgress(nextProgress)
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : '회로도를 불러올 수 없습니다.')
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [problem])

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setSelectedQuestionId(null)
    }
    window.addEventListener('keydown', listener)
    return () => window.removeEventListener('keydown', listener)
  }, [])

  useEffect(() => {
    const reset = () => { setDraft({}); setResult(undefined); setNotice(undefined); setSelectedQuestionId(null) }
    window.addEventListener('electrician:reset-circuit', reset)
    return () => window.removeEventListener('electrician:reset-circuit', reset)
  }, [])

  if (!problem) {
    return <PlaceholderPage stage="1단계" title="회로도 분석" description="상단에서 연습할 문제를 먼저 선택해 주세요." icon="⌁" />
  }

  const updateAnswer = (questionId: string, slotId: string, pin: number) => {
    const next = { ...draft, [questionId]: { ...(draft[questionId] ?? {}), [slotId]: pin } }
    setDraft(next)
    window.localStorage.setItem(draftKey(problem), JSON.stringify(next))
    setResult(undefined)
    setNotice(undefined)
  }
  const clearSelected = () => {
    if (!selectedQuestionId) return
    const next = { ...draft }
    delete next[selectedQuestionId]
    setDraft(next)
    window.localStorage.setItem(draftKey(problem), JSON.stringify(next))
    setResult(undefined)
  }
  const submit = async () => {
    const complete = problem.socket_questions.every((question) =>
      question.answer_slots.every((slot) => draft[question.question_id]?.[slot.slot_id]),
    )
    if (problem.socket_questions.length > 0 && !complete) {
      setNotice('아직 입력하지 않은 소켓번호가 있습니다. 모든 슬롯을 입력해 주세요.')
      return
    }
    try {
      setNotice(undefined)
      const nextResult = await submitCircuitAttempt(problem.problem_id, problem.version, draft)
      setResult(nextResult)
      setProgress((value) => ({ problem_id: problem.problem_id, attempt_count: (value?.attempt_count ?? 0) + 1, last_submitted_at: new Date().toISOString(), last_overall_correct: nextResult.overall_correct, last_correct_count: nextResult.correct_count, total_count: nextResult.total_count }))
    } catch (reason) {
      setNotice(reason instanceof Error ? reason.message : '채점 요청에 실패했습니다.')
    }
  }

  return <section className="workspace-page circuit-workspace">
    <header className="workspace-toolbar">
      <div><span>1단계 · SVG 회로도 분석</span><h2>회로도 분석</h2></div>
      <div className="circuit-overview" role="region" aria-label="회로 데이터 요약">
        <span>장치 {problem.circuit.devices.length}</span><span>단자 {problem.circuit.terminals.length}</span>
        <span>접점 {problem.circuit.contacts.length}</span><span>코일 {problem.circuit.coils.length}</span>
      </div>
    </header>
    {loading && <div className="circuit-loading">구조화된 회로도를 불러오는 중입니다.</div>}
    {error && <div className="circuit-load-error" role="alert"><strong>회로도를 표시할 수 없습니다.</strong><span>{error}</span><button type="button" onClick={() => window.location.reload()}>다시 불러오기</button></div>}
    {!loading && !error && diagram && <div className="circuit-layout">
      <CircuitDiagram key={problem.problem_id} diagram={diagram} questions={problem.socket_questions} selectedQuestionId={selectedQuestionId} draft={draft} result={result} onSelect={(id) => { setSelectedQuestionId(id); setNotice(undefined) }} onClear={() => setSelectedQuestionId(null)} />
      <CircuitQuestionPanel problem={problem} question={selectedQuestion} sockets={sockets} draft={draft} result={result} attemptCount={progress?.attempt_count ?? 0} notice={notice} onChange={updateAnswer} onSubmit={() => void submit()} onClear={clearSelected} />
    </div>}
  </section>
}
