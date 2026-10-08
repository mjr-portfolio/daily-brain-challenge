"""Gemini-backed structured puzzle generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.models.puzzle import PuzzleType
from app.schemas.puzzle import AnagramContent, NewsQuizContent, PatternContent
from app.services.hashing import hash_solution


class GeneratedPattern(BaseModel):
    grid: list[list[int | str | None]]
    prompt: str
    choices: list[int | str]
    solution: int | str
    explanation: str


class GeneratedAnagram(BaseModel):
    scrambled_word: str
    hint: str | None = None
    prompt: str | None = "Unscramble the letters to reveal the target word"
    solution: str
    explanation: str


class GeneratedNewsQuiz(BaseModel):
    question: str
    options: list[str] = Field(min_length=2)
    source_headline: str | None = None
    hint: str | None = None
    solution: str
    explanation: str


@dataclass(frozen=True)
class GeneratedPuzzle:
    puzzle_type: PuzzleType
    content: dict[str, Any]
    solution: object
    explanation: str
    solution_hash: str


class GenerationError(RuntimeError):
    """Raised when Gemini generation or validation fails."""


def _require_api_key() -> str:
    key = get_settings().GEMINI_API_KEY
    if not key:
        raise GenerationError("GEMINI_API_KEY is not configured")
    return key


def _generate_structured[T: BaseModel](prompt: str, schema: type[T]) -> T:
    """Create a fresh Client per call (safe for asyncio.to_thread workers)."""
    settings = get_settings()
    # Never reuse a module-level/shared Client across threads — each worker owns
    # its own HTTP session for the duration of this call.
    with genai.Client(api_key=_require_api_key()) as client:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise GenerationError(f"Empty Gemini response for {schema.__name__}")
        try:
            return schema.model_validate_json(text)
        except Exception as exc:
            raise GenerationError(
                f"Invalid Gemini payload for {schema.__name__}: {exc}"
            ) from exc


def generate_pattern_puzzle() -> GeneratedPuzzle:
    raw = _generate_structured(
        (
            "Create one original pattern-recognition puzzle suitable for a daily brain-training app. "
            "Use a 3x3 grid of numbers or short letters with exactly one null blank cell. "
            "Provide 3 multiple-choice options including the correct answer. "
            "solution must equal the blank cell value and appear in choices. "
            "Keep the prompt concise and the explanation clear."
        ),
        GeneratedPattern,
    )
    content = PatternContent(
        grid=raw.grid,
        prompt=raw.prompt,
        choices=raw.choices,
    ).model_dump()
    return GeneratedPuzzle(
        puzzle_type=PuzzleType.PATTERN,
        content=content,
        solution=raw.solution,
        explanation=raw.explanation,
        solution_hash=hash_solution(raw.solution),
    )


def generate_anagram_puzzle() -> GeneratedPuzzle:
    raw = _generate_structured(
        (
            "Create one original anagram puzzle for a daily brain-training app. "
            "scrambled_word must be a scrambled form of solution with the same letters. "
            "Provide a short helpful hint and a clear explanation. "
            "solution must be a single English word."
        ),
        GeneratedAnagram,
    )
    content = AnagramContent(
        scrambled_word=raw.scrambled_word,
        hint=raw.hint,
        prompt=raw.prompt,
    ).model_dump()
    return GeneratedPuzzle(
        puzzle_type=PuzzleType.ANAGRAM,
        content=content,
        solution=raw.solution,
        explanation=raw.explanation,
        solution_hash=hash_solution(raw.solution),
    )


def generate_news_quiz_puzzle() -> GeneratedPuzzle:
    raw = _generate_structured(
        (
            "Create one original multiple-choice news quiz for a daily brain-training app. "
            "Use a plausible recent-tech or science context headline. "
            "Provide exactly 4 distinct options. solution must be one of the options. "
            "Keep the question factual-sounding and include a short explanation."
        ),
        GeneratedNewsQuiz,
    )
    if raw.solution not in raw.options:
        raise GenerationError("News quiz solution must be one of the options")
    content = NewsQuizContent(
        question=raw.question,
        options=raw.options,
        source_headline=raw.source_headline,
        hint=raw.hint,
    ).model_dump()
    return GeneratedPuzzle(
        puzzle_type=PuzzleType.NEWS_QUIZ,
        content=content,
        solution=raw.solution,
        explanation=raw.explanation,
        solution_hash=hash_solution(raw.solution),
    )


def generate_puzzle(puzzle_type: PuzzleType) -> GeneratedPuzzle:
    if puzzle_type == PuzzleType.PATTERN:
        return generate_pattern_puzzle()
    if puzzle_type == PuzzleType.ANAGRAM:
        return generate_anagram_puzzle()
    if puzzle_type == PuzzleType.NEWS_QUIZ:
        return generate_news_quiz_puzzle()
    raise GenerationError(f"Unsupported puzzle type: {puzzle_type}")
