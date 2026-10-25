import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getAccount } from '@/api/auth.ts'
import { getDaily, getPuzzleArchive, startDaily } from '@/api/puzzles.ts'
import App from '@/App.tsx'
import { Navbar } from '@/components/Navbar.tsx'
import { AuthProvider } from '@/context/AuthContext.tsx'
import { utcToday } from '@/utils/storage.ts'

vi.mock('@/api/auth.ts', () => ({
  getAccount: vi.fn().mockRejectedValue(new Error('Not authenticated')),
  adoptGuestStreak: vi.fn().mockResolvedValue({
    email: 'player@example.com',
    display_name: null,
    preferences: { theme: 'dark' },
    streak: 2,
    total_score: 180,
    applied: true,
  }),
  loginAccount: vi.fn(),
  registerAccount: vi.fn(),
  logoutAccount: vi.fn(),
}))

vi.mock('@/api/puzzles.ts', () => ({
  getDaily: vi.fn(),
  startDaily: vi.fn(),
  getPuzzleArchive: vi.fn(),
  submitPuzzle: vi.fn(),
  getDailyLeaderboard: vi.fn().mockResolvedValue({
    puzzle_id: '11111111-1111-1111-1111-111111111111',
    assigned_date: '2026-10-22',
    limit: 25,
    entries: [],
    viewer: null,
  }),
  getArchiveBenchmark: vi.fn(),
}))

const puzzleId = '11111111-1111-1111-1111-111111111111'

function preview() {
  return {
    id: puzzleId,
    puzzle_type: 'pattern' as const,
    assigned_date: utcToday(),
    is_completed: false,
    started_at: null,
  }
}

function renderWithProviders(ui: ReactNode, path = '/') {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  )
}

describe('daily clock', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(getAccount).mockRejectedValue(new Error('Not authenticated'))
    vi.mocked(getDaily).mockResolvedValue(preview())
    vi.mocked(startDaily).mockResolvedValue({
      puzzle: {
        id: puzzleId,
        puzzle_type: 'pattern',
        assigned_date: utcToday(),
        created_at: '2026-10-22T00:00:00Z',
        content: {
          grid: [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, null],
          ],
          prompt: 'Which number completes the sequence?',
          choices: [9, 10, 12],
        },
      },
      started_at: null,
      server_now: '2026-10-22T12:00:00Z',
    })
  })

  it('starts the clock only after Start is pressed', async () => {
    const user = userEvent.setup()
    renderWithProviders(<App />)

    expect(await screen.findByRole('button', { name: /start today's puzzle/i })).toBeVisible()
    expect(screen.queryByRole('button', { name: /leaderboard/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/leaderboard coming soon/i)).not.toBeInTheDocument()
    expect(startDaily).not.toHaveBeenCalled()
    expect(localStorage.getItem('daily_started_at')).toBeNull()
    expect(screen.queryByText(/^\d{2}:\d{2}$/)).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /start today's puzzle/i }))

    expect(startDaily).toHaveBeenCalledOnce()
    expect(localStorage.getItem('daily_started_at')).toContain(puzzleId)
    expect(await screen.findByText(/^\d{2}:\d{2}$/)).toBeVisible()
  })
})

describe('archive route', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(getAccount).mockResolvedValue({
      email: 'player@example.com',
      display_name: null,
      preferences: { theme: 'dark' },
      streak: 2,
      total_score: 180,
    })
    vi.mocked(getDaily).mockResolvedValue(preview())
    vi.mocked(getPuzzleArchive).mockResolvedValue({
      page: 1,
      limit: 12,
      total: 1,
      items: [
        {
          id: 'archive-1',
          puzzle_type: 'pattern',
          assigned_date: '2026-10-01',
          created_at: '2026-10-01T00:00:00Z',
          is_completed: false,
          is_correct: null,
          score: null,
          content: {
            grid: [
              [1, 2, 3],
              [4, 5, 6],
              [7, 8, null],
            ],
            prompt: 'Past pattern',
            choices: [9, 10, 12],
          },
        },
      ],
    })
  })

  it('opens the grid for a signed-in visit without starting a puzzle', async () => {
    renderWithProviders(<App />, '/archive')

    expect(await screen.findByRole('heading', { name: 'Archive' })).toBeVisible()
    expect(screen.getByText('Play a past puzzle.')).toBeVisible()
    expect(await screen.findByText('Unplayed')).toBeVisible()
    expect(localStorage.getItem('archive_started_at')).toBeNull()
    expect(screen.getByRole('button', { name: /start today's puzzle/i })).toBeVisible()
  })
})

describe('completed daily card', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(getAccount).mockResolvedValue({
      email: 'player@example.com',
      display_name: null,
      preferences: { theme: 'dark' },
      streak: 2,
      total_score: 180,
    })
    vi.mocked(getDaily).mockResolvedValue({ ...preview(), is_completed: true })
  })

  it('offers today\'s leaderboard after the daily is finished', async () => {
    renderWithProviders(<App />)

    expect(await screen.findByRole('button', { name: /view today's leaderboard/i })).toBeVisible()
    expect(screen.queryByRole('button', { name: /start today's puzzle/i })).not.toBeInTheDocument()
  })
})

describe('total score', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(getAccount).mockRejectedValue(new Error('Not authenticated'))
  })

  it('shows the total for a signed-in player and hides it from a guest', async () => {
    const { unmount } = renderWithProviders(<Navbar onOpenArchive={() => undefined} />)
    expect(screen.queryByTitle('Total score')).not.toBeInTheDocument()
    unmount()

    vi.mocked(getAccount).mockResolvedValue({
      email: 'player@example.com',
      display_name: null,
      preferences: { theme: 'dark' },
      streak: 2,
      total_score: 180,
    })
    renderWithProviders(<Navbar onOpenArchive={() => undefined} />)

    expect(await screen.findByText('180 pts')).toBeVisible()
    expect(screen.getByTitle('Daily streak')).toHaveTextContent('2')
  })
})
