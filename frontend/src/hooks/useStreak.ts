import { useQuery } from '@tanstack/react-query'
import { getAccount } from '@/api/auth.ts'
import { useAuth } from '@/hooks/useAuth.ts'
import { useGuestStreak } from '@/hooks/useGuestStreak.ts'

export function useStreak(): number {
  const { email, isAuthenticated } = useAuth()
  const guestStreak = useGuestStreak()
  const account = useQuery({
    queryKey: ['streak', email],
    queryFn: getAccount,
    enabled: isAuthenticated,
  })
  return isAuthenticated ? (account.data?.streak ?? 0) : guestStreak
}
