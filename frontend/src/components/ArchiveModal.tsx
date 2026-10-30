import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getPuzzleArchive } from '@/api/puzzles.ts'
import { useAuth } from '@/hooks/useAuth.ts'
import type { ArchivePuzzleItem, ArchivePuzzleType } from '@/types/puzzle.ts'

const PAGE_SIZE = 12

const FILTERS: { id: ArchivePuzzleType | 'all'; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'pattern', label: 'Pattern' },
  { id: 'anagram', label: 'Anagram' },
  { id: 'news_quiz', label: 'News' },
]

const TYPE_LABEL: Record<ArchivePuzzleType, string> = {
  pattern: 'Pattern',
  anagram: 'Anagram',
  news_quiz: 'News',
}

type ArchiveModalProps = {
  open: boolean
  onClose: () => void
  onSelect: (item: ArchivePuzzleItem) => void
}

export function ArchiveModal({ open, onClose, onSelect }: ArchiveModalProps) {
  const { email } = useAuth()
  const [page, setPage] = useState(1)
  const [filter, setFilter] = useState<ArchivePuzzleType | 'all'>('all')
  const puzzleType = filter === 'all' ? undefined : filter
  const archive = useQuery({
    queryKey: ['puzzle', 'archive', 'list', email ?? 'guest', page, puzzleType ?? 'all'],
    queryFn: () => getPuzzleArchive({ page, limit: PAGE_SIZE, puzzleType }),
    enabled: open,
  })

  if (!open) return null

  const total = archive.data?.total ?? 0
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))

  function selectFilter(next: ArchivePuzzleType | 'all') {
    setFilter(next)
    setPage(1)
  }

  return (
    <div
      className="fixed inset-0 z-40 flex items-start justify-center bg-black/60 px-4 pb-4 pt-20"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="archive-title"
        className="flex max-h-[min(40rem,100%)] w-full max-w-3xl flex-col rounded-2xl border border-slate-700 bg-slate-900 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-800 px-5 py-4">
          <div>
            <h2 id="archive-title" className="text-xl font-semibold text-white">
              Archive
            </h2>
            <p className="mt-1 text-sm text-slate-400">Play a past puzzle.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full px-3 py-1 text-sm text-slate-400 hover:text-white"
          >
            Close
          </button>
        </div>

        <div className="flex flex-wrap gap-2 px-5 pt-4">
          {FILTERS.map((option) => {
            const selected = option.id === filter
            return (
              <button
                key={option.id}
                type="button"
                onClick={() => selectFilter(option.id)}
                className={`rounded-full px-3 py-1 text-sm ${
                  selected
                    ? 'border border-amber-500 bg-amber-400 font-medium text-slate-950 hover:border-slate-950'
                    : 'border border-slate-700 text-slate-200 hover:border-amber-400'
                }`}
              >
                {option.label}
              </button>
            )
          })}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {archive.isLoading ? (
            <p className="text-sm text-slate-300">Loading archive…</p>
          ) : archive.isError ? (
            <div className="text-sm text-rose-100">
              <p>Could not load the archive.</p>
              <button
                type="button"
                onClick={() => void archive.refetch()}
                className="mt-2 underline"
              >
                Retry
              </button>
            </div>
          ) : archive.data && archive.data.items.length === 0 ? (
            <p className="text-sm text-slate-300">No puzzles in this archive.</p>
          ) : (
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {archive.data?.items.map((item) => (
                <li key={item.id}>
                  <ArchiveCard item={item} onSelect={() => onSelect(item)} />
                </li>
              ))}
            </ul>
          )}
        </div>

        {total > PAGE_SIZE ? (
          <div className="flex items-center justify-between border-t border-slate-800 px-5 py-3 text-sm text-slate-300">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              className="rounded-full border border-slate-700 px-3 py-1 hover:border-amber-400 disabled:opacity-40 disabled:hover:border-slate-700"
            >
              Previous
            </button>
            <span>
              Page {page} of {pageCount}
            </span>
            <button
              type="button"
              disabled={page >= pageCount}
              onClick={() => setPage((current) => current + 1)}
              className="rounded-full border border-slate-700 px-3 py-1 hover:border-amber-400 disabled:opacity-40 disabled:hover:border-slate-700"
            >
              Next
            </button>
          </div>
        ) : null}
      </div>
    </div>
  )
}

type ArchiveResult = 'solved' | 'incorrect' | 'unplayed'

const RESULT_CARD: Record<ArchiveResult, string> = {
  solved: 'border-emerald-400/40 bg-emerald-400/10 hover:border-emerald-400',
  incorrect: 'border-orange-400/40 bg-orange-400/10 hover:border-orange-400',
  unplayed: 'border-slate-800 bg-slate-950 hover:border-slate-600',
}

const RESULT_TEXT: Record<ArchiveResult, string> = {
  solved: 'text-emerald-200',
  incorrect: 'text-orange-200',
  unplayed: 'text-slate-400',
}

const RESULT_DOT: Record<ArchiveResult, string> = {
  solved: 'bg-emerald-300',
  incorrect: 'bg-orange-300',
  unplayed: 'bg-slate-500',
}

const RESULT_LABEL: Record<ArchiveResult, string> = {
  solved: 'Solved',
  incorrect: 'Incorrect',
  unplayed: 'Unplayed',
}

function ArchiveCard({ item, onSelect }: { item: ArchivePuzzleItem; onSelect: () => void }) {
  const result = archiveResult(item)
  const body = (
    <>
      <span className="text-sm font-medium text-white">{formatAssignedDate(item.assigned_date)}</span>
      <span className="mt-1 text-xs text-slate-400">{TYPE_LABEL[item.puzzle_type]}</span>
      <span className={`mt-3 inline-flex items-center gap-2 text-xs ${RESULT_TEXT[result]}`}>
        <span className={`h-2 w-2 rounded-full ${RESULT_DOT[result]}`} aria-hidden="true" />
        {RESULT_LABEL[result]}
        {result !== 'unplayed' && item.score != null ? ` · ${item.score}` : ''}
      </span>
    </>
  )
  if (result !== 'unplayed') {
    return (
      <div
        title="Already played"
        className={`flex h-full w-full flex-col rounded-2xl border p-4 text-left ${RESULT_CARD[result]}`}
      >
        {body}
      </div>
    )
  }
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex h-full w-full flex-col rounded-2xl border p-4 text-left ${RESULT_CARD[result]}`}
    >
      {body}
    </button>
  )
}

function archiveResult(item: ArchivePuzzleItem): ArchiveResult {
  if (!item.is_completed || item.is_correct == null) return 'unplayed'
  return item.is_correct ? 'solved' : 'incorrect'
}

function formatAssignedDate(value: string): string {
  const [year, month, day] = value.split('-').map(Number)
  if (!year || !month || !day) return value
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  })
}
