import { useState } from 'react'
import { ModalFrame } from '@/components/ModalFrame.tsx'
import { useUserStats } from '@/hooks/useUserStats.ts'
import type { CategoryStats, StatsSlice } from '@/types/stats.ts'
import { formatTime } from '@/utils/time.ts'

const CATEGORIES: Array<{ key: 'pattern' | 'anagram' | 'news_quiz'; label: string }> = [
  { key: 'pattern', label: 'Patterns' },
  { key: 'anagram', label: 'Anagrams' },
  { key: 'news_quiz', label: 'News' },
]

function formatPercent(value: number | null): string {
  if (value == null) return '—'
  return Number.isInteger(value) ? `${value}%` : `${value.toFixed(1)}%`
}

function formatSpeed(seconds: number | null): string {
  if (seconds == null) return '—'
  return formatTime(Math.round(seconds))
}

export function AccountStatsModal({
  open,
  email,
  onClose,
}: {
  open: boolean
  email: string | null
  onClose: () => void
}) {
  const stats = useUserStats(open)
  const [scope, setScope] = useState<'daily' | 'overall'>('daily')
  if (!open) return null

  const slice = stats.data ? stats.data[scope] : null

  return (
    <ModalFrame title="Account" subtitle={email} onClose={onClose} wide>
      <div className="flex gap-2">
        <ScopeButton selected={scope === 'daily'} onClick={() => setScope('daily')}>
          Daily
        </ScopeButton>
        <ScopeButton selected={scope === 'overall'} onClick={() => setScope('overall')}>
          Overall
        </ScopeButton>
      </div>
      <p className="mt-3 text-sm text-slate-400">
        {scope === 'daily'
          ? 'Ranked daily plays, plus your live streak.'
          : 'Every puzzle you have finished, including the archive.'}
      </p>
      {stats.isLoading ? <p className="mt-4 text-sm text-slate-400">Loading stats…</p> : null}
      {stats.isError ? <p className="mt-4 text-sm text-rose-300">Could not load your stats.</p> : null}
      {stats.data && slice ? (
        <>
          <dl className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3">
            {scope === 'daily' ? (
              <>
                <Stat label="Active Streak 🔥" value={String(stats.data.current_streak)} />
                <Stat label="Best Streak ⚡" value={String(stats.data.best_streak)} />
              </>
            ) : (
              <>
                <Stat label="Completion" value={formatPercent(slice.completion_percent)} />
                <Stat label="Left to play" value={String(slice.left_to_play)} />
              </>
            )}
            <Stat label="Puzzles Solved 🧩" value={String(slice.puzzles_solved)} />
            <Stat label="Win Rate" value={formatPercent(slice.win_rate)} />
            <Stat label="Avg Speed ⏱️" value={formatSpeed(slice.average_completion_time_seconds)} />
          </dl>
          <CategoryList slice={slice} scope={scope} />
        </>
      ) : null}
    </ModalFrame>
  )
}

function ScopeButton({
  selected,
  onClick,
  children,
}: {
  selected: boolean
  onClick: () => void
  children: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-sm ${
        selected
          ? 'bg-amber-400 text-slate-950'
          : 'border border-slate-700 text-slate-300 hover:border-amber-400'
      }`}
    >
      {children}
    </button>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2">
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className="mt-1 text-lg font-semibold tabular-nums text-white">{value}</dd>
    </div>
  )
}

function CategoryList({ slice, scope }: { slice: StatsSlice; scope: 'daily' | 'overall' }) {
  const heading =
    scope === 'daily'
      ? 'Correct daily puzzles of each type'
      : 'Attempted, out of every puzzle of each type'
  return (
    <div className="mt-5 space-y-3">
      <h3 className="text-sm text-slate-400">{heading}</h3>
      {CATEGORIES.map(({ key, label }) => (
        <CategoryRow key={key} label={label} category={slice.categories[key]} scope={scope} />
      ))}
    </div>
  )
}

function CategoryRow({
  label,
  category,
  scope,
}: {
  label: string
  category: CategoryStats
  scope: 'daily' | 'overall'
}) {
  const opened = Math.min(category.played, category.available)
  const width =
    scope === 'daily'
      ? category.played === 0
        ? 0
        : (category.solved / category.played) * 100
      : category.available === 0
        ? 0
        : (opened / category.available) * 100
  const detail =
    scope === 'daily'
      ? `${category.solved}/${category.played} solved`
      : `${opened}/${category.available} played`
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="text-slate-200">{label}</span>
        <span className="tabular-nums text-slate-400">{detail}</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div className="h-full rounded-full bg-amber-400" style={{ width: `${width}%` }} />
      </div>
    </div>
  )
}
