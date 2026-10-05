export type AnswerType = string | number | Array<string | number>

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
}

export function formatAnswer(answer: AnswerType): string {
  if (Array.isArray(answer)) return answer.map((item) => String(item)).join(', ')
  return String(answer)
}
