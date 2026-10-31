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

function newsSearchUrl(headline: string): string {
  return `https://www.google.com/search?q=${encodeURIComponent(headline)}`
}

type DailyCompletionModalProps = {
  open: boolean
  result: SubmitResult | null
  selectedAnswer: AnswerType | null
  puzzleType: string
  assignedDate: string | null
  sourceHeadline?: string | null
  onClose: () => void
  timingNote?: string | null
}

export function DailyCompletionModal({
  open,
  result,
  selectedAnswer,
  puzzleType,
  assignedDate,
  sourceHeadline = null,
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
  const headline = sourceHeadline?.trim() ? sourceHeadline.trim() : null
  const showNewsLink = puzzleType === 'news_quiz' && headline != null

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
  else if (result.is_correct) title = 'Correct!'

  return (
    <ModalFrame
      title={title}
      subtitle={formatAssignedDate(assignedDate)}
      onClose={onClose}
      wide
      celebrate={result.is_correct && !showBoard}
    >
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
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <StatChip label="Time" value={formatTime(result.time_taken_seconds)} />
            {result.score != null ? (
              <StatChip label="Score" value={`${result.score}`} accent />
            ) : null}
            {isAuthenticated && result.streak != null ? (
              <StatChip label="Streak" value={`${result.streak}`} accent />
            ) : null}
            {!isAuthenticated ? (
              <StatChip label="Streak" value={`${guestStreak}`} accent />
            ) : null}
            {percentileLabel ? (
              <StatChip label="Rank" value={percentileLabel} accent />
            ) : null}
          </div>

          {timingNote ? <p className="text-xs text-slate-500">{timingNote}</p> : null}

          <div className="rounded-xl border border-slate-700 bg-slate-950/70 px-4 py-3">
            {selectedAnswer != null ? (
              <p className="text-sm text-slate-400">
                Your answer:{' '}
                <span className="font-medium text-slate-100">
                  {formatAnswer(selectedAnswer)}
                </span>
              </p>
            ) : null}
            <p className="mt-1 text-sm text-slate-400">
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

          {isAuthenticated ? (
            <div className="space-y-3">
              <pre className="whitespace-pre-wrap rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100">
                {card}
              </pre>
              <div className="flex flex-wrap gap-2">
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
                  className="rounded-full border border-amber-500 bg-amber-400 px-4 py-2 text-sm font-medium text-slate-950 hover:border-slate-950"
                >
                  Today&apos;s leaderboard
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
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
        </div>
      )}
    </ModalFrame>
  )
}

function StatChip({
  label,
  value,
  accent = false,
}: {
  label: string
  value: string
  accent?: boolean
}) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-950/60 px-3 py-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-0.5 text-sm font-semibold ${accent ? 'text-amber-300' : 'text-white'}`}>
        {value}
      </p>
    </div>
  )
}
