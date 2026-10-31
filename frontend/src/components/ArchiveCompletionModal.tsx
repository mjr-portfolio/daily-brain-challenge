import { useQuery } from '@tanstack/react-query'
import { getArchiveBenchmark } from '@/api/puzzles.ts'
import { ModalFrame } from '@/components/ModalFrame.tsx'
import type { ArchiveBenchmark } from '@/types/leaderboard.ts'
import { formatAnswer, type SubmitResult } from '@/types/submit.ts'
import { formatTime } from '@/utils/time.ts'

export function benchmarkLine(data: ArchiveBenchmark): string {
  const personal = data.viewer?.faster_than_percent
  const fastest = data.fastest_completion_time_seconds
  const viewerTime = data.viewer?.time_taken_seconds
  if (personal != null && fastest != null && viewerTime != null) {
    if (personal > 0) return `Faster than ${Math.round(personal)}% of solvers on this day`
    if (viewerTime === fastest) return 'Matched the fastest time on this day'
    return 'Slower than the solvers on this day'
  }
  if (data.median_completion_time_seconds != null) {
    return `Median time that day: ${formatTime(Math.round(data.median_completion_time_seconds))}`
  }
  return 'No live benchmark for this day.'
}

function formatScore(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}

function solverLabel(count: number): string {
  return `${count} ${count === 1 ? 'solver' : 'solvers'}`
}

function newsSearchUrl(headline: string): string {
  return `https://www.google.com/search?q=${encodeURIComponent(headline)}`
}

export function ArchiveCompletionModal({
  open,
  result,
  puzzleId,
  puzzleType = null,
  sourceHeadline = null,
  onClose,
}: {
  open: boolean
  result: SubmitResult | null
  puzzleId: string
  puzzleType?: string | null
  sourceHeadline?: string | null
  onClose: () => void
}) {
  const benchmark = useQuery({
    queryKey: ['benchmark', puzzleId],
    queryFn: () => getArchiveBenchmark(puzzleId),
    enabled: open,
  })

  if (!open || !result) return null

  const headline = sourceHeadline?.trim() ? sourceHeadline.trim() : null
  const showNewsLink = puzzleType === 'news_quiz' && headline != null

  return (
    <ModalFrame
      title={result.is_correct ? 'Correct!' : 'Not quite'}
      onClose={onClose}
      celebrate={result.is_correct}
    >
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Time
            </p>
            <p className="mt-0.5 text-sm font-semibold text-white">
              {formatTime(result.time_taken_seconds)}
            </p>
          </div>
          {result.score != null ? (
            <div className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                Score
              </p>
              <p className="mt-0.5 text-sm font-semibold text-amber-300">{result.score}</p>
            </div>
          ) : null}
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-950/70 px-4 py-3">
          <p className="text-sm text-slate-400">
            Correct answer:{' '}
            <span className="font-medium text-amber-200">
              {formatAnswer(result.correct_answer)}
            </span>
          </p>
          {result.explanation ? (
            <p className="mt-3 text-sm leading-relaxed text-slate-300">{result.explanation}</p>
          ) : null}
          {showNewsLink ? (
            <a
              href={newsSearchUrl(headline)}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex text-sm font-medium text-amber-300 underline-offset-2 hover:text-amber-200 hover:underline"
            >
              Search this story
            </a>
          ) : null}
        </div>

        {benchmark.isLoading ? (
          <p className="text-sm text-slate-400">Loading this day&apos;s benchmark…</p>
        ) : null}
        {benchmark.isError ? (
          <p className="text-sm text-rose-300">Could not load the historical benchmark.</p>
        ) : null}
        {benchmark.data ? (
          <div className="rounded-xl border border-sky-400/30 bg-sky-400/10 p-3 text-sm text-sky-100">
            <p>{benchmarkLine(benchmark.data)}</p>
            {benchmark.data.solver_count > 0 ? (
              <p className="mt-1 text-sky-200/80">
                Median {formatTime(Math.round(benchmark.data.median_completion_time_seconds ?? 0))}
                {benchmark.data.average_score != null
                  ? ` · Average score ${formatScore(benchmark.data.average_score)}`
                  : ''}
                {' · '}
                {solverLabel(benchmark.data.solver_count)}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </ModalFrame>
  )
}
