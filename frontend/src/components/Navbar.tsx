import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AccountStatsModal } from '@/components/AccountStatsModal.tsx'
import { useAuth } from '@/hooks/useAuth.ts'
import { useStreak, useTotalScore } from '@/hooks/useStreak.ts'

export function Navbar({ onOpenArchive }: { onOpenArchive: () => void }) {
  const streak = useStreak()
  const totalScore = useTotalScore()
  const { isAuthenticated, email, logout, openAuthModal } = useAuth()
  const [statsOpen, setStatsOpen] = useState(false)

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
        {totalScore != null ? (
          <p className="text-sm text-slate-300" title="Total score">
            {totalScore} pts
          </p>
        ) : null}
        <nav className="ml-auto flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenArchive}
            className="rounded-full border border-slate-700 px-3 py-1 text-sm text-slate-200 hover:border-amber-400"
          >
            Archive
          </button>
          {isAuthenticated ? (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setStatsOpen(true)}
                aria-label={email ? `Account, ${email}` : 'Account'}
                className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-700 text-slate-200 hover:border-amber-400"
              >
                <UserIcon />
              </button>
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
              className="rounded-full border border-amber-500 bg-amber-400 px-3 py-1 text-sm font-medium text-slate-950 hover:border-slate-950"
            >
              Sign in
            </button>
          )}
        </nav>
      </div>
      <AccountStatsModal open={statsOpen} email={email} onClose={() => setStatsOpen(false)} />
    </header>
  )
}

function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
      <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-4.4 0-8 2.2-8 5v1h16v-1c0-2.8-3.6-5-8-5z" />
    </svg>
  )
}

function FlameIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-amber-400" aria-hidden="true">
      <path d="M12 2s1.5 3 1.5 5.2c0 1.3-.7 2.2-1.5 2.8.8-.2 2.2-.2 3.2.8 1.2 1.2 1.8 2.8 1.8 4.7A6.5 6.5 0 0 1 10.5 22 6.5 6.5 0 0 1 7 12.6c0-1.6.6-3 1.6-4.2C10 6.6 12 2 12 2z" />
    </svg>
  )
}
