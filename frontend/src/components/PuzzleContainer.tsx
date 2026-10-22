import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { ApiError } from '@/api/client.ts'
import { startDaily } from '@/api/puzzles.ts'
import { AnagramBoard } from '@/components/puzzles/AnagramBoard.tsx'
import { NewsQuizBoard } from '@/components/puzzles/NewsQuizBoard.tsx'
import { PatternBoard } from '@/components/PatternBoard.tsx'
import { SubmissionModal } from '@/components/SubmissionModal.tsx'
import { Timer } from '@/components/Timer.tsx'
import type { AccountRead } from '@/api/auth.ts'
import { useAuth } from '@/hooks/useAuth.ts'
import { useDailyPuzzle } from '@/hooks/useDailyPuzzle.ts'
import { useSubmitPuzzle } from '@/hooks/useSubmitPuzzle.ts'
import { useTimer } from '@/hooks/useTimer.ts'
import { useStreak } from '@/hooks/useStreak.ts'
import {
  isAnagramPuzzle,
  isNewsQuizPuzzle,
  isPatternPuzzle,
  type ArchivePuzzleItem,
  type ArchivePuzzleType,
  type DailyPreview,
  type DailySession,
  type Puzzle,
} from '@/types/puzzle.ts'
import type { AnswerType, SubmitResult } from '@/types/submit.ts'
import {
  bumpStreakIfDaily,
  ensureArchiveStarted,
  getDailyStartedAt,
  hasCompletedDailyLocally,
  markDailyPlayedLocally,
  markDailyStarted,
  recordGuestCompletion,
  utcToday,
} from '@/utils/storage.ts'
import { originFromServer } from '@/utils/time.ts'

type PuzzleMode = 'daily' | 'archive'

export function PuzzleContainer({
  mode,
  playback = null,
  onClearPlayback,
  onOpenArchive,
  onLeaveResult,
}: {
  mode: PuzzleMode
  playback?: ArchivePuzzleItem | null
  onClearPlayback?: () => void
  onOpenArchive: () => void
  onLeaveResult: () => void
}) {
  if (mode === 'daily') {
    return <DailyChallenge onOpenArchive={onOpenArchive} onLeaveResult={onLeaveResult} />
  }

  return (
    <ArchiveChallenge
      playback={playback}
      onClearPlayback={onClearPlayback}
      onOpenArchive={onOpenArchive}
      onLeaveResult={onLeaveResult}
    />
  )
}

function ArchiveChallenge({
  playback = null,
  onClearPlayback,
  onOpenArchive,
  onLeaveResult,
}: {
  playback?: ArchivePuzzleItem | null
  onClearPlayback?: () => void
  onOpenArchive: () => void
  onLeaveResult: () => void
}) {
  if (!playback) return null

  return (
    <PuzzleSession
      key={playback.id}
      mode="archive"
      puzzle={playback}
      onExitPlayback={onClearPlayback}
      onOpenArchive={onOpenArchive}
      onLeaveResult={onLeaveResult}
    />
  )
}

function DailyChallenge({
  onOpenArchive,
  onLeaveResult,
}: {
  onOpenArchive: () => void
  onLeaveResult: () => void
}) {
  const { isAuthenticated, email } = useAuth()
  const previewQuery = useDailyPuzzle()
  const [session, setSession] = useState<DailySession | null>(null)
  const [startError, setStartError] = useState<string | null>(null)
  const [heldResult, setHeldResult] = useState<SubmitResult | null>(null)
  const [heldAnswer, setHeldAnswer] = useState<AnswerType | null>(null)
  const [solvedLocally, setSolvedLocally] = useState(false)
  const preview = previewQuery.data
  const done =
    solvedLocally || (preview != null && dailyPreviewDone(preview, isAuthenticated))
  const shouldResume =
    preview != null &&
    !done &&
    (isAuthenticated ? preview.started_at != null : getDailyStartedAt(preview.id) != null)

  useEffect(() => {
    setSession(null)
    setStartError(null)
    setHeldResult(null)
    setHeldAnswer(null)
    setSolvedLocally(false)
  }, [email])

  useEffect(() => {
    if (!shouldResume || session || startError || !preview) return
    let cancelled = false
    void startDaily()
      .then((next) => {
        if (!cancelled) setSession(next)
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setStartError(error instanceof Error ? error.message : 'Could not start the puzzle.')
        }
      })
    return () => {
      cancelled = true
    }
  }, [shouldResume, session, startError, preview])

  const startedAtMs = useMemo(() => {
    if (!session) return 0
    if (session.started_at) return originFromServer(session.started_at, session.server_now)
    return getDailyStartedAt(session.puzzle.id) ?? Date.now()
  }, [session])

  async function begin() {
    if (!preview) return
    setStartError(null)
    if (!isAuthenticated) markDailyStarted(preview.id)
    try {
      setSession(await startDaily())
    } catch (error) {
      setStartError(error instanceof Error ? error.message : 'Could not start the puzzle.')
    }
  }

  function holdResult(result: SubmitResult, answer: AnswerType) {
    setHeldResult(result)
    setHeldAnswer(answer)
    setSolvedLocally(true)
  }

  let board: ReactNode
  if (previewQuery.isLoading) {
    board = <StatusCard title="Loading puzzle…" />
  } else if (previewQuery.isError) {
    board = (
      <StatusCard title="Could not load the puzzle.">
        <button
          type="button"
          onClick={() => void previewQuery.refetch()}
          className="mt-3 rounded-full bg-slate-800 px-4 py-2 text-sm"
        >
          Retry
        </button>
      </StatusCard>
    )
  } else if (!preview) {
    board = <StatusCard title="No puzzle available." />
  } else if (done) {
    board = <CompletedDailyCard onOpenArchive={onOpenArchive} />
  } else if (startError) {
    board = (
      <StatusCard title={startError}>
        <button
          type="button"
          onClick={() => void begin()}
          className="mt-3 rounded-full bg-slate-800 px-4 py-2 text-sm"
        >
          Retry
        </button>
      </StatusCard>
    )
  } else if (!session) {
    board = shouldResume ? (
      <StatusCard title="Loading puzzle…" />
    ) : (
      <DailyReadyBoard preview={preview} onStart={() => void begin()} />
    )
  } else {
    board = (
      <PuzzleSession
        key={session.puzzle.id}
        mode="daily"
        puzzle={session.puzzle}
        startedAtMs={startedAtMs}
        onOpenArchive={onOpenArchive}
        onLeaveResult={onLeaveResult}
        onDailySolved={holdResult}
      />
    )
  }

  return (
    <>
      {board}
      <SubmissionModal
        open={heldResult != null}
        result={heldResult}
        selectedAnswer={heldAnswer}
        onClose={() => {
          if (heldResult == null) return
          setHeldResult(null)
          onLeaveResult()
        }}
        onOpenArchive={() => {
          if (heldResult == null) return
          setHeldResult(null)
          onLeaveResult()
          onOpenArchive()
        }}
        timingNote="Timed from when you started."
      />
    </>
  )
}

