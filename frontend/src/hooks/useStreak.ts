import { useAuth } from '@/hooks/useAuth.ts'
import { useGuestStreak } from '@/hooks/useGuestStreak.ts'

export function useStreak(): number {
  const { isAuthenticated, streak } = useAuth()
  const guestStreak = useGuestStreak()
  return isAuthenticated ? streak : guestStreak
}

export function useTotalScore(): number | null {
  const { isAuthenticated, totalScore } = useAuth()
  if (!isAuthenticated) return null
  return totalScore
}
