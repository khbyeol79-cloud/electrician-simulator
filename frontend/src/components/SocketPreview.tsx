import type { SocketType } from '../api/client'

export function SocketPreview({ socket }: { socket: SocketType }) {
  const rows = Object.fromEntries(socket.rows.map((row) => [row.row_id, row.pins]))
  return (
    <section className={`socket-preview socket-${socket.pin_count}p`} aria-label={`${socket.name} 핀 배열`}>
      <header>
        <div>
          <span>{socket.pin_count}P 규격</span>
          <h4>{socket.name}</h4>
        </div>
        <small>배선용 베이스 정면</small>
      </header>
      <div className="socket-body" data-testid={`socket-${socket.pin_count}p-body`}>
        <div className="socket-row top" aria-label={`상단 ${rows.top.join(' ')}`}>
          {rows.top.map((pin) => <span className="socket-slot" key={pin}>{pin}</span>)}
        </div>
        <div className={`socket-center ${socket.center.shape}`}>
          <strong>{socket.pin_count}P</strong>
          <span>장치 명칭 영역</span>
        </div>
        <div className="socket-row bottom" aria-label={`하단 ${rows.bottom.join(' ')}`}>
          {rows.bottom.map((pin) => <span className="socket-slot" key={pin}>{pin}</span>)}
        </div>
      </div>
      <dl className="socket-array-text">
        <div><dt>상단</dt><dd>{rows.top.join(',')}</dd></div>
        <div><dt>하단</dt><dd>{rows.bottom.join(',')}</dd></div>
      </dl>
    </section>
  )
}
