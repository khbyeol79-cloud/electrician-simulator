import type { CircuitAttemptResult, PublicProblemDetail, SocketQuestion, SocketType } from '../../api/client'

type Draft = Record<string, Record<string, number>>

export function CircuitQuestionPanel({ problem, question, sockets, draft, result, attemptCount, notice, onChange, onSubmit, onClear }: {
  problem: PublicProblemDetail; question?: SocketQuestion; sockets: SocketType[]; draft: Draft
  result?: CircuitAttemptResult; attemptCount: number; notice?: string
  onChange: (questionId: string, slotId: string, pin: number) => void; onSubmit: () => void; onClear: () => void
}) {
  const contact = question?.target_element_type === 'contact' ? problem.circuit.contacts.find((item) => item.contact_id === question.target_element_id) : undefined
  const coil = question?.target_element_type === 'coil' ? problem.circuit.coils.find((item) => item.coil_id === question.target_element_id) : undefined
  const ownerId = contact?.owner_device_id ?? coil?.owner_device_id
  const device = problem.circuit.devices.find((item) => item.device_id === ownerId)
  const socket = sockets.find((item) => item.socket_type_id === device?.socket_type_id)
  const pins = socket?.rows.flatMap((row) => row.pins).sort((a, b) => a - b) ?? []
  const values = question ? draft[question.question_id] ?? {} : {}
  const complete = problem.socket_questions.filter((item) => item.answer_slots.every((slot) => draft[item.question_id]?.[slot.slot_id])).length

  return <aside className="circuit-question-panel" aria-label="접점·소켓번호">
    <section><span className="panel-kicker">선택 요소</span>{question ? <><h3>{question.display_label}</h3><dl><div><dt>참조 ID</dt><dd>{question.target_element_id}</dd></div><div><dt>요소 종류</dt><dd>{contact ? `${contact.contact_type} 접점` : '코일'}</dd></div><div><dt>장치</dt><dd>{device?.label ?? '-'}</dd></div><div><dt>소켓</dt><dd>{socket?.name ?? '-'}</dd></div></dl></> : <p className="panel-empty">회로도의 파란 선택 가능 요소를 클릭하세요.</p>}</section>
    {question && <section><span className="panel-kicker">소켓번호 입력</span>{question.answer_slots.map((slot) => <label className="pin-select" key={slot.slot_id}><span>{slot.slot_id} · {slot.position}</span><select aria-label={`${slot.slot_id} 소켓번호`} value={values[slot.slot_id] ?? ''} onChange={(e) => onChange(question.question_id, slot.slot_id, Number(e.target.value))}><option value="">선택</option>{pins.map((pin) => <option key={pin} value={pin} disabled={Object.entries(values).some(([key, value]) => key !== slot.slot_id && value === pin)}>{pin}</option>)}</select><small>{values[slot.slot_id] ? `${device?.device_id}-${values[slot.slot_id]}` : '미입력'}</small></label>)}<button type="button" className="clear-answer" onClick={onClear}>선택 답안 지우기</button></section>}
    <section><span className="panel-kicker">진행 상태</span><div className="progress-count"><strong>{complete}</strong><span>/ {problem.socket_questions.length} 입력</span></div><p>제출 횟수 {attemptCount}회</p>{result && <div className={`grading-message ${result.gradable ? result.overall_correct ? 'correct' : 'wrong' : 'warning'}`} role="status"><strong>{result.gradable ? result.overall_correct ? '정답 ✓' : '오답 ✕' : '채점 불가 !'}</strong><span>{result.message}</span></div>}{notice && <div className="submission-notice" role="alert">{notice}</div>}<button type="button" className="submit-circuit" onClick={onSubmit}>소켓번호 제출</button></section>
    <section className="virtual-warning"><strong>학습 데이터 안내</strong><p>{problem.problem_id.startsWith('training_') ? '이 문제는 프로그램 기능 확인용 가상 회로이며 실제 시험 정답이 아닙니다.' : '정답이 미검증이면 입력은 가능하지만 채점하지 않습니다.'}</p></section>
    <section className="compact-sockets"><span className="panel-kicker">소켓 규격 데이터</span>{sockets.map((item) => <div key={item.socket_type_id}><strong>{item.pin_count}P</strong><span>상단 {item.rows[0].pins.join(' ')}</span><span>하단 {item.rows[1].pins.join(' ')}</span></div>)}</section>
  </aside>
}
