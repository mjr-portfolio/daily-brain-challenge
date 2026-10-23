from datetime import date
from uuid import UUID

from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    display_name: str
    score: int
    completion_time_seconds: int
    is_viewer: bool


class LeaderboardRead(BaseModel):
    puzzle_id: UUID
    assigned_date: date
    limit: int
    entries: list[LeaderboardEntry]
    viewer: LeaderboardEntry | None


class BenchmarkViewer(BaseModel):
    time_taken_seconds: int
    score: int
    is_correct: bool
    faster_than_percent: float | None


class ArchiveBenchmark(BaseModel):
    puzzle_id: UUID
    assigned_date: date
    solver_count: int
    fastest_completion_time_seconds: int | None
    median_completion_time_seconds: float | None
    average_score: float | None
    viewer: BenchmarkViewer | None
