import type { ShapeItem } from '@/types/puzzle.ts'

export type AnswerType = string | number | Array<string | number> | ShapeItem

export type SubmitPayload = {
  answer: AnswerType
  time_taken_seconds: number
}

export type SubmitResult = {
  is_correct: boolean
  time_taken_seconds: number
  correct_answer: AnswerType
  explanation: string
  percentile: number | null
  score: number | null
  is_daily_official: boolean | null
  streak: number | null
}

export function formatAnswer(answer: AnswerType): string {
  if (Array.isArray(answer)) return answer.map((item) => String(item)).join(', ')
  if (typeof answer === 'object') {
    const count = answer.count ?? 1
    const rotation = answer.rotation ?? 0
    const noun = count === 1 ? answer.shape : `${answer.shape}s`
    const turn = rotation ? `, ${rotation}°` : ''
    return `${count} ${answer.color} ${noun}${turn}`
  }
  return String(answer)
}
