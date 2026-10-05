import { useState, type ReactNode } from 'react'
import { ApiError } from '@/api/client.ts'
import { PatternBoard } from '@/components/PatternBoard.tsx'
import { SubmissionModal } from '@/components/SubmissionModal.tsx'
import { Timer } from '@/components/Timer.tsx'
import { useArchivePuzzle } from '@/hooks/useArchivePuzzle.ts'
import { useAuth } from '@/hooks/useAuth.ts'
import { useDailyPuzzle } from '@/hooks/useDailyPuzzle.ts'
import { useSubmitPuzzle } from '@/hooks/useSubmitPuzzle.ts'
import { useTimer } from '@/hooks/useTimer.ts'
import { isPatternPuzzle, type Puzzle } from '@/types/puzzle.ts'
import type { SubmitResult } from '@/types/submit.ts'
import { bumpStreakIfDaily, recordGuestCompletion } from '@/utils/storage.ts'

type PuzzleMode = 'daily' | 'archive'

export function PuzzleContainer({ mode }: { mode: PuzzleMode }) {
  const daily = useDailyPuzzle()
  const archive = useArchivePuzzle()
  const query = mode === 'daily' ? daily : archive

  if (query.isLoading) {
    return <StatusCard title="Loading puzzle…" />
  }

  if (query.isError) {
    if (
      mode === 'archive' &&
      query.error instanceof ApiError &&
      query.error.status === 404
    ) {
      return <StatusCard title="No uncompleted archive puzzles left." />
    }
    return (
      <StatusCard title="Could not load the puzzle.">
        <button
          type="button"
          onClick={() => void query.refetch()}
          className="mt-3 rounded-full bg-slate-800 px-4 py-2 text-sm"
        >
          Retry
        </button>
      </StatusCard>
    )
  }

  if (!query.data) return <StatusCard title="No puzzle available." />

  return <PuzzleSession key={query.data.id} mode={mode} puzzle={query.data} />
}

function PuzzleSession({ mode, puzzle }: { mode: PuzzleMode; puzzle: Puzzle }) {
  const { isAuthenticated } = useAuth()
  const submit = useSubmitPuzzle()
  const [result, setResult] = useState<SubmitResult | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const timer = useTimer(result == null)

  async function handleSubmit(answer: string | number) {
    const seconds = timer.stop()
    setSubmitError(null)
    try {
      const response = await submit.mutateAsync({
        id: puzzle.id,
        payload: { answer, time_taken_seconds: seconds },
      })
      if (!isAuthenticated && mode === 'daily') {
        recordGuestCompletion({
          puzzleId: puzzle.id,
          assignedDate: puzzle.assigned_date,
          timeTakenSeconds: seconds,
          answer,
          isCorrect: response.is_correct,
        })
        bumpStreakIfDaily(puzzle.id, puzzle.assigned_date, response.is_correct)
      }
      setResult(response)
      setModalOpen(true)
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Submission failed')
    }
  }

  const phase = submitError ? 'error' : result ? 'submitted' : 'active'

  return (
    <section className="mx-auto mt-8 w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <span
          className={`rounded-full px-3 py-1 text-xs font-medium ${
            mode === 'daily'
              ? 'bg-amber-400/15 text-amber-200'
              : 'bg-sky-400/15 text-sky-200'
          }`}
        >
          {mode === 'daily' ? 'Official Daily Challenge' : 'Archive Catch-Up'}
        </span>
        <Timer seconds={timer.seconds} />
      </div>
      {phase === 'error' ? (
        <div className="mb-4 rounded-lg border border-rose-400/40 bg-rose-400/10 p-3 text-sm text-rose-100">
          <p>{submitError}</p>
          <button
            type="button"
            onClick={() => setSubmitError(null)}
            className="mt-2 underline"
          >
            Try again
          </button>
        </div>
      ) : null}
      <PuzzleBody puzzle={puzzle} disabled={phase !== 'active'} onSubmit={handleSubmit} />
      <SubmissionModal
        open={modalOpen && phase === 'submitted'}
        mode={mode}
        result={result}
        onClose={() => setModalOpen(false)}
      />
    </section>
  )
}

function PuzzleBody({
  puzzle,
  disabled,
  onSubmit,
}: {
  puzzle: Puzzle
  disabled: boolean
  onSubmit: (answer: string | number) => void
}) {
  if (!isPatternPuzzle(puzzle)) {
    return <p className="text-center text-slate-300">This puzzle type is not available yet.</p>
  }
  return <PatternBoard content={puzzle.content} disabled={disabled} onSubmit={onSubmit} />
}

function StatusCard({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <section className="mx-auto mt-8 w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 text-center">
      <p>{title}</p>
      {children}
    </section>
  )
}
