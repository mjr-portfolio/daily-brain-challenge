import { SESSION_CLEARED_EVENT, clearAuth } from '@/utils/storage.ts'

// Default /api is same-origin: Vite proxies locally, vercel.json proxies in
// production. Leave VITE_API_BASE unset so Safari can keep auth cookies.
const configured = import.meta.env.VITE_API_BASE?.trim()
export const API_BASE = configured ? configured.replace(/\/$/, '') : '/api'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const REFRESH_SKIP = new Set(['/auth/refresh', '/auth/login', '/auth/register'])

let refreshing: Promise<boolean> | null = null

function readDetail(body: unknown): string | null {
  if (!body || typeof body !== 'object' || !('detail' in body)) return null
  const detail = body.detail
  if (typeof detail === 'string') return detail
  if (!Array.isArray(detail)) return null
  for (const item of detail) {
    if (item && typeof item === 'object' && 'msg' in item && typeof item.msg === 'string') {
      return item.msg
    }
  }
  return null
}

async function refreshOnce(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
    if (!response.ok) {
      clearAuth()
      window.dispatchEvent(new Event(SESSION_CLEARED_EVENT))
      return false
    }
    return true
  } catch {
    return false
  }
}

function refreshSession(): Promise<boolean> {
  refreshing ??= refreshOnce().finally(() => {
    refreshing = null
  })
  return refreshing
}

export async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body != null && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  })
  if (response.status === 401 && retry && !REFRESH_SKIP.has(path)) {
    const refreshed = await refreshSession()
    if (refreshed) return request<T>(path, init, false)
  }

  if (!response.ok) {
    let detail = response.statusText
    try {
      detail = readDetail(await response.json()) ?? detail
    } catch {
      // non-JSON error body
    }
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
