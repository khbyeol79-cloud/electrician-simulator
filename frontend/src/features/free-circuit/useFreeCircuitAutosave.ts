import { useCallback, useEffect, useRef, useState } from 'react'
import { saveFreeCircuitWorkspace, type FreeCircuitWorkspace, type WiringConnection } from '../../api/client'

export type AutosaveStatus = 'idle' | 'pending' | 'saving' | 'saved' | 'error'

type EditableSnapshot = {
  workspace: FreeCircuitWorkspace
  connections: WiringConnection[]
  mode: 'graphic' | 'summary'
}

type SnapshotChange = {
  connections?: WiringConnection[]
  mode?: 'graphic' | 'summary'
}

const AUTOSAVE_DELAY_MS = 800

export function useFreeCircuitAutosave({
  workspace,
  connections,
  mode,
  onSaved,
  onError,
  delay = AUTOSAVE_DELAY_MS,
  saveWorkspace = saveFreeCircuitWorkspace,
}: {
  workspace?: FreeCircuitWorkspace
  connections: WiringConnection[]
  mode: 'graphic' | 'summary'
  onSaved: (workspace: FreeCircuitWorkspace) => void
  onError: (message: string) => void
  delay?: number
  saveWorkspace?: (workspace: FreeCircuitWorkspace) => Promise<FreeCircuitWorkspace>
}) {
  const [status, setStatus] = useState<AutosaveStatus>('idle')
  const workspaceRef = useRef(workspace)
  const connectionsRef = useRef(connections)
  const modeRef = useRef(mode)
  const activeWorkspaceIdRef = useRef(workspace?.workspace_id)
  const dirtyRevisionRef = useRef(0)
  const queuedRevisionRef = useRef(0)
  const failedRevisionRef = useRef<number | null>(null)
  const timerRef = useRef<number | undefined>(undefined)
  const saveTailRef = useRef<Promise<void>>(Promise.resolve())
  const mountedRef = useRef(true)

  useEffect(() => { workspaceRef.current = workspace }, [workspace])
  useEffect(() => { connectionsRef.current = connections }, [connections])
  useEffect(() => { modeRef.current = mode }, [mode])

  useEffect(() => {
    const nextId = workspace?.workspace_id
    if (activeWorkspaceIdRef.current === nextId) return
    if (timerRef.current !== undefined) window.clearTimeout(timerRef.current)
    timerRef.current = undefined
    activeWorkspaceIdRef.current = nextId
    dirtyRevisionRef.current = 0
    queuedRevisionRef.current = 0
    failedRevisionRef.current = null
    setStatus('idle')
  }, [workspace?.workspace_id])

  const snapshot = useCallback((): EditableSnapshot | undefined => {
    const currentWorkspace = workspaceRef.current
    if (!currentWorkspace) return undefined
    return {
      workspace: currentWorkspace,
      connections: connectionsRef.current,
      mode: modeRef.current,
    }
  }, [])

  const enqueue = useCallback((revision: number, value: EditableSnapshot) => {
    queuedRevisionRef.current = revision
    failedRevisionRef.current = null
    const workspaceId = value.workspace.workspace_id
    const task = saveTailRef.current.catch(() => undefined).then(async () => {
      if (activeWorkspaceIdRef.current !== workspaceId) return
      if (mountedRef.current) setStatus('saving')
      try {
        const saved = await saveWorkspace({
          ...value.workspace,
          connections: value.connections,
          editor: { ...value.workspace.editor, mode: value.mode },
        })
        if (activeWorkspaceIdRef.current !== workspaceId) return
        if (mountedRef.current) onSaved(saved)
        if (dirtyRevisionRef.current === revision) {
          failedRevisionRef.current = null
          if (mountedRef.current) setStatus('saved')
        }
      } catch (reason) {
        if (activeWorkspaceIdRef.current !== workspaceId) return
        failedRevisionRef.current = revision
        const message = reason instanceof Error ? reason.message : '자유회로를 자동 저장할 수 없습니다.'
        if (mountedRef.current && dirtyRevisionRef.current === revision) {
          setStatus('error')
          onError(message)
        }
        throw reason
      }
    })
    saveTailRef.current = task.catch(() => undefined)
    return task
  }, [onError, onSaved, saveWorkspace])

  const flushPending = useCallback(async () => {
    if (timerRef.current !== undefined) window.clearTimeout(timerRef.current)
    timerRef.current = undefined
    while (activeWorkspaceIdRef.current) {
      const revision = dirtyRevisionRef.current
      const retryFailed = failedRevisionRef.current === revision
      if (revision <= queuedRevisionRef.current && !retryFailed) {
        await saveTailRef.current
        if (dirtyRevisionRef.current <= queuedRevisionRef.current) return
        continue
      }
      const value = snapshot()
      if (!value) return
      await enqueue(revision, value)
      if (dirtyRevisionRef.current === revision) return
    }
  }, [enqueue, snapshot])

  const schedule = useCallback((change: SnapshotChange = {}) => {
    if (!workspaceRef.current) return
    if (change.connections) connectionsRef.current = change.connections
    if (change.mode) modeRef.current = change.mode
    dirtyRevisionRef.current += 1
    failedRevisionRef.current = null
    setStatus('pending')
    if (timerRef.current !== undefined) window.clearTimeout(timerRef.current)
    timerRef.current = window.setTimeout(() => { void flushPending().catch(() => undefined) }, delay)
  }, [delay, flushPending])

  const saveNow = useCallback(async () => {
    schedule()
    await flushPending()
  }, [flushPending, schedule])

  const discardPending = useCallback(() => {
    if (timerRef.current !== undefined) window.clearTimeout(timerRef.current)
    timerRef.current = undefined
    dirtyRevisionRef.current = queuedRevisionRef.current
    failedRevisionRef.current = null
    setStatus('idle')
  }, [])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      if (timerRef.current !== undefined) window.clearTimeout(timerRef.current)
      timerRef.current = undefined
      const revision = dirtyRevisionRef.current
      if (revision <= queuedRevisionRef.current || !workspaceRef.current) return
      const value = snapshot()
      if (value) void enqueue(revision, value).catch(() => undefined)
    }
  }, [enqueue, snapshot])

  return { status, schedule, saveNow, flushPending, discardPending }
}

export function isTextEditingTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
}
