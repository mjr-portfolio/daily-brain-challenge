export type LeaderboardLimit = 10 | 25 | 50 | 100

export type LeaderboardEntry = {
  rank: number
  display_name: string
  score: number
  completion_time_seconds: number
  is_viewer: boolean
}

export type DailyLeaderboard = {
  puzzle_id: string
  assigned_date: string
  limit: LeaderboardLimit
  entries: LeaderboardEntry[]
  viewer: LeaderboardEntry | null
}

export type ArchiveBenchmark = {
  puzzle_id: string
  assigned_date: string
  solver_count: number
  fastest_completion_time_seconds: number | null
  median_completion_time_seconds: number | null
  average_score: number | null
  viewer: {
    time_taken_seconds: number
    score: number
    is_correct: boolean
    faster_than_percent: number | null
  } | null
}
