import { activeAccountId } from './authSession'
export const USER_ID_STORAGE_KEY = 'electrician.webUserId'
const NICKNAME_STORAGE_KEY = 'electrician.userNickname'
const ACCESS_SEEN_STORAGE_KEY = 'electrician.userAccessSeen'

export type UserProfile = { userId: string; nickname: string; isLegacy: boolean }

function stableNicknameId(nickname: string) {
  const normalized = nickname.normalize('NFKC').trim().toLocaleLowerCase('ko-KR')
  let first = 0x811c9dc5
  let second = 0x9e3779b9
  for (let index = 0; index < normalized.length; index += 1) {
    const code = normalized.charCodeAt(index)
    first = Math.imul(first ^ code, 0x01000193) >>> 0
    second = Math.imul(second ^ (code + index), 0x85ebca6b) >>> 0
  }
  return `user_${first.toString(36)}${second.toString(36)}`
}

export function loadUserProfile(): UserProfile {
  const userId = window.localStorage.getItem(USER_ID_STORAGE_KEY)
  const nickname = window.localStorage.getItem(NICKNAME_STORAGE_KEY)
  if (userId && nickname) return { userId, nickname, isLegacy: false }
  return { userId: 'default', nickname: '기존 로컬 사용자', isLegacy: true }
}

export function saveNicknameProfile(nickname: string): UserProfile {
  const trimmed = nickname.normalize('NFKC').trim().replace(/\s+/g, ' ')
  if (trimmed.length < 2 || trimmed.length > 20) throw new Error('닉네임은 2~20자로 입력해 주세요.')
  const profile = { userId: stableNicknameId(trimmed), nickname: trimmed, isLegacy: false }
  window.localStorage.setItem(USER_ID_STORAGE_KEY, profile.userId)
  window.localStorage.setItem(NICKNAME_STORAGE_KEY, profile.nickname)
  window.localStorage.setItem(ACCESS_SEEN_STORAGE_KEY, '1')
  return profile
}

export function useLegacyProfile(): UserProfile {
  window.localStorage.removeItem(USER_ID_STORAGE_KEY)
  window.localStorage.removeItem(NICKNAME_STORAGE_KEY)
  window.localStorage.setItem(ACCESS_SEEN_STORAGE_KEY, '1')
  return loadUserProfile()
}

export function shouldIntroduceUserAccess() {
  return window.localStorage.getItem(ACCESS_SEEN_STORAGE_KEY) !== '1'
}

export function activeUserStorageSuffix() {
  return activeAccountId() ?? window.localStorage.getItem(USER_ID_STORAGE_KEY) ?? 'default'
}
