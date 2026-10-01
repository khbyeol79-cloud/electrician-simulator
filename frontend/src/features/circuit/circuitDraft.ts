import { activeUserStorageSuffix } from '../user/userProfile'
import { studyDraftStorage } from '../user/authSession'

export type CircuitDraft = Record<string, Record<string, number>>

export function circuitDraftKey(problemId: string, version: number) {
  const legacyKey = `electrician.circuitDraft.${problemId}.v${version}`
  const userId = activeUserStorageSuffix()
  return userId === 'default' ? legacyKey : `${legacyKey}.${userId}`
}

export function restoreCircuitDraft(problemId: string, version: number): CircuitDraft {
  const key = circuitDraftKey(problemId, version)
  try {
    const raw = studyDraftStorage().getItem(key)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    return parsed && typeof parsed === 'object' ? parsed as CircuitDraft : {}
  } catch {
    studyDraftStorage().removeItem(key)
    return {}
  }
}
