import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getAccount,
  loginAccount,
  logoutAccount,
  registerAccount,
  type AccountRead,
  type ThemePreference,
} from '@/api/auth.ts'
import { deleteMyAccount } from '@/api/users.ts'
import { migrateGuestDataToAccount } from '@/services/migration.ts'
import {
  SESSION_CLEARED_EVENT,
  clearAuth,
  clearGuestCompletions,
  listGuestCompletions,
  markDailyPlayedLocally,
  utcToday,
} from '@/utils/storage.ts'
import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

export type AuthContextValue = {
  email: string | null
  displayName: string | null
  streak: number
  totalScore: number
  isAuthenticated: boolean
  sessionPending: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName?: string) => Promise<void>
  logout: () => Promise<void>
  loggingOut: boolean
  deleteAccount: (password: string) => Promise<void>
  updateAccount: (account: AccountRead) => void
  authModalOpen: boolean
  openAuthModal: () => void
  closeAuthModal: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export { AuthContext }

function applyTheme(theme: ThemePreference): void {
  document.documentElement.dataset.theme = theme
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const migratedFor = useRef<string | null>(null)
  const account = useQuery({
    queryKey: ['account'],
    queryFn: getAccount,
    retry: false,
  })

  useEffect(() => {
    clearAuth()
  }, [])

  useEffect(() => {
    const current = account.data?.email ?? null
    if (!current) {
      migratedFor.current = null
      return
    }
    if (migratedFor.current === current) return
    migratedFor.current = current
    keepTodayLocked()
    void migrateGuestDataToAccount().finally(() => {
      void queryClient.invalidateQueries({ queryKey: ['account'] })
    })
  }, [account.data, queryClient])

  useEffect(() => {
    applyTheme(account.data?.preferences.theme ?? 'dark')
  }, [account.data?.preferences.theme])

  useEffect(() => {
    function onCleared() {
      queryClient.setQueryData(['account'], null)
      applyTheme('dark')
      queryClient.removeQueries({ queryKey: ['puzzle'] })
    }
    window.addEventListener(SESSION_CLEARED_EVENT, onCleared)
    return () => window.removeEventListener(SESSION_CLEARED_EVENT, onCleared)
  }, [queryClient])

  const rememberAccount = useCallback((next: AccountRead) => {
    queryClient.setQueryData(['account'], next)
    queryClient.removeQueries({ queryKey: ['puzzle'] })
    applyTheme(next.preferences.theme)
  }, [queryClient])

  const login = useCallback(async (nextEmail: string, password: string) => {
    rememberAccount(await loginAccount(nextEmail, password))
  }, [rememberAccount])

  const register = useCallback(async (nextEmail: string, password: string, displayName?: string) => {
    rememberAccount(await registerAccount(nextEmail, password, displayName))
  }, [rememberAccount])

  const forgetLocalSession = useCallback(() => {
    keepTodayLocked()
    clearAuth()
    clearGuestCompletions()
    queryClient.setQueryData(['account'], null)
    applyTheme('dark')
    queryClient.removeQueries({ queryKey: ['puzzle'] })
  }, [queryClient])

  const logout = useCallback(async () => {
    setLoggingOut(true)
    try {
      await logoutAccount()
    } catch {
      // Drop the browser session even when the cookie is already gone.
    } finally {
      forgetLocalSession()
      setLoggingOut(false)
    }
  }, [forgetLocalSession])

  const deleteAccount = useCallback(async (password: string) => {
    await deleteMyAccount(password)
    forgetLocalSession()
  }, [forgetLocalSession])

  const updateAccount = useCallback((next: AccountRead) => {
    queryClient.setQueryData(['account'], next)
    applyTheme(next.preferences.theme)
  }, [queryClient])

  const value = useMemo<AuthContextValue>(
    () => ({
      email: account.data?.email ?? null,
      displayName: account.data?.display_name ?? null,
      streak: account.data?.streak ?? 0,
      totalScore: account.data?.total_score ?? 0,
      isAuthenticated: account.data != null,
      sessionPending: account.isPending,
      login,
      register,
      logout,
      loggingOut,
      deleteAccount,
      updateAccount,
      authModalOpen,
      openAuthModal: () => setAuthModalOpen(true),
      closeAuthModal: () => setAuthModalOpen(false),
    }),
    [
      account.data,
      account.isPending,
      login,
      register,
      logout,
      loggingOut,
      deleteAccount,
      updateAccount,
      authModalOpen,
    ],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

function keepTodayLocked(): void {
  const today = utcToday()
  if (listGuestCompletions().some((entry) => entry.assignedDate === today)) {
    markDailyPlayedLocally(today)
  }
}
