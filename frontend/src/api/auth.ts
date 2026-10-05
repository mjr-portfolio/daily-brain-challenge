import { request } from '@/api/client.ts'

export type TokenResponse = {
  access_token: string
  token_type: string
}

export function requestToken(email: string): Promise<TokenResponse> {
  return request<TokenResponse>('/auth/token', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}
