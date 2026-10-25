from app.schemas.auth import TokenResponse
from app.schemas.puzzle import (
    AnagramContent,
    AnagramPuzzleRead,
    NewsQuizContent,
    NewsQuizPuzzleRead,
    PatternContent,
    PatternPuzzleRead,
    PuzzleRead,
    ShapeItem,
)
from app.schemas.user_completion import CompletionCreate, SubmitResult

__all__ = [
    "AnagramContent",
    "AnagramPuzzleRead",
    "CompletionCreate",
    "NewsQuizContent",
    "NewsQuizPuzzleRead",
    "PatternContent",
    "PatternPuzzleRead",
    "PuzzleRead",
    "ShapeItem",
    "SubmitResult",
    "TokenResponse",
]
