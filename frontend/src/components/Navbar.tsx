import { Link } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth.ts'
import { useGuestStreak } from '@/hooks/useGuestStreak.ts'

export function Navbar() {
  const streak = useGuestStreak()
  const { isAuthenticated, email, logout, openAuthModal } = useAuth()

  return (
    <header className="border-b border-slate-800 bg-slate-950/80">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
        <Link to="/" className="text-lg font-semibold tracking-tight text-white">
          Daily Challenge
        </Link>
        <p className="flex items-center gap-1 text-sm text-amber-300" title="Daily streak">
          <FlameIcon />
          <span>{streak}</span>
        </p>
        <nav className="ml-auto flex items-center gap-3">
          {isAuthenticated ? (
            <Link
              to="/archive"
              className="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-200 hover:border-amber-400"
            >
              Archive
            </Link>
          ) : (
            <span
              className="cursor-not-allowed rounded-full border border-slate-800 px-3 py-1 text-sm text-slate-500"
              title="Sign in to play past puzzles"
            >
              Archive
            </span>
          )}
          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              <span className="max-w-40 truncate text-sm text-slate-300">{email}</span>
              <button
                type="button"
                onClick={logout}
                className="rounded-full bg-slate-800 px-3 py-1 text-sm text-white hover:bg-slate-700"
              >
                Log out
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={openAuthModal}
              className="rounded-full bg-amber-400 px-3 py-1 text-sm font-medium text-slate-950 hover:bg-amber-300"
            >
              Sign in
            </button>
          )}
        </nav>
      </div>
    </header>
  )
}

function FlameIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-amber-400" aria-hidden="true">
      <path d="M12 2s1.5 3 1.5 5.2c0 1.3-.7 2.2-1.5 2.8.8-.2 2.2-.2 3.2.8 1.2 1.2 1.8 2.8 1.8 4.7A6.5 6.5 0 0 1 10.5 22 6.5 6.5 0 0 1 7 12.6c0-1.6.6-3 1.6-4.2C10 6.6 12 2 12 2z" />
    </svg>
  )
}
