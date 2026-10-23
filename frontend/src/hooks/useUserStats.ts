import { useQuery } from '@tanstack/react-query'
import { getMyStats } from '@/api/users.ts'
import { useAuth } from '@/hooks/useAuth.ts'

export function userStatsKey(email: string | null) {
  return ['user', 'stats', email] as const
}

export function useUserStats(enabled: boolean) {
  const { email, isAuthenticated } = useAuth()
  return useQuery({
    queryKey: userStatsKey(email),
    queryFn: getMyStats,
    enabled: enabled && isAuthenticated,
  })
}
