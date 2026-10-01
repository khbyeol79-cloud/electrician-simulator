// Credentials live only in an HttpOnly cookie; these are non-secret UI state
// and a CSRF token, scoped to this loaded page (never persisted).
export type Account = { user_id: string; username: string; nickname: string }
export type AuthSession = { required: boolean; user: Account | null; csrf_token: string | null; registration_open: boolean; is_admin?: boolean }
let session: AuthSession | undefined
export function setAuthSession(value: AuthSession | undefined) { session = value }
export function currentAuthSession() { return session }
export function authHeaders(): Record<string, string> {
  if (!session?.required) return {}
  return {
    'X-Requested-With': 'ElectricianSimulator',
    ...(session.csrf_token ? { 'X-CSRF-Token': session.csrf_token } : {}),
    ...(session.user ? { 'X-Session-User': session.user.user_id } : {}),
  }
}
export function activeAccountId() { return session?.user?.user_id }
// No study answers persist on the browser disk in classroom account mode.
const transientDrafts = new Map<string, string>()
export function studyDraftStorage() {
  return session?.required ? {
    getItem: (key: string) => transientDrafts.get(key) ?? null,
    setItem: (key: string, value: string) => { transientDrafts.set(key, value) },
    removeItem: (key: string) => { transientDrafts.delete(key) },
  } : window.localStorage
}
export function clearAccountDrafts() { transientDrafts.clear() }
