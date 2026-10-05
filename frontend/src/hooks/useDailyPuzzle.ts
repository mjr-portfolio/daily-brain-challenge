import { useQuery } from '@tanstack/react-query'
import { getDaily } from '@/api/puzzles.ts'

export function useDailyPuzzle() {
  return useQuery({
    queryKey: ['puzzle', 'daily'],
    queryFn: getDaily,
  })
}
