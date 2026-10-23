import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AccountStatsModal } from '@/components/AccountStatsModal.tsx'
import type { CategoryStats, StatsSlice, UserStats } from '@/types/stats.ts'

const { stats } = vi.hoisted(() => {
  function category(overrides: Partial<CategoryStats> = {}): CategoryStats {
    return {
      solved: 0,
      played: 0,
      available: 0,
      win_rate: null,
      average_completion_time_seconds: null,
      ...overrides,
    }
  }

  function slice(overrides: Partial<StatsSlice> = {}): StatsSlice {
    return {
      puzzles_solved: 0,
      puzzles_played: 0,
      puzzles_available: 0,
      completion_percent: null,
      left_to_play: 0,
      win_rate: null,
      average_completion_time_seconds: null,
      categories: {
        pattern: category(),
        anagram: category(),
        news_quiz: category(),
      },
      ...overrides,
    }
  }

  const stats: UserStats = {
    current_streak: 4,
    best_streak: 9,
    daily: slice({
      puzzles_solved: 1,
      puzzles_played: 1,
      win_rate: 100,
      categories: {
        pattern: category(),
        anagram: category({ solved: 1, played: 1, win_rate: 100 }),
        news_quiz: category(),
      },
    }),
    overall: slice({
      puzzles_solved: 5,
      puzzles_played: 7,
      puzzles_available: 20,
      completion_percent: 25,
      left_to_play: 13,
      win_rate: 71.4,
      categories: {
        pattern: category({ solved: 2, played: 2, available: 10, win_rate: 100 }),
        anagram: category({ solved: 2, played: 4, available: 5, win_rate: 50 }),
        news_quiz: category({ solved: 1, played: 1, available: 5, win_rate: 100 }),
      },
    }),
  }

  return { stats }
})

vi.mock('@/hooks/useUserStats.ts', () => ({
  useUserStats: () => ({
    data: stats,
    isLoading: false,
    isError: false,
  }),
}))

describe('account stats modal', () => {
  it('keeps streaks on Daily and catalog progress on Overall', async () => {
    const user = userEvent.setup()
    render(<AccountStatsModal open email="ada@example.com" onClose={() => {}} />)

    expect(screen.getByText('Active Streak 🔥')).toBeVisible()
    expect(screen.getByText('4')).toBeVisible()
    expect(screen.getByText('Best Streak ⚡')).toBeVisible()
    expect(screen.getByText('9')).toBeVisible()
    expect(screen.getByText('1/1 solved')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Correct daily puzzles of each type' })).toBeVisible()
    expect(screen.queryByText('Completion')).not.toBeInTheDocument()
    expect(screen.queryByText('Left to play')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Overall' }))

    expect(screen.getByText('Completion')).toBeVisible()
    expect(screen.getByText('25%')).toBeVisible()
    expect(screen.getByText('Left to play')).toBeVisible()
    expect(screen.getByText('13')).toBeVisible()
    expect(screen.getByText('2/10 played')).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Attempted, out of every puzzle of each type' })).toBeVisible()
    expect(screen.queryByText('Active Streak 🔥')).not.toBeInTheDocument()
    expect(screen.queryByText('Best Streak ⚡')).not.toBeInTheDocument()
    expect(screen.queryByText('1/1 solved')).not.toBeInTheDocument()
  })
})
