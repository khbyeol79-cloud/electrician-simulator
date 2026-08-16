export type CircuitDraft = Record<string, Record<string, number>>

export function circuitDraftKey(problemId: string, version: number) {
  return `electrician.circuitDraft.${problemId}.v${version}`
}

export function restoreCircuitDraft(problemId: string, version: number): CircuitDraft {
  const key = circuitDraftKey(problemId, version)
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    return parsed && typeof parsed === 'object' ? parsed as CircuitDraft : {}
  } catch {
    window.localStorage.removeItem(key)
    return {}
  }
}
