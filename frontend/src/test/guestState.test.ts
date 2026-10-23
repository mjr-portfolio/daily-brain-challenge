import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/api/client.ts'
import { adoptGuestStreak } from '@/api/auth.ts'
import { submitPuzzle } from '@/api/puzzles.ts'
import { migrateGuestDataToAccount } from '@/services/migration.ts'
import {
  bumpStreakIfDaily,
  ensureArchiveStarted,
  getDailyStartedAt,
  listGuestCompletions,
  markDailyStarted,
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

describe('start clocks', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('keeps an archive start on one account and starts fresh on another', () => {
    const started = ensureArchiveStarted('puzzle-1', 'ada@example.com')
    const book = JSON.parse(localStorage.getItem('archive_started_at') ?? '{}') as {
      [scope: string]: { [puzzleId: string]: number }
    }
    book['ada@example.com']['puzzle-1'] = started - 30 * 60 * 1000
    localStorage.setItem('archive_started_at', JSON.stringify(book))

    expect(ensureArchiveStarted('puzzle-1', 'ada@example.com')).toBe(started - 30 * 60 * 1000)
    const other = ensureArchiveStarted('puzzle-1', 'bea@example.com')
    expect(other).toBeGreaterThan(started - 5 * 1000)
  })

  it('resets an archive start that is older than an hour', () => {
    ensureArchiveStarted('puzzle-1', 'ada@example.com')
    const book = JSON.parse(localStorage.getItem('archive_started_at') ?? '{}') as {
      [scope: string]: { [puzzleId: string]: number }
    }
    book['ada@example.com']['puzzle-1'] = Date.now() - 2 * 60 * 60 * 1000
    localStorage.setItem('archive_started_at', JSON.stringify(book))

    const reset = ensureArchiveStarted('puzzle-1', 'ada@example.com')
    expect(reset).toBeGreaterThan(Date.now() - 5 * 1000)
  })

  it('ignores a start saved before accounts were separated', () => {
    localStorage.setItem(
      'archive_started_at',
      JSON.stringify({ 'puzzle-1': Date.now() - 60 * 1000 }),
    )
    const started = ensureArchiveStarted('puzzle-1', 'ada@example.com')
    expect(started).toBeGreaterThan(Date.now() - 5 * 1000)
  })

  it('drops a guest daily start after an hour away', () => {
    markDailyStarted('puzzle-1')
    const book = JSON.parse(localStorage.getItem('daily_started_at') ?? '{}') as {
      guest: { [puzzleId: string]: number }
    }
    book.guest['puzzle-1'] = Date.now() - 2 * 60 * 60 * 1000
    localStorage.setItem('daily_started_at', JSON.stringify(book))

    expect(getDailyStartedAt('puzzle-1')).toBeNull()
  })
})
