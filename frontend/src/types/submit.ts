export type SubmitPayload = {
  answer: string | number
  time_taken_seconds: number
}

export type SubmitResult = {
  is_correct: boolean
  time_taken_seconds: number
  percentile: number | null
  score: number | null
  is_daily_official: boolean | null
}
