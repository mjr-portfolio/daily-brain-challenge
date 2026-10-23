import { useQuery } from '@tanstack/react-query'
import { getArchiveBenchmark } from '@/api/puzzles.ts'
import { ModalFrame } from '@/components/ModalFrame.tsx'
import type { ArchiveBenchmark } from '@/types/leaderboard.ts'
import type { SubmitResult } from '@/types/submit.ts'
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

export function ArchiveCompletionModal({
  open,
  result,
  puzzleId,
  onClose,
}: {
  open: boolean
  result: SubmitResult | null
  puzzleId: string
  onClose: () => void
}) {
  const benchmark = useQuery({
    queryKey: ['benchmark', puzzleId],
    queryFn: () => getArchiveBenchmark(puzzleId),
    enabled: open,
  })

  if (!open || !result) return null

  return (
    <ModalFrame title={result.is_correct ? 'Correct' : 'Not quite'} onClose={onClose}>
      <p className="text-slate-300">Time: {formatTime(result.time_taken_seconds)}</p>
      {result.score != null ? <p className="mt-1 text-slate-300">Score: {result.score}</p> : null}
      {benchmark.isLoading ? (
        <p className="mt-3 text-sm text-slate-400">Loading this day's benchmark…</p>
      ) : null}
      {benchmark.isError ? (
        <p className="mt-3 text-sm text-rose-300">Could not load the historical benchmark.</p>
      ) : null}
      {benchmark.data ? (
        <div className="mt-3 rounded-xl border border-sky-400/30 bg-sky-400/10 p-3 text-sm text-sky-100">
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
      <p className="mt-4 text-sm leading-relaxed text-slate-300">{result.explanation}</p>
    </ModalFrame>
  )
}
