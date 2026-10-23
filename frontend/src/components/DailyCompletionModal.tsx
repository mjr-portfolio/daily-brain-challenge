import { useEffect, useRef, useState } from 'react'
import { LeaderboardPanel } from '@/components/LeaderboardPanel.tsx'
import { ModalFrame } from '@/components/ModalFrame.tsx'
import { useAuth } from '@/hooks/useAuth.ts'
import { useGuestStreak } from '@/hooks/useGuestStreak.ts'
import type { ArchivePuzzleType } from '@/types/puzzle.ts'
import { formatAnswer, type AnswerType, type SubmitResult } from '@/types/submit.ts'
import { formatTime } from '@/utils/time.ts'

const CATEGORY_LABEL: Record<ArchivePuzzleType, string> = {
  pattern: 'Pattern',
  anagram: 'Anagram',
  news_quiz: 'News',
}

function formatAssignedDate(value: string | null): string {
  if (!value) return 'Daily Challenge'
  const [year, month, day] = value.split('-').map(Number)
  if (!year || !month || !day) return value
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

function shareText(
  result: SubmitResult,
  puzzleType: string,
  assignedDate: string | null,
): string {
  const label = CATEGORY_LABEL[puzzleType as ArchivePuzzleType] ?? 'Daily'
  const mark = result.is_correct ? '🟩' : '🟥'
  const lines = [
    `Daily Challenge · ${formatAssignedDate(assignedDate)}`,
    `${label} ${mark}`,
    `${result.time_taken_seconds}s${result.score != null ? ` · ${result.score} pts` : ''}`,
  ]
  if (result.streak != null) lines.push(`Streak ${result.streak}`)
  return lines.join('\n')
}

type DailyCompletionModalProps = {
  open: boolean
  result: SubmitResult | null
  selectedAnswer: AnswerType | null
  puzzleType: string
  assignedDate: string | null
  onClose: () => void
  timingNote?: string | null
}

export function DailyCompletionModal({
  open,
  result,
  selectedAnswer,
  puzzleType,
  assignedDate,
  onClose,
  timingNote = null,
}: DailyCompletionModalProps) {
  const { isAuthenticated, openAuthModal } = useAuth()
  const openedAsGuest = useRef(!isAuthenticated)
  const closedAfterLogin = useRef(false)
  const guestStreak = useGuestStreak()
  const [showBoard, setShowBoard] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!openedAsGuest.current || !isAuthenticated || closedAfterLogin.current) return
    closedAfterLogin.current = true
    onClose()
  }, [isAuthenticated, onClose])

  useEffect(() => {
    if (!open) {
      setShowBoard(false)
      setCopied(false)
    }
  }, [open])

  if (!open || !result) return null

  const percentileLabel =
    result.percentile == null
      ? null
      : `Top ${Math.max(1, Math.round(100 - result.percentile))}%`
  const card = shareText(result, puzzleType, assignedDate)

  async function copyCard() {
    try {
      await navigator.clipboard.writeText(card)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  let title = 'Not quite'
  if (showBoard) title = "Today's leaderboard"
  else if (result.is_correct) title = 'Correct'

  return (
    <ModalFrame title={title} onClose={onClose} wide>
      {showBoard ? (
        <>
          <LeaderboardPanel />
          <button
            type="button"
            onClick={() => setShowBoard(false)}
            className="mt-4 text-sm text-slate-400 hover:text-white"
          >
            Back to result
          </button>
        </>
      ) : (
        <>
            {selectedAnswer != null ? (
              <p className="mt-2 text-slate-300">Your answer: {formatAnswer(selectedAnswer)}</p>
            ) : null}
            <p className="mt-1 text-slate-300">
              Correct answer: {formatAnswer(result.correct_answer)}
            </p>
            <p className="mt-2 text-slate-300">Time: {formatTime(result.time_taken_seconds)}</p>
            {timingNote ? <p className="mt-1 text-sm text-slate-400">{timingNote}</p> : null}
            {isAuthenticated ? (
              <div className="mt-3 space-y-2 text-slate-200">
                {result.score != null ? <p>Score: {result.score}</p> : null}
                {result.streak != null ? (
                  <p className="text-amber-300">Streak: {result.streak}</p>
                ) : null}
                {percentileLabel ? (
                  <p className="text-lg font-medium text-amber-300">{percentileLabel}</p>
                ) : null}
                <pre className="mt-3 whitespace-pre-wrap rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100">
                  {card}
                </pre>
                <button
                  type="button"
                  onClick={() => void copyCard()}
                  className="rounded-full border border-slate-600 px-4 py-2 text-sm text-slate-100 hover:border-amber-400"
                >
                  {copied ? 'Copied' : 'Copy result'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowBoard(true)}
                  className="ml-2 rounded-full border border-amber-500 bg-amber-400 px-4 py-2 text-sm font-medium text-slate-950 hover:border-slate-950"
                >
                  Today&apos;s leaderboard
                </button>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                <p className="text-slate-200">Streak: {guestStreak}</p>
                <div className="rounded-xl border border-amber-400/40 bg-amber-400/10 p-3 text-sm text-amber-100">
                  Sign up with your email to record your score, view global percentile ranks, and
                  catch up on past daily puzzles!
                </div>
                <button
                  type="button"
                  onClick={openAuthModal}
                  className="rounded-full border border-amber-500 bg-amber-400 px-4 py-2 text-sm font-medium text-slate-950 hover:border-slate-950"
                >
                  Sign up
                </button>
              </div>
            )}
            <p className="mt-4 text-sm leading-relaxed text-slate-300">{result.explanation}</p>
          </>
        )}
    </ModalFrame>
  )
}
