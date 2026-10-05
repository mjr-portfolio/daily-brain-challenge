from app.schemas.puzzle import (
    AnagramContent,
    AnagramPuzzleRead,
    NewsQuizContent,
    NewsQuizPuzzleRead,
    PatternContent,
    PatternPuzzleRead,
    PuzzleCreate,
    PuzzleRead,
)
from app.schemas.user import UserCreate, UserRead
from app.schemas.user_completion import CompletionCreate, CompletionRead, SubmitResult

__all__ = [
    "AnagramContent",
    "AnagramPuzzleRead",
    "CompletionCreate",
    "CompletionRead",
    "NewsQuizContent",
    "NewsQuizPuzzleRead",
    "PatternContent",
    "PatternPuzzleRead",
    "PuzzleCreate",
    "PuzzleRead",
    "SubmitResult",
    "UserCreate",
    "UserRead",
]
