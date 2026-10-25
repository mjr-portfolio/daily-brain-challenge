import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getAccount, logoutAccount } from '@/api/auth.ts'
import { Navbar } from '@/components/Navbar.tsx'
import { AuthProvider } from '@/context/AuthContext.tsx'

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

function renderNavbar() {
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
  return render(<Navbar onOpenArchive={() => undefined} />, { wrapper: Wrapper })
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
    let finish = () => undefined
    vi.mocked(logoutAccount).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = () => resolve(undefined)
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
})
