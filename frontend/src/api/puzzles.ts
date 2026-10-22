import { request } from '@/api/client.ts'
import type { ArchivePage, ArchivePuzzleType, DailyPreview, DailySession } from '@/types/puzzle.ts'
import type { SubmitPayload, SubmitResult } from '@/types/submit.ts'

export function getDaily(): Promise<DailyPreview> {
  return request<DailyPreview>('/puzzles/daily')
}

export function startDaily(): Promise<DailySession> {
  return request<DailySession>('/puzzles/daily/start', { method: 'POST' })
}

export function getPuzzleArchive({
  page = 1,
  limit = 20,
  puzzleType,
}: {
  page?: number
  limit?: number
  puzzleType?: ArchivePuzzleType
} = {}): Promise<ArchivePage> {
  const search = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  })
  if (puzzleType) search.set('puzzle_type', puzzleType)
  return request<ArchivePage>(`/puzzles/archive?${search.toString()}`)
}

export function submitPuzzle(id: string, payload: SubmitPayload): Promise<SubmitResult> {
  return request<SubmitResult>(`/puzzles/${id}/submit`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
