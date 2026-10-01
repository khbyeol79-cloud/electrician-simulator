export function SlotNumberExample() {
  return <section className="slot-number-example"><strong>슬롯번호 입력 예시</strong>
    <svg viewBox="0 0 280 230" role="img" aria-label="가로 접점은 좌우에 10과 4, 세로 접점은 위아래에 4와 10을 입력하는 예시">
      <rect width="280" height="230" rx="8" fill="#f5f8fc" />
      <g fill="#24364e" fontSize="13" textAnchor="middle"><text x="140" y="24">가로 접점 · 좌우 입력</text><text x="140" y="145">세로 접점 · 위아래 입력</text><text x="140" y="51">EOCR</text><text x="178" y="190">MC1</text></g>
      <g fill="white" stroke="#334155" strokeWidth="2"><path d="M45 76H111 M169 76H235 M118 76L160 68 M158 64V85 M130 158V171 M130 204V220 M130 179L138 198" fill="none"/><circle cx="116" cy="76" r="4"/><circle cx="164" cy="76" r="4"/><circle cx="130" cy="175" r="4"/><circle cx="130" cy="200" r="4"/></g>
      <g fill="#087a4a" fontWeight="bold" fontSize="17" textAnchor="middle"><text x="95" y="65">10</text><text x="185" y="65">4</text><text x="109" y="172">4</text><text x="107" y="218">10</text></g>
      <text x="140" y="109" textAnchor="middle" fill="#64748b" fontSize="11">접점 클릭 → 양쪽 단자에 각각 입력</text>
    </svg><small>입력 위치 안내용 예시입니다. 실제 단자번호는 사용 기구에 맞춰 입력하세요.</small>
  </section>
}
