import { request } from '@/api/client.ts'

export type ThemePreference = 'dark' | 'light'

export type Preferences = {
  theme: ThemePreference
}

export type AccountRead = {
  email: string
  display_name: string | null
  preferences: Preferences
  streak: number
  total_score: number
}

export type StreakAdoptResult = AccountRead & {
  applied: boolean
}

export function registerAccount(
  email: string,
  password: string,
  displayName?: string,
): Promise<AccountRead> {
  return request<AccountRead>('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email,
      password,
      ...(displayName ? { display_name: displayName } : {}),
    }),
  })
}

export function loginAccount(email: string, password: string): Promise<AccountRead> {
  return request<AccountRead>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function logoutAccount(): Promise<void> {
  return request<void>('/auth/logout', { method: 'POST' })
}

export function getAccount(): Promise<AccountRead> {
  return request<AccountRead>('/auth/me')
}

export function adoptGuestStreak(count: number, lastDate: string | null): Promise<StreakAdoptResult> {
  return request<StreakAdoptResult>('/auth/streak', {
    method: 'POST',
    body: JSON.stringify({ count, last_date: lastDate }),
  })
}
