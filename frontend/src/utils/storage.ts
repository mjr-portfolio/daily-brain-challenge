import type { AnswerType } from '@/types/submit.ts'

const TOKEN_KEY = 'auth_token'
const REFRESH_KEY = 'auth_refresh_token'
const EMAIL_KEY = 'auth_email'
export const SESSION_CLEARED_EVENT = 'auth-session-cleared'
const STREAK_KEY = 'guest_streak'
const STREAK_DATE_KEY = 'guest_streak_date'
const COMPLETIONS_KEY = 'guest_completions'
const PLAYED_DAILY_DATES_KEY = 'played_daily_dates'
const DAILY_STARTS_KEY = 'daily_started_at'
const ARCHIVE_STARTS_KEY = 'archive_started_at'
const GUEST_SCOPE = 'guest'
const START_LIMIT_MS = 60 * 60 * 1000
const STATS_EVENT = 'guest-stats'

export type GuestCompletion = {
  puzzleId: string
  assignedDate: string | null
  timeTakenSeconds: number
  answer: AnswerType
  isCorrect: boolean
  countedForStreak: boolean
}

function notify(): void {
  window.dispatchEvent(new Event(STATS_EVENT))
}

export function utcToday(): string {
  return new Date().toISOString().slice(0, 10)
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(EMAIL_KEY)
}

export function clearGuestProgress(): void {
  localStorage.removeItem(STREAK_KEY)
  localStorage.removeItem(STREAK_DATE_KEY)
  localStorage.removeItem(COMPLETIONS_KEY)
  localStorage.removeItem(PLAYED_DAILY_DATES_KEY)
  notify()
}

export function getStreak(): number {
  return visibleGuestStreak()
}

export type GuestStreakRecord = {
  count: number
  lastDate: string | null
}

export function getGuestStreakRecord(): GuestStreakRecord {
  const raw = localStorage.getItem(STREAK_KEY)
  const count = raw ? Number(raw) : 0
  return {
    count: Number.isFinite(count) ? count : 0,
    lastDate: localStorage.getItem(STREAK_DATE_KEY),
  }
}

export function visibleGuestStreak(): number {
  const today = utcToday()
  const { count, lastDate } = getGuestStreakRecord()
  const visible = displayStreak(count, lastDate, today)
  if (lastDate && visible === 0 && count !== 0) {
    localStorage.setItem(STREAK_KEY, '0')
    notify()
  }
  return visible
}

export function clearGuestStreak(): void {
  localStorage.removeItem(STREAK_KEY)
  localStorage.removeItem(STREAK_DATE_KEY)
  notify()
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

function listPlayedDailyDates(): string[] {
  const raw = localStorage.getItem(PLAYED_DAILY_DATES_KEY)
  if (!raw) return []
  try {
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((item) => typeof item === 'string') : []
  } catch {
    return []
  }
}

export function markDailyPlayedLocally(assignedDate: string): void {
  const dates = listPlayedDailyDates()
  if (dates.includes(assignedDate)) return
  dates.push(assignedDate)
  localStorage.setItem(PLAYED_DAILY_DATES_KEY, JSON.stringify(dates))
  notify()
}

export function hasCompletedDailyLocally(assignedDate: string): boolean {
  if (listPlayedDailyDates().includes(assignedDate)) return true
  return listGuestCompletions().some((entry) => entry.assignedDate === assignedDate)
}

export function dropGuestCompletions(puzzleIds: string[]): void {
  const drop = new Set(puzzleIds)
  const entries = listGuestCompletions().filter((entry) => !drop.has(entry.puzzleId))
  if (entries.length === 0) localStorage.removeItem(COMPLETIONS_KEY)
  else writeCompletions(entries)
  notify()
}

export function recordGuestCompletion(
  entry: Omit<GuestCompletion, 'countedForStreak'>,
): GuestCompletion {
  const list = listGuestCompletions()
  const existing = list.find((item) => item.puzzleId === entry.puzzleId)
  if (existing) {
    if (existing.assignedDate === utcToday()) markDailyPlayedLocally(existing.assignedDate)
    return existing
  }

  const stored: GuestCompletion = { ...entry, countedForStreak: false }
  list.push(stored)
  writeCompletions(list)
  if (entry.assignedDate === utcToday()) markDailyPlayedLocally(entry.assignedDate)
  notify()
  return stored
}

export function bumpStreakIfDaily(puzzleId: string, assignedDate: string | null): number {
  const today = utcToday()
  if (assignedDate !== today) return visibleGuestStreak()

  const list = listGuestCompletions()
  const entry = list.find((item) => item.puzzleId === puzzleId)
  if (!entry || entry.countedForStreak) return visibleGuestStreak()

  entry.countedForStreak = true
  writeCompletions(list)
  const { count, lastDate } = getGuestStreakRecord()
  const visible = displayStreak(count, lastDate, today)
  const next = lastDate === shiftUtcDate(today, -1) && visible > 0 ? visible + 1 : 1
  return writeGuestStreak(next, today)
}

function writeGuestStreak(count: number, lastDate: string): number {
  localStorage.setItem(STREAK_KEY, String(count))
  localStorage.setItem(STREAK_DATE_KEY, lastDate)
  notify()
  return count
}

function displayStreak(count: number, lastDate: string | null, today: string): number {
  if (!lastDate || lastDate < shiftUtcDate(today, -1)) return 0
  return Math.max(0, count)
}

function shiftUtcDate(isoDate: string, days: number): string {
  const [year, month, day] = isoDate.split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

export function getDailyStartedAt(puzzleId: string): number | null {
  return readFreshStamp(DAILY_STARTS_KEY, GUEST_SCOPE, puzzleId)
}

export function markDailyStarted(puzzleId: string): number {
  return ensureFreshStamp(DAILY_STARTS_KEY, GUEST_SCOPE, puzzleId)
}

export function ensureArchiveStarted(puzzleId: string, accountKey: string): number {
  return ensureFreshStamp(ARCHIVE_STARTS_KEY, accountKey, puzzleId)
}

type StampBook = Record<string, Record<string, number>>

function readBook(key: string): StampBook {
  const raw = localStorage.getItem(key)
  if (!raw) return {}
  try {
    const parsed: unknown = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    const book: StampBook = {}
    for (const [scope, value] of Object.entries(parsed)) {
      if (!value || typeof value !== 'object' || Array.isArray(value)) continue
      const stamps = Object.fromEntries(
        Object.entries(value).filter((entry): entry is [string, number] => typeof entry[1] === 'number'),
      )
      if (Object.keys(stamps).length > 0) book[scope] = stamps
    }
    return book
  } catch {
    return {}
  }
}

function writeBook(key: string, book: StampBook): void {
  localStorage.setItem(key, JSON.stringify(book))
}

function readFreshStamp(key: string, scope: string, puzzleId: string): number | null {
  const existing = readBook(key)[scope]?.[puzzleId]
  if (typeof existing !== 'number') return null
  if (Date.now() - existing > START_LIMIT_MS) return null
  return existing
}

function ensureFreshStamp(key: string, scope: string, puzzleId: string): number {
  const book = readBook(key)
  const stamps = book[scope] ?? {}
  const existing = stamps[puzzleId]
  const now = Date.now()
  if (typeof existing === 'number' && now - existing <= START_LIMIT_MS) return existing
  stamps[puzzleId] = now
  book[scope] = stamps
  writeBook(key, book)
  return now
}

export function subscribeGuestStats(listener: () => void): () => void {
  window.addEventListener(STATS_EVENT, listener)
  return () => window.removeEventListener(STATS_EVENT, listener)
}
