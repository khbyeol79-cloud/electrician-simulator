import type { CircuitAttemptResult, DiagramElement, SchematicDiagram, SocketQuestion } from '../../api/client'
import { useSvgViewport } from './useSvgViewport'

type Draft = Record<string, Record<string, number>>

function ElementShape({ element }: { element: DiagramElement }) {
  const { x, y, width: w, height: h } = element
  const cx = x + w / 2
  const cy = y + h / 2
  const poleXs = [x + w / 4, x + w / 2, x + (w * 3) / 4]
  switch (element.element_type) {
    case 'terminal':
      return <g className="symbol-stroke terminal-symbol"><line x1={cx} y1={y} x2={cx} y2={cy - 7} /><circle cx={cx} cy={cy} r="7" /><line x1={cx} y1={cy + 7} x2={cx} y2={y + h} /></g>
    case 'contact_no':
    case 'contact_nc':
    case 'push_button_no':
    case 'push_button_nc':
    case 'timer_contact':
      return <g className="symbol-stroke"><line x1={cx} y1={y + 8} x2={cx} y2={cy - 16} /><circle cx={cx} cy={cy - 16} r="5" /><circle cx={cx} cy={cy + 16} r="5" /><line x1={cx} y1={cy + 16} x2={element.element_type.includes('nc') ? cx : cx + 22} y2={cy - 12} /><line x1={cx} y1={cy + 16} x2={cx} y2={y + h - 8} /></g>
    case 'coil':
      return <g className="symbol-stroke"><line x1={x} y1={cy} x2={x + 16} y2={cy} /><ellipse cx={cx} cy={cy} rx={w / 2 - 16} ry={h / 2 - 8} /><line x1={x + w - 16} y1={cy} x2={x + w} y2={cy} /></g>
    case 'indicator_lamp':
      return <g className="symbol-stroke"><circle cx={cx} cy={cy} r={Math.min(w, h) / 2 - 7} /><line x1={cx - 16} y1={cy - 16} x2={cx + 16} y2={cy + 16} /><line x1={cx + 16} y1={cy - 16} x2={cx - 16} y2={cy + 16} /></g>
    case 'motor':
      return <g className="symbol-stroke"><circle cx={cx} cy={cy} r={Math.min(w, h) / 2 - 5} /><text x={cx} y={cy + 9} textAnchor="middle">M</text></g>
    case 'mccb':
      return <g className="symbol-stroke three-pole-symbol"><rect x={x + 4} y={y + 4} width={w - 8} height={h - 8} rx="3" />{poleXs.map((poleX) => <g key={poleX}><line x1={poleX} y1={y} x2={poleX} y2={cy - 13} /><circle cx={poleX} cy={cy - 13} r="4" /><circle cx={poleX} cy={cy + 13} r="4" /><line x1={poleX} y1={cy + 13} x2={poleX + 13} y2={cy - 9} /><line x1={poleX} y1={cy + 13} x2={poleX} y2={y + h} /></g>)}</g>
    case 'magnetic_contactor':
      return <g className="symbol-stroke three-pole-symbol">{poleXs.map((poleX) => <g key={poleX}><line x1={poleX} y1={y} x2={poleX} y2={cy - 13} /><circle cx={poleX} cy={cy - 13} r="4" /><circle cx={poleX} cy={cy + 13} r="4" /><line x1={poleX} y1={cy + 13} x2={poleX + 13} y2={cy - 9} /><line x1={poleX} y1={cy + 13} x2={poleX} y2={y + h} /></g>)}</g>
    case 'eocr':
      return <g className="symbol-stroke eocr-symbol">{poleXs.map((poleX) => <g key={poleX}><line x1={poleX} y1={y} x2={poleX} y2={y + 8} /><line x1={poleX} y1={y + h - 8} x2={poleX} y2={y + h} /></g>)}<rect x={x + 4} y={y + 8} width={w - 8} height={h - 16} /><text x={cx} y={cy + 7} textAnchor="middle">EOCR</text></g>
    case 'fuse':
      return <g className="symbol-stroke fuse-symbol"><line x1={x} y1={cy} x2={x + w * .2} y2={cy} /><rect x={x + w * .2} y={y + 5} width={w * .6} height={h - 10} /><line x1={x + w * .8} y1={cy} x2={x + w} y2={cy} /></g>
    case 'ground':
      return <g className="symbol-stroke ground-symbol"><line x1={cx} y1={y} x2={cx} y2={y + h * .35} /><line x1={x + w * .15} y1={y + h * .35} x2={x + w * .85} y2={y + h * .35} /><line x1={x + w * .28} y1={y + h * .55} x2={x + w * .72} y2={y + h * .55} /><line x1={x + w * .4} y1={y + h * .75} x2={x + w * .6} y2={y + h * .75} /></g>
    case 'junction':
      return <circle className="junction-dot" cx={cx} cy={cy} r="6" />
    case 'text':
    case 'power_label':
      return <text className="diagram-note" x={cx} y={cy} textAnchor="middle">{element.label}</text>
    default:
      return <g className="symbol-stroke"><rect x={x + 5} y={y + 5} width={w - 10} height={h - 10} /><text x={cx} y={cy + 6} textAnchor="middle">{element.label}</text></g>
  }
}

