import { useQuery } from '@tanstack/react-query'
import { getDaily } from '@/api/puzzles.ts'
import { useAuth } from '@/hooks/useAuth.ts'

export function useDailyPuzzle() {
  const { email } = useAuth()
  return useQuery({
    queryKey: ['puzzle', 'daily', email ?? 'guest'],
    queryFn: getDaily,
  })
}
