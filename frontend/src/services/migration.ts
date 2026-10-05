import { ApiError } from '@/api/client.ts'
import { submitPuzzle } from '@/api/puzzles.ts'
import {
  clearGuestCompletions,
  listGuestCompletions,
  saveGuestCompletions,
  utcToday,
} from '@/utils/storage.ts'

export async function migrateGuestDataToAccount(): Promise<string[]> {
  const pending = listGuestCompletions()
  const failures: string[] = []

  for (const entry of pending) {
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

  const todayEntries = pending.filter((entry) => entry.assignedDate === utcToday())
  clearGuestCompletions()
  if (todayEntries.length > 0) saveGuestCompletions(todayEntries)
  return failures
}
