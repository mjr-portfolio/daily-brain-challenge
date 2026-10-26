import { useState, type FormEvent } from 'react'
import { useAuth } from '@/hooks/useAuth.ts'

export function AuthModal() {
  const { authModalOpen, closeAuthModal, login, register } = useAuth()
  const [mode, setMode] = useState<'sign-in' | 'create'>('sign-in')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  if (!authModalOpen) return null

  function switchMode(next: 'sign-in' | 'create') {
    setMode(next)
    setError(null)
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError(null)
    const normalized = email.trim().toLowerCase()
    try {
      if (mode === 'create') {
        const handle = displayName.trim()
        if (!handle) {
          setError('Display name is required')
          setPending(false)
          return
        }
        await register(normalized, password, handle)
      } else {
        await login(normalized, password)
      }
      setEmail('')
      setPassword('')
      setDisplayName('')
      closeAuthModal()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in')
    } finally {
      setPending(false)
    }
  }

  const creating = mode === 'create'

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-xl"
      >
        <h2 className="text-xl font-semibold text-white">
          {creating ? 'Create account' : 'Sign in'}
        </h2>
        <p className="mt-1 text-sm text-slate-400">
          {creating
            ? 'Save your streak and unlock past puzzles.'
            : 'Use the email and password for your account.'}
        </p>
        <div className="mt-4 flex gap-2">
          <button
            type="button"
            onClick={() => switchMode('sign-in')}
            className={`rounded-full px-3 py-1 text-sm ${
              mode === 'sign-in'
                ? 'bg-amber-400 text-slate-950'
                : 'border border-slate-700 text-slate-300'
            }`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => switchMode('create')}
            className={`rounded-full px-3 py-1 text-sm ${
              creating
                ? 'bg-amber-400 text-slate-950'
                : 'border border-slate-700 text-slate-300'
            }`}
          >
            Create account
          </button>
        </div>
        <label className="mt-4 block text-sm text-slate-300" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-400"
        />
        <label className="mt-4 block text-sm text-slate-300" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          required
          minLength={creating ? 8 : 1}
          autoComplete={creating ? 'new-password' : 'current-password'}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-400"
        />
        {creating ? (
          <>
            <label className="mt-4 block text-sm text-slate-300" htmlFor="display-name">
              Display name
            </label>
            <input
              id="display-name"
              type="text"
              required
              minLength={2}
              maxLength={32}
              autoComplete="nickname"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-400"
            />
            <p className="mt-1 text-xs text-slate-500">Letters, numbers, and underscores.</p>
          </>
        ) : null}
        {error ? <p className="mt-2 text-sm text-rose-300">{error}</p> : null}
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={closeAuthModal}
            className="rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={pending}
            className="rounded-lg border border-amber-500 bg-amber-400 px-3 py-2 text-sm font-medium text-slate-950 hover:border-slate-950 disabled:opacity-60"
          >
            {pending ? 'Saving…' : creating ? 'Create account' : 'Sign in'}
          </button>
        </div>
      </form>
    </div>
  )
}
