import { request } from '@/api/client.ts'
import type { AccountRead, ThemePreference } from '@/api/auth.ts'
import type { UserStats } from '@/types/stats.ts'

export type ProfileUpdate = {
  display_name?: string | null
  email?: string
  theme?: ThemePreference
  current_password?: string
  new_password?: string
}

export function getMyStats(): Promise<UserStats> {
  return request<UserStats>('/users/me/stats')
}

export function updateMe(body: ProfileUpdate): Promise<AccountRead> {
  return request<AccountRead>('/users/me', {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export function deleteMyAccount(password: string): Promise<void> {
  return request<void>('/users/me', {
    method: 'DELETE',
    body: JSON.stringify({ password }),
  })
}
