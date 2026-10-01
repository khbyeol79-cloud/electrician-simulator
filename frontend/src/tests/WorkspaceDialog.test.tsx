import { useState } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it } from 'vitest'
import { WorkspaceDialog } from '../components/WorkspaceDialog'

afterEach(cleanup)

it('keeps keyboard focus inside the popup and returns it to the menu on Escape', async () => {
  function Harness() {
    const [open, setOpen] = useState(false)
    return <><button onClick={() => setOpen(true)}>작업공간 열기</button>{open && <WorkspaceDialog onClose={() => setOpen(false)}><button>JSON 내보내기</button></WorkspaceDialog>}</>
  }
  const user = userEvent.setup()
  render(<Harness />)
  const menu = screen.getByRole('button', { name: '작업공간 열기' })
  await user.click(menu)
  expect(screen.getByRole('dialog', { name: '작업공간' })).toHaveFocus()
  await user.tab({ shift: true })
  expect(screen.getByRole('button', { name: 'JSON 내보내기' })).toHaveFocus()
  await user.tab()
  expect(screen.getByRole('button', { name: '작업공간 닫기' })).toHaveFocus()
  await user.keyboard('{Escape}')
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  expect(menu).toHaveFocus()
})
