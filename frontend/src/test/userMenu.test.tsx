import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getAccount, logoutAccount, registerAccount } from '@/api/auth.ts'
import { updateMe } from '@/api/users.ts'
import { AuthModal } from '@/components/AuthModal.tsx'
import { Navbar } from '@/components/Navbar.tsx'
import { AuthProvider } from '@/context/AuthContext.tsx'
import { useAuth } from '@/hooks/useAuth.ts'

vi.mock('@/api/auth.ts', () => ({
  getAccount: vi.fn().mockRejectedValue(new Error('Not authenticated')),
  adoptGuestStreak: vi.fn().mockResolvedValue({
    email: 'ada@example.com',
    display_name: 'Ada',
    preferences: { theme: 'dark' },
    streak: 4,
    total_score: 20,
    applied: true,
  }),
  loginAccount: vi.fn(),
  registerAccount: vi.fn(),
  logoutAccount: vi.fn(),
}))

vi.mock('@/api/users.ts', () => ({
  getMyStats: vi.fn(() => new Promise(() => undefined)),
  updateMe: vi.fn(),
  deleteMyAccount: vi.fn(),
}))

function renderInAuth(node: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={client}>
        <AuthProvider>
          <MemoryRouter>{children}</MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    )
  }
  return render(node, { wrapper: Wrapper })
}

function renderNavbar() {
  return renderInAuth(<Navbar onOpenArchive={() => undefined} />)
}

function OpenAuth() {
  const { openAuthModal } = useAuth()
  return (
    <>
      <button type="button" onClick={openAuthModal}>
        Open auth
      </button>
      <AuthModal />
    </>
  )
}

describe('profile menu', () => {
  beforeEach(() => {
    vi.mocked(getAccount).mockResolvedValue({
      email: 'ada@example.com',
      display_name: 'Ada',
      preferences: { theme: 'dark' },
      streak: 4,
      total_score: 20,
    })
  })

  it('opens stats and settings from the profile button', async () => {
    const user = userEvent.setup()
    renderNavbar()

    await user.click(await screen.findByRole('button', { name: 'Account, Ada' }))
    expect(screen.getByRole('menu', { name: 'Account' })).toBeVisible()
    expect(screen.getByText('Streak 4')).toBeVisible()

    await user.click(screen.getByRole('menuitem', { name: 'Stats Dashboard' }))
    expect(await screen.findByRole('dialog', { name: 'Account' })).toBeVisible()
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Close' }))
    await user.click(screen.getByRole('button', { name: 'Account, Ada' }))
    await user.click(screen.getByRole('menuitem', { name: 'Settings & Preferences' }))

    expect(await screen.findByRole('dialog', { name: 'Settings' })).toBeVisible()
    expect(screen.queryByRole('dialog', { name: 'Account' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Dark' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('closes the menu and spins the account button until logout finishes', async () => {
    let finish: () => void = () => undefined
    vi.mocked(logoutAccount).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = () => {
            resolve(undefined)
          }
        }),
    )
    const user = userEvent.setup()
    renderNavbar()

    await user.click(await screen.findByRole('button', { name: 'Account, Ada' }))
    await user.click(screen.getByRole('menuitem', { name: 'Log out' }))

    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Logging out' })).toBeDisabled()

    finish()
    expect(await screen.findByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  it('does not save a blank display name', async () => {
    const user = userEvent.setup()
    renderNavbar()

    await user.click(await screen.findByRole('button', { name: 'Account, Ada' }))
    await user.click(screen.getByRole('menuitem', { name: 'Settings & Preferences' }))
    const name = await screen.findByLabelText('Display name')
    expect(name).toBeRequired()
    await user.clear(name)
    await user.click(screen.getByRole('button', { name: 'Save details' }))

    expect(updateMe).not.toHaveBeenCalled()
    expect(name).toBeInvalid()
  })
})

describe('create account', () => {
  it('requires a display name', async () => {
    const user = userEvent.setup()
    renderInAuth(<OpenAuth />)

    await user.click(screen.getByRole('button', { name: 'Open auth' }))
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    const name = screen.getByLabelText('Display name')
    expect(name).toBeRequired()
    expect(screen.getByText(/letters, numbers, and underscores/i)).toBeVisible()
    expect(screen.queryByText(/optional/i)).not.toBeInTheDocument()
    const submit = screen.getAllByRole('button', { name: 'Create account' }).at(-1)
    if (!submit) throw new Error('missing submit')
    await user.click(submit)
    expect(registerAccount).not.toHaveBeenCalled()
  })
})
