export function isProtectiveEarth(terminal: string) {
  return /(^|[-_:])PE$/i.test(terminal)
}

export function workspaceTime(value?: string | null) {
  if (!value) return '기록 없음'
  const date = new Date(/(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value.replace(' ', 'T')}Z`)
  if (Number.isNaN(date.getTime())) return '기록 없음'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}
