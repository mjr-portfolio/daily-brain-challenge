import { useQuery } from '@tanstack/react-query'
import { getArchiveNext } from '@/api/puzzles.ts'
import { useAuth } from '@/hooks/useAuth.ts'

export function useArchivePuzzle() {
  const { isAuthenticated } = useAuth()
  return useQuery({
    queryKey: ['puzzle', 'archive', 'next'],
    queryFn: getArchiveNext,
    enabled: isAuthenticated,
    retry: false,
  })
}
