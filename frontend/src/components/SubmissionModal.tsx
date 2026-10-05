import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth.ts'
import { useGuestStreak } from '@/hooks/useGuestStreak.ts'
import { formatTime } from '@/utils/time.ts'
import { formatAnswer, type AnswerType, type SubmitResult } from '@/types/submit.ts'

type SubmissionModalProps = {
  open: boolean
  mode: 'daily' | 'archive'
  result: SubmitResult | null
  selectedAnswer: AnswerType | null
  onClose: () => void
}

export function SubmissionModal({
  open,
  mode,
  result,
  selectedAnswer,
  onClose,
}: SubmissionModalProps) {
  const { isAuthenticated, openAuthModal } = useAuth()
  const openedAsGuest = useRef(!isAuthenticated)
  const closedAfterLogin = useRef(false)
  const streak = useGuestStreak()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  useEffect(() => {
    if (!openedAsGuest.current || !isAuthenticated || closedAfterLogin.current) return
    closedAfterLogin.current = true
    onClose()
  }, [isAuthenticated, onClose])

  if (!open || !result) return null

  async function playArchive() {
    await queryClient.invalidateQueries({ queryKey: ['puzzle', 'archive', 'next'] })
    if (mode === 'archive') {
      onClose()
      return
    }
    await navigate('/archive')
  }

  const percentileLabel =
    result.percentile == null
      ? null
      : `Top ${Math.max(1, Math.round(100 - result.percentile))}%`

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-xl">
        <h2 className="text-xl font-semibold text-white">
          {result.is_correct ? 'Correct' : 'Not quite'}
        </h2>
        {selectedAnswer != null ? (
          <p className="mt-2 text-slate-300">Your answer: {formatAnswer(selectedAnswer)}</p>
        ) : null}
        <p className="mt-1 text-slate-300">
          Correct answer: {formatAnswer(result.correct_answer)}
        </p>
        <p className="mt-2 text-slate-300">Time: {formatTime(result.time_taken_seconds)}</p>
        {isAuthenticated ? (
          <div className="mt-3 space-y-2 text-slate-200">
            {result.score != null ? <p>Score: {result.score}</p> : null}
            {percentileLabel ? (
              <p className="text-lg font-medium text-amber-300">{percentileLabel}</p>
            ) : null}
            <button
              type="button"
              onClick={() => void playArchive()}
              className="mt-2 rounded-full bg-amber-400 px-4 py-2 text-sm font-medium text-slate-950"
            >
              {mode === 'archive' ? 'Next puzzle' : 'Play archive'}
            </button>
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            <p className="text-slate-200">Streak: {streak}</p>
            <div className="rounded-xl border border-amber-400/40 bg-amber-400/10 p-3 text-sm text-amber-100">
              Sign up with your email to record your score, view global percentile ranks, and
              catch up on past daily puzzles!
            </div>
            <button
              type="button"
              onClick={openAuthModal}
              className="rounded-full bg-amber-400 px-4 py-2 text-sm font-medium text-slate-950"
            >
              Sign up
            </button>
          </div>
        )}
        <p className="mt-4 text-sm leading-relaxed text-slate-300">{result.explanation}</p>
        <button
          type="button"
          onClick={onClose}
          className="mt-4 text-sm text-slate-400 hover:text-white"
        >
          Close
        </button>
      </div>
    </div>
  )
}
