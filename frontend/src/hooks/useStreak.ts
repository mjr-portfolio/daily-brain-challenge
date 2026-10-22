import { useQuery } from '@tanstack/react-query'
import { getAccount } from '@/api/auth.ts'
import { useAuth } from '@/hooks/useAuth.ts'
import { useGuestStreak } from '@/hooks/useGuestStreak.ts'

function useAccount() {
  const { email, isAuthenticated } = useAuth()
  return useQuery({
    queryKey: ['streak', email],
    queryFn: getAccount,
    enabled: isAuthenticated,
  })
}

export function useStreak(): number {
  const { isAuthenticated } = useAuth()
  const guestStreak = useGuestStreak()
  const account = useAccount()
  return isAuthenticated ? (account.data?.streak ?? 0) : guestStreak
}

export function useTotalScore(): number | null {
  const { isAuthenticated } = useAuth()
  const account = useAccount()
  if (!isAuthenticated) return null
  return account.data?.total_score ?? 0
}
