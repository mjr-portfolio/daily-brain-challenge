import { requestToken } from '@/api/auth.ts'
import { migrateGuestDataToAccount } from '@/services/migration.ts'
import {
  clearAuth,
  getEmail,
  getToken,
  setEmail,
  setToken,
} from '@/utils/storage.ts'
import {
  createContext,
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type AuthContextValue = {
  token: string | null
  email: string | null
  isAuthenticated: boolean
  login: (email: string) => Promise<void>
  logout: () => void
  authModalOpen: boolean
  openAuthModal: () => void
  closeAuthModal: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export { AuthContext }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken())
  const [email, setEmailState] = useState<string | null>(() => getEmail())
  const [authModalOpen, setAuthModalOpen] = useState(false)

  const login = useCallback(async (nextEmail: string) => {
    const response = await requestToken(nextEmail)
    setToken(response.access_token)
    setEmail(nextEmail)
    setTokenState(response.access_token)
    setEmailState(nextEmail)
    await migrateGuestDataToAccount()
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    setTokenState(null)
    setEmailState(null)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      email,
      isAuthenticated: Boolean(token),
      login,
      logout,
      authModalOpen,
      openAuthModal: () => setAuthModalOpen(true),
      closeAuthModal: () => setAuthModalOpen(false),
    }),
    [token, email, login, logout, authModalOpen],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

