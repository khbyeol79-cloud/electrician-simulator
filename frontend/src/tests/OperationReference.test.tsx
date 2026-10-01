import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LayoutActivity, OperationReference } from '../features/operation/components/OperationReference'
import { layoutDevices } from '../features/operation/layoutDevices'
import { contactTargets } from '../features/circuit/analysisAnnotations'
import type { OperationSessionState } from '../api/client'
import { installApiMock } from './mockApi'

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })
const id = 'qnet_electrician_practical_001'
const state = { controls: { PB1: { active: true }, SS: { active: false } }, indicators: { YL: 'off', RL: 'on', GL: 'error' }, audible_outputs: { BZ: 'on' }, motors: { M1: 'forward' } } as unknown as OperationSessionState

describe('operation layout reference', () => {
  it('covers 18 lower symbol rows and only unique verified page-5 device positions', () => {
    for (let n=1; n<=18; n++) {
      const problemId = `qnet_electrician_practical_${String(n).padStart(3,'0')}`
      const bodies = contactTargets(problemId).filter(x=>x.kind==='body')
      expect(bodies).toHaveLength(11)
      expect(new Set(bodies.map(x=>x.id)).size).toBe(11)
      const devices = layoutDevices(problemId)
      expect(devices).toHaveLength(7)
      expect(new Set(devices.map(x=>x.id)).size).toBe(7)
      expect(devices.every(x=>x.x>0 && x.x<992 && x.y>0 && x.y<1402)).toBe(true)
    }
    expect(layoutDevices('unknown')).toEqual([])
    expect(layoutDevices('qnet_electrician_practical_002').find(x=>x.id==='GL')?.y).toBe(677)
    expect(layoutDevices('qnet_electrician_practical_006').find(x=>x.id==='GL')?.y).toBe(704)
  })
  it('uses actual output states, not button activity, and updates on stop/reset', () => {
    const { container, rerender } = render(<svg><LayoutActivity problemId={id} session={state} /></svg>)
    expect(screen.getByRole('img',{name:'PB1 누름'})).toBeInTheDocument()
    expect(screen.getByRole('img',{name:'YL 꺼짐'})).toHaveAttribute('data-state','off')
    expect(screen.getByRole('img',{name:'RL 점등'})).toHaveAttribute('data-state','on')
    expect(screen.getByRole('img',{name:'GL 오류'})).toHaveAttribute('data-state','error')
    expect(container.querySelector('.buzzer-wave')).toBeInTheDocument()
    rerender(<svg><LayoutActivity problemId={id} session={{...state, indicators:{RL:'off'},audible_outputs:{BZ:'off'}}} /></svg>)
    expect(screen.getByRole('img',{name:'RL 꺼짐'})).toHaveAttribute('data-state','off')
    expect(container.querySelector('.buzzer-wave')).not.toBeInTheDocument()
  })
  it('does not invent active or off states when a session/device state is missing', () => {
    const {container} = render(<svg><LayoutActivity problemId={id} /></svg>)
    expect(container.querySelectorAll('[data-state="unknown"]')).toHaveLength(7)
    expect(container.querySelector('.active')).not.toBeInTheDocument()
  })
  it('shows live overlays only in the layout view and keeps schematics static', async () => {
    installApiMock()
    const {container,rerender} = render(<OperationReference problemId={id} view="layout" session={state} />)
    expect(screen.getByRole('img',{name:'동작시험 배관배치도'}).querySelector('image')).toHaveAttribute('href',`/api/problems/${id}/layout-reference`)
    expect(container.querySelector('.motor-rotor.forward')).toBeInTheDocument()
    rerender(<OperationReference problemId={id} view="schematic" session={state} />)
    await screen.findByRole('img',{name:'동작시험 시퀀스 회로도'})
    expect(container.querySelector('.layout-activity')).not.toBeInTheDocument()
  })
})
