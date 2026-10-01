import { afterEach, describe, expect, it } from 'vitest'
import { circuitDraftKey } from '../features/circuit/circuitDraft'
import { loadUserProfile, saveNicknameProfile, useLegacyProfile } from '../features/user/userProfile'

afterEach(() => window.localStorage.clear())

describe('사용자별 학습 공간', () => {
  it('maps the same normalized nickname to the same safe database id', () => {
    const first = saveNicknameProfile(' 학생 01 ')
    const second = saveNicknameProfile('학생 01')
    expect(first.userId).toBe(second.userId)
    expect(first.userId).toMatch(/^user_[a-z0-9]+$/)
    expect(loadUserProfile().nickname).toBe('학생 01')
  })

  it('namespaces browser drafts while preserving the legacy key', () => {
    expect(circuitDraftKey('practice_001', 1)).toBe('electrician.circuitDraft.practice_001.v1')
    const profile = saveNicknameProfile('학습자A')
    expect(circuitDraftKey('practice_001', 1)).toBe(`electrician.circuitDraft.practice_001.v1.${profile.userId}`)
    useLegacyProfile()
    expect(circuitDraftKey('practice_001', 1)).toBe('electrician.circuitDraft.practice_001.v1')
  })
})
