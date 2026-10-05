import { useMutation } from '@tanstack/react-query'
import { submitPuzzle } from '@/api/puzzles.ts'
import type { SubmitPayload } from '@/types/submit.ts'

export function useSubmitPuzzle() {
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: SubmitPayload }) =>
      submitPuzzle(id, payload),
  })
}
