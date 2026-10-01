import { useEffect, useId, useRef, type ReactNode } from 'react'

export function WorkspaceDialog({ onClose, children, title = '작업공간' }: { onClose: () => void; children: ReactNode; title?: string }) {
  const panel = useRef<HTMLElement>(null)
  const titleId = useId()
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    panel.current?.focus()
    return () => previous?.focus()
  }, [])
  return <div className="problem-dialog-backdrop workspace-dialog-backdrop" onMouseDown={event => {
    if (event.target === event.currentTarget) onClose()
  }}>
    <section ref={panel} tabIndex={-1} className="workspace-dialog" role="dialog" aria-modal="true" aria-labelledby={titleId} onKeyDown={event => {
      event.stopPropagation()
      if (event.key === 'Escape') { event.preventDefault(); onClose() }
      if (event.key === 'Tab') {
        const items = Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), select:not(:disabled), input:not([hidden]):not(:disabled)') ?? [])
        const first = items[0], last = items.at(-1)
        if (event.shiftKey && (document.activeElement === first || document.activeElement === panel.current)) { event.preventDefault(); last?.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
      }
    }}>
      <header><h2 id={titleId}>{title}</h2><button type="button" aria-label={`${title} 닫기`} onClick={onClose}>닫기</button></header>
      {children}
    </section>
  </div>
}
