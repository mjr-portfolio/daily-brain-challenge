from pydantic import BaseModel


class CategoryStats(BaseModel):
    solved: int
    played: int
    available: int = 0
    win_rate: float | None
    average_completion_time_seconds: float | None


class CategoryBreakdown(BaseModel):
    pattern: CategoryStats
    anagram: CategoryStats
    news_quiz: CategoryStats


class StatsSlice(BaseModel):
    puzzles_solved: int
    puzzles_played: int
    puzzles_available: int = 0
    completion_percent: float | None = None
    left_to_play: int = 0
    win_rate: float | None
    average_completion_time_seconds: float | None
    categories: CategoryBreakdown


class UserStatsRead(BaseModel):
    current_streak: int
    best_streak: int
    daily: StatsSlice
    overall: StatsSlice
