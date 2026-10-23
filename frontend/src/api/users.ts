import { request } from '@/api/client.ts'
import type { UserStats } from '@/types/stats.ts'

export function getMyStats(): Promise<UserStats> {
  return request<UserStats>('/users/me/stats')
}
