import { useState, type FormEvent } from 'react'
import { useAuth } from '@/hooks/useAuth.ts'

export function AuthModal() {
  const { authModalOpen, closeAuthModal, login } = useAuth()
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  if (!authModalOpen) return null

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await login(email.trim())
      setEmail('')
      closeAuthModal()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 p-4">
      <form
        onSubmit={onSubmit}
        className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-xl"
      >
        <h2 className="text-xl font-semibold text-white">Sign in</h2>
        <p className="mt-1 text-sm text-slate-400">
          Enter your email to save scores and unlock past puzzles.
        </p>
        <label className="mt-4 block text-sm text-slate-300" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-white outline-none focus:border-amber-400"
        />
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
            className="rounded-lg bg-amber-400 px-3 py-2 text-sm font-medium text-slate-950 disabled:opacity-60"
          >
            {pending ? 'Signing in…' : 'Continue'}
          </button>
        </div>
      </form>
    </div>
  )
}
