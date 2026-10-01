import { expect, it } from 'vitest'
import { isProtectiveEarth, workspaceTime } from '../features/wiring/engine/workspaceDisplay'

it('recognizes PE terminals but not ordinary terminal or device names', () => {
  for (const id of ['PE', 'PWR-PE', 'M1-PE', 'M2-PE', 'FLS-PE']) expect(isProtectiveEarth(id)).toBe(true)
  for (const id of ['PWR-L1', 'FLS-E1', 'PE-1', 'SCOPE']) expect(isProtectiveEarth(id)).toBe(false)
})

it('formats UTC database timestamps consistently with explicit UTC values', () => {
  expect(workspaceTime('2026-09-18T01:02:03')).toBe(workspaceTime('2026-09-18T01:02:03Z'))
  expect(workspaceTime('2026-09-18T01:02:03Z')).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/)
  expect(workspaceTime(null)).toBe('기록 없음')
  expect(workspaceTime('invalid')).toBe('기록 없음')
})
