import { request } from '@/api/client.ts'

export type TokenResponse = {
  access_token: string
  token_type: string
}

export type AccountRead = {
  email: string
  streak: number
  total_score: number
}

export function requestToken(email: string): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/token', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export function getAccount(): Promise<AccountRead> {
  return request<AccountRead>('/auth/me')
}

export function adoptGuestStreak(count: number, lastDate: string | null): Promise<AccountRead> {
  return request<AccountRead>('/auth/streak', {
    method: 'POST',
    body: JSON.stringify({ count, last_date: lastDate }),
  })
}
