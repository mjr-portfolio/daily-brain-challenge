import { useEffect, useState } from 'react'
import { getStreak, subscribeGuestStats } from '@/utils/storage.ts'

export function useGuestStreak(): number {
  const [streak, setStreak] = useState(getStreak)

  useEffect(() => subscribeGuestStats(() => setStreak(getStreak())), [])

  return streak
}
