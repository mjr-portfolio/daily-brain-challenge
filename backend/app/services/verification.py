from datetime import date

from app.models.puzzle import Puzzle
from app.services.hashing import hash_solution


def verify_answer(puzzle: Puzzle, answer: object) -> bool:
    return hash_solution(answer) == puzzle.solution_hash


def compute_score(is_correct: bool) -> int:
    return 100 if is_correct else 0


def is_daily_official(puzzle: Puzzle, today_utc: date) -> bool:
    return puzzle.assigned_date == today_utc
