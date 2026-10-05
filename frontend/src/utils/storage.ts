const TOKEN_KEY = 'auth_token'
const EMAIL_KEY = 'auth_email'
const STREAK_KEY = 'guest_streak'
const COMPLETIONS_KEY = 'guest_completions'
const STATS_EVENT = 'guest-stats'

export type GuestCompletion = {
  puzzleId: string
  assignedDate: string | null
  timeTakenSeconds: number
  answer: string | number
  isCorrect: boolean
  countedForStreak: boolean
}

function notify(): void {
  window.dispatchEvent(new Event(STATS_EVENT))
}

export function utcToday(): string {
  return new Date().toISOString().slice(0, 10)
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getEmail(): string | null {
  return localStorage.getItem(EMAIL_KEY)
}

export function setEmail(email: string): void {
  localStorage.setItem(EMAIL_KEY, email)
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(EMAIL_KEY)
}

export function getStreak(): number {
  const raw = localStorage.getItem(STREAK_KEY)
  const value = raw ? Number(raw) : 0
  return Number.isFinite(value) ? value : 0
}

export function listGuestCompletions(): GuestCompletion[] {
  const raw = localStorage.getItem(COMPLETIONS_KEY)
  if (!raw) return []
  try {
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as GuestCompletion[]) : []
  } catch {
    return []
  }
}

function writeCompletions(entries: GuestCompletion[]): void {
  localStorage.setItem(COMPLETIONS_KEY, JSON.stringify(entries))
}

export function clearGuestCompletions(): void {
  localStorage.removeItem(COMPLETIONS_KEY)
  notify()
}

export function recordGuestCompletion(
  entry: Omit<GuestCompletion, 'countedForStreak'>,
): GuestCompletion {
  const list = listGuestCompletions()
  const existing = list.find((item) => item.puzzleId === entry.puzzleId)
  if (existing) return existing

  const stored: GuestCompletion = { ...entry, countedForStreak: false }
  list.push(stored)
  writeCompletions(list)
  notify()
  return stored
}

export function bumpStreakIfDaily(
  puzzleId: string,
  assignedDate: string | null,
  isCorrect: boolean,
): number {
  const current = getStreak()
  if (!isCorrect || assignedDate !== utcToday()) return current

  const list = listGuestCompletions()
  const entry = list.find((item) => item.puzzleId === puzzleId)
  if (!entry || entry.countedForStreak) return current

  entry.countedForStreak = true
  writeCompletions(list)
  const next = current + 1
  localStorage.setItem(STREAK_KEY, String(next))
  notify()
  return next
}

export function subscribeGuestStats(listener: () => void): () => void {
  window.addEventListener(STATS_EVENT, listener)
  return () => window.removeEventListener(STATS_EVENT, listener)
}
