import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client.ts'
import { adoptGuestStreak } from '@/api/auth.ts'
import { submitPuzzle } from '@/api/puzzles.ts'
import { migrateGuestDataToAccount } from '@/services/migration.ts'
import {
  bumpStreakIfDaily,
  listGuestCompletions,
  recordGuestCompletion,
  utcToday,
  visibleGuestStreak,
} from '@/utils/storage.ts'

vi.mock('@/api/auth.ts', () => ({
  adoptGuestStreak: vi.fn(),
}))

vi.mock('@/api/puzzles.ts', () => ({
  submitPuzzle: vi.fn(),
}))

function yesterday(): string {
  const [year, month, day] = utcToday().split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  date.setUTCDate(date.getUTCDate() - 1)
  return date.toISOString().slice(0, 10)
}

describe('guest streak', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('keeps the streak when today is answered incorrectly', () => {
    localStorage.setItem('guest_streak', '4')
    localStorage.setItem('guest_streak_date', yesterday())
    recordGuestCompletion({
      puzzleId: 'daily-1',
      assignedDate: utcToday(),
      timeTakenSeconds: 40,
      answer: 1,
      isCorrect: false,
    })

    expect(bumpStreakIfDaily('daily-1', utcToday())).toBe(5)
    expect(visibleGuestStreak()).toBe(5)
    expect(bumpStreakIfDaily('daily-1', utcToday())).toBe(5)
  })
})

describe('guest migration', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(adoptGuestStreak).mockResolvedValue({
      email: 'player@example.com',
      streak: 1,
      total_score: 0,
    })
  })

  it('keeps a completion when saving it to the account fails', async () => {
    recordGuestCompletion({
      puzzleId: 'daily-1',
      assignedDate: utcToday(),
      timeTakenSeconds: 20,
      answer: 'trace',
      isCorrect: true,
    })
    vi.mocked(submitPuzzle).mockRejectedValue(new ApiError(502, 'unavailable'))

    const failures = await migrateGuestDataToAccount()

    expect(failures).toEqual(['daily-1'])
    expect(listGuestCompletions().map((entry) => entry.puzzleId)).toEqual(['daily-1'])
  })
})