function PuzzleSession({
  mode,
  puzzle,
  startedAtMs,
  onExitPlayback,
  onOpenArchive,
  onLeaveResult,
  onDailySolved,
}: {
  mode: PuzzleMode
  puzzle: Puzzle
  startedAtMs?: number
  onExitPlayback?: () => void
  onOpenArchive: () => void
  onLeaveResult: () => void
  onDailySolved?: (result: SubmitResult, answer: AnswerType) => void
}) {
  const { isAuthenticated, email } = useAuth()
  const queryClient = useQueryClient()
  const submit = useSubmitPuzzle()
  const [result, setResult] = useState<SubmitResult | null>(null)
  const [selectedAnswer, setSelectedAnswer] = useState<AnswerType | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [showCompleted, setShowCompleted] = useState(false)
  const [origin] = useState(() =>
    mode === 'archive' ? ensureArchiveStarted(puzzle.id) : (startedAtMs ?? Date.now()),
  )
  const timer = useTimer(result == null && !showCompleted, origin)

  async function handleSubmit(answer: AnswerType) {
    const seconds = timer.stop()
    setSelectedAnswer(answer)
    setSubmitError(null)
    try {
      const response = await submit.mutateAsync({
        id: puzzle.id,
        payload: { answer, time_taken_seconds: seconds },
      })
      if (!isAuthenticated) {
        recordGuestCompletion({
          puzzleId: puzzle.id,
          assignedDate: puzzle.assigned_date,
          timeTakenSeconds: seconds,
          answer,
          isCorrect: response.is_correct,
        })
        if (puzzle.assigned_date === utcToday()) {
          bumpStreakIfDaily(puzzle.id, puzzle.assigned_date)
        }
      }
      rememberDailyPlay(puzzle.assigned_date)
      setResult(response)
      if (response.streak != null && email) {
        queryClient.setQueryData<AccountRead>(['streak', email], (current) => ({
          email,
          streak: response.streak ?? 0,
          total_score: (current?.total_score ?? 0) + (response.score ?? 0),
        }))
        void queryClient.invalidateQueries({ queryKey: ['streak', email] })
      }
      if (onDailySolved) onDailySolved(response, answer)
      else setModalOpen(true)
      await queryClient.invalidateQueries({ queryKey: ['puzzle', 'daily'] })
      await queryClient.invalidateQueries({ queryKey: ['puzzle', 'archive', 'list'] })
    } catch (error) {
      if (
        mode === 'daily' &&
        error instanceof ApiError &&
        error.status === 409 &&
        puzzle.assigned_date
      ) {
        rememberDailyPlay(puzzle.assigned_date)
        setShowCompleted(true)
        return
      }
      setSubmitError(error instanceof Error ? error.message : 'Submission failed')
    }
  }

  if (showCompleted) return <CompletedDailyCard onOpenArchive={onOpenArchive} />

  const phase = submitError ? 'error' : result ? 'submitted' : 'active'

  return (
    <section className="mx-auto mt-8 w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              mode === 'daily'
                ? 'bg-amber-400/15 text-amber-200'
                : 'bg-sky-400/15 text-sky-200'
            }`}
          >
            {mode === 'daily' ? 'Official Daily Challenge' : archiveLabel(puzzle)}
          </span>
          {onExitPlayback ? (
            <button
              type="button"
              onClick={onExitPlayback}
              className="text-xs text-slate-400 hover:text-white"
            >
              Back to today
            </button>
          ) : null}
        </div>
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
      {onDailySolved ? null : (
        <SubmissionModal
          open={modalOpen && phase === 'submitted'}
          result={result}
          selectedAnswer={selectedAnswer}
          onClose={onLeaveResult}
          onOpenArchive={() => {
            onLeaveResult()
            onOpenArchive()
          }}
        />
      )}
    </section>
  )
}

function rememberDailyPlay(assignedDate: string | null): void {
  if (assignedDate === utcToday()) markDailyPlayedLocally(assignedDate)
}

function dailyPreviewDone(preview: DailyPreview, isAuthenticated: boolean): boolean {
  if (isAuthenticated) return preview.is_completed
  return hasCompletedDailyLocally(preview.assigned_date)
}

const DAILY_INTRO: Record<ArchivePuzzleType, { label: string; text: string }> = {
  pattern: {
    label: 'Pattern',
    text: 'A grid with one missing cell. Find the rule, then pick the piece that completes it.',
  },
  anagram: {
    label: 'Anagram',
    text: 'A scrambled word and a hint. Unscramble the letters.',
  },
  news_quiz: {
    label: 'News',
    text: 'A question about recent events. Choose the right answer.',
  },
}

function DailyReadyBoard({ preview, onStart }: { preview: DailyPreview; onStart: () => void }) {
  const streak = useStreak()
  const intro = DAILY_INTRO[preview.puzzle_type] ?? {
    label: 'Daily',
    text: 'Start when you are ready. The clock runs from then.',
  }

  return (
    <section className="mx-auto mt-8 w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 text-center">
      <p className="text-sm text-slate-400">{formatAssignedDate(preview.assigned_date)}</p>
      <h1 className="mt-2 text-xl font-semibold text-white">Today&apos;s puzzle</h1>
      <p className="mt-3 text-sm font-medium text-amber-200">{intro.label}</p>
      <p className="mt-2 text-sm text-slate-300">{intro.text}</p>
      <p className="mt-4 text-sm text-amber-300">Streak: {streak}</p>
      <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          disabled
          title="Coming soon"
          className="cursor-default rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-400"
        >
          Leaderboard
        </button>
        <button
          type="button"
          onClick={onStart}
          className="rounded-full border border-amber-500 bg-amber-400 px-4 py-2 text-sm font-medium text-slate-950 hover:border-slate-950"
        >
          Start today&apos;s puzzle
        </button>
      </div>
      <p className="mt-3 text-xs text-slate-500">Leaderboard coming soon</p>
    </section>
  )
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

function archiveLabel(puzzle: Puzzle): string {
  return puzzle.assigned_date ? `Archive · ${puzzle.assigned_date}` : 'Archive Catch-Up'
}

function PuzzleBody({
  puzzle,
  disabled,
  onSubmit,
}: {
  puzzle: Puzzle
  disabled: boolean
  onSubmit: (answer: AnswerType) => void
}) {
  if (isPatternPuzzle(puzzle)) {
    return <PatternBoard content={puzzle.content} disabled={disabled} onSubmit={onSubmit} />
  }
  if (isAnagramPuzzle(puzzle)) {
    return <AnagramBoard content={puzzle.content} disabled={disabled} onSubmit={onSubmit} />
  }
  if (isNewsQuizPuzzle(puzzle)) {
    return <NewsQuizBoard content={puzzle.content} disabled={disabled} onSubmit={onSubmit} />
  }
  return <p className="text-center text-slate-300">This puzzle type is not available yet.</p>
}

function CompletedDailyCard({ onOpenArchive }: { onOpenArchive: () => void }) {
  const { isAuthenticated, openAuthModal } = useAuth()

  return (
    <section className="mx-auto mt-8 w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 text-center">
      <h1 className="text-xl font-semibold text-white">Daily Challenge Completed</h1>
      <p className="mt-2 text-sm text-slate-300">You already finished today's puzzle.</p>
      {isAuthenticated ? (
        <button
          type="button"
          onClick={onOpenArchive}
          className="mt-5 rounded-full border border-amber-500 bg-amber-400 px-4 py-2 text-sm font-medium text-slate-950 hover:border-slate-950"
        >
          Archive
        </button>
      ) : (
        <button
          type="button"
          onClick={openAuthModal}
          className="mt-5 rounded-full border border-amber-500 bg-amber-400 px-4 py-2 text-sm font-medium text-slate-950 hover:border-slate-950"
        >
          Sign Up to Access Archive & Save Streaks
        </button>
      )}
    </section>
  )
}

function StatusCard({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <section className="mx-auto mt-8 w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 text-center">
      <p>{title}</p>
      {children}
    </section>
  )
}
