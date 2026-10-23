export type CategoryStats = {
  solved: number
  played: number
  available: number
  win_rate: number | null
  average_completion_time_seconds: number | null
}

export type StatsSlice = {
  puzzles_solved: number
  puzzles_played: number
  puzzles_available: number
  completion_percent: number | null
  left_to_play: number
  win_rate: number | null
  average_completion_time_seconds: number | null
  categories: {
    pattern: CategoryStats
    anagram: CategoryStats
    news_quiz: CategoryStats
  }
}

export type UserStats = {
  current_streak: number
  best_streak: number
  daily: StatsSlice
  overall: StatsSlice
}
