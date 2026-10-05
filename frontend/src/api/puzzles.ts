import { request } from '@/api/client.ts'
import type { Puzzle } from '@/types/puzzle.ts'
import type { SubmitPayload, SubmitResult } from '@/types/submit.ts'

export function getDaily(): Promise<Puzzle> {
  return request<Puzzle>('/puzzles/daily')
}

export function getArchiveNext(): Promise<Puzzle> {
  return request<Puzzle>('/puzzles/archive/next')
}

export function submitPuzzle(id: string, payload: SubmitPayload): Promise<SubmitResult> {
  return request<SubmitResult>(`/puzzles/${id}/submit`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
