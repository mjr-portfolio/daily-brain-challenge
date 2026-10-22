import { ApiError } from '@/api/client.ts'
import { adoptGuestStreak } from '@/api/auth.ts'
import { submitPuzzle } from '@/api/puzzles.ts'
import {
  clearGuestStreak,
  dropGuestCompletions,
  getGuestStreakRecord,
  listGuestCompletions,
  markDailyPlayedLocally,
  utcToday,
} from '@/utils/storage.ts'

export async function migrateGuestDataToAccount(): Promise<string[]> {
  const record = getGuestStreakRecord()
  try {
    await adoptGuestStreak(record.count, record.lastDate)
    clearGuestStreak()
  } catch {
    // Leave the browser streak in place so a later sign-in can try again.
  }

  const pending = listGuestCompletions()
  const failures: string[] = []

  const today = utcToday()
  for (const entry of pending) {
    if (entry.assignedDate === today) markDailyPlayedLocally(today)
    try {
      await submitPuzzle(entry.puzzleId, {
        answer: entry.answer,
        time_taken_seconds: entry.timeTakenSeconds,
      })
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) continue
      failures.push(entry.puzzleId)
    }
  }

  const failed = new Set(failures)
  dropGuestCompletions(pending.filter((entry) => !failed.has(entry.puzzleId)).map((entry) => entry.puzzleId))
  return failures
}
