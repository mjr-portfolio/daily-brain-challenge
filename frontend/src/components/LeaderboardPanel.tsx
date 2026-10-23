import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getDailyLeaderboard } from '@/api/puzzles.ts'
import { ModalFrame } from '@/components/ModalFrame.tsx'
import type { LeaderboardLimit } from '@/types/leaderboard.ts'
import { formatTime } from '@/utils/time.ts'

const LIMITS: LeaderboardLimit[] = [10, 25, 50, 100]

export function LeaderboardPanel() {
  const [limit, setLimit] = useState<LeaderboardLimit>(25)
  const board = useQuery({
    queryKey: ['leaderboard', 'daily', limit],
    queryFn: () => getDailyLeaderboard(limit),
  })

  const viewer = board.data?.viewer ?? null
  const viewerOnPage = board.data?.entries.some((entry) => entry.is_viewer) ?? false

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {LIMITS.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setLimit(option)}
            className={`rounded-full px-3 py-1 text-xs ${
              option === limit
                ? 'bg-amber-400 text-slate-950'
                : 'border border-slate-700 text-slate-300 hover:border-amber-400'
            }`}
          >
            Top {option}
          </button>
        ))}
      </div>
      {board.isLoading ? <p className="mt-4 text-sm text-slate-400">Loading standings…</p> : null}
      {board.isError ? (
        <p className="mt-4 text-sm text-rose-300">Could not load today's leaderboard.</p>
      ) : null}
      {board.data && board.data.entries.length === 0 ? (
        <p className="mt-4 text-sm text-slate-400">No ranked finishes yet.</p>
      ) : null}
      {board.data && board.data.entries.length > 0 ? (
        <ol className="mt-4 space-y-1">
          {board.data.entries.map((entry) => (
            <li
              key={`${entry.rank}-${entry.display_name}`}
              className={`flex items-center gap-3 rounded-lg px-2 py-1.5 text-sm ${
                entry.is_viewer ? 'bg-amber-400/15 text-amber-100' : 'text-slate-200'
              }`}
            >
              <span className="w-8 tabular-nums text-slate-400">{entry.rank}</span>
              <span className="min-w-0 flex-1 truncate">{entry.display_name}</span>
              <span className="tabular-nums">{entry.score}</span>
              <span className="w-14 text-right tabular-nums text-slate-400">
                {formatTime(entry.completion_time_seconds)}
              </span>
            </li>
          ))}
        </ol>
      ) : null}
      {viewer && !viewerOnPage ? (
        <p className="mt-3 rounded-lg bg-amber-400/15 px-2 py-1.5 text-sm text-amber-100">
          You · {viewer.display_name} · rank {viewer.rank} · {viewer.score} pts ·{' '}
          {formatTime(viewer.completion_time_seconds)}
        </p>
      ) : null}
    </div>
  )
}

export function LeaderboardModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null

  return (
    <ModalFrame title="Today's leaderboard" onClose={onClose} wide>
      <LeaderboardPanel />
    </ModalFrame>
  )
}
