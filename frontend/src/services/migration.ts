import { ApiError } from '@/api/client.ts'
import { submitPuzzle } from '@/api/puzzles.ts'
import { clearGuestCompletions, listGuestCompletions } from '@/utils/storage.ts'

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

  clearGuestCompletions()
  return failures
}