function AnswerMarkers({ element, question, draft, result }: { element: DiagramElement; question?: SocketQuestion; draft: Draft; result?: CircuitAttemptResult }) {
  if (!question) return null
  const values = draft[question.question_id] ?? {}
  const slotResult = result?.results.find((item) => item.question_id === question.question_id)?.slot_results
  return <g className="answer-marker-layer">
    {question.answer_slots.map((slot) => {
      const value = values[slot.slot_id]
      const x = slot.position === 'left' ? element.x - 34 : slot.position === 'right' ? element.x + element.width + 34 : element.x + element.width / 2
      const y = slot.position === 'above' ? element.y - 28 : slot.position === 'below' ? element.y + element.height + 28 : element.y + element.height / 2
      const state = slotResult?.[slot.slot_id] === true ? 'correct' : slotResult?.[slot.slot_id] === false ? 'wrong' : value ? 'entered' : 'empty'
      return <g key={slot.slot_id} className={`answer-marker ${state}`} transform={`translate(${x} ${y})`}><circle r="20" /><text textAnchor="middle" y="6">{value ?? '!'}</text></g>
    })}
  </g>
}

export function CircuitDiagram({ diagram, questions, selectedQuestionId, draft, result, onSelect, onClear }: {
  diagram: SchematicDiagram; questions: SocketQuestion[]; selectedQuestionId: string | null
  draft: Draft; result?: CircuitAttemptResult; onSelect: (id: string) => void; onClear: () => void
}) {
  const viewport = useSvgViewport()
  const questionMap = Object.fromEntries(questions.map((question) => [question.question_id, question]))
  return <div className="diagram-stage">
    <div className="diagram-toolbar" aria-label="회로도 보기 도구">
      <button type="button" onClick={() => viewport.zoomBy(0.15)} aria-label="확대">＋</button>
      <button type="button" onClick={() => viewport.zoomBy(-0.15)} aria-label="축소">－</button>
      <button type="button" onClick={viewport.fit}>화면 맞춤</button>
      <button type="button" onClick={viewport.reset}>100%</button>
      <span>{Math.round(viewport.zoom * 100)}%</span>
      <span>✋ 드래그 이동</span>
    </div>
    <svg
      className="circuit-svg" role="img" aria-label="시퀀스 회로도"
      viewBox={`${diagram.view_box.x} ${diagram.view_box.y} ${diagram.view_box.width} ${diagram.view_box.height}`}
      onPointerDown={viewport.pointerDown} onPointerMove={viewport.pointerMove} onPointerUp={viewport.pointerUp}
      onWheel={viewport.wheel} onClick={(event) => { if (event.target === event.currentTarget && !viewport.consumeDragClick()) onClear() }}
    >
      <g transform={`translate(${viewport.pan.x} ${viewport.pan.y}) scale(${viewport.zoom})`}>
        <g className="diagram-sections">{diagram.sections.map((section) => <g key={section.section_id}><rect x={section.bounds.x} y={section.bounds.y} width={section.bounds.width} height={section.bounds.height} /><text x={section.bounds.x + 18} y={section.bounds.y + 34}>{section.label}</text></g>)}</g>
        <g className="conductor-layer">{diagram.conductors.map((wire) => <g key={wire.conductor_id} className={`conductor ${wire.line_style}`}><polyline points={wire.points.map((p) => `${p.x},${p.y}`).join(' ')} />{wire.junctions.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="6" />)}</g>)}</g>
        <g className="symbol-layer">{diagram.elements.map((element) => {
          const selected = Boolean(element.interactive && element.question_id && element.question_id === selectedQuestionId)
          return <g key={element.element_id} data-element-id={element.element_id} className={`diagram-element${selected ? ' selected' : ''}`}>
            {selected && <rect className="selection-box" x={element.x - 12} y={element.y - 12} width={element.width + 24} height={element.height + 24} rx="10" />}
            <ElementShape element={element} />
            {element.element_type !== 'text' && element.element_type !== 'power_label' && element.label && <text className="element-label" x={element.x + element.width / 2} y={element.y - 10} textAnchor="middle">{element.label}</text>}
            {element.interactive && element.question_id && <rect className="element-hitbox" role="button" aria-label={`${element.label} ${element.circuit_ref_id} 선택`} tabIndex={0} x={element.x - 14} y={element.y - 14} width={element.width + 28} height={element.height + 28} onClick={(e) => { e.stopPropagation(); if (!viewport.consumeDragClick()) onSelect(element.question_id!) }} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(element.question_id!) } }} />}
            <AnswerMarkers element={element} question={element.question_id ? questionMap[element.question_id] : undefined} draft={draft} result={result} />
          </g>
        })}</g>
      </g>
    </svg>
  </div>
}
