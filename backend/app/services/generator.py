"""Gemini-backed structured puzzle generation."""

from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path

import httpx
from google.genai.errors import APIError, ServerError
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.models.puzzle import PuzzleType
from app.schemas.puzzle import (
    AnagramContent,
    NewsQuizContent,
    PatternContent,
    ShapeItem,
    coerce_pattern_cell,
)
from app.services.hashing import hash_solution

PatternKind = Literal["numerical", "unicode", "shape"]


class GeneratedPattern(BaseModel):
    grid: list[list[int | str | ShapeItem | None]]
    prompt: str
    choices: list[int | str | ShapeItem]
    solution: int | str | ShapeItem
    explanation: str


ShapeRow = Annotated[list[ShapeItem | None], Field(min_length=4, max_length=4)]


class GeneratedShape(BaseModel):
    grid: list[ShapeRow] = Field(min_length=4, max_length=4)
    prompt: str
    choices: list[ShapeItem] = Field(min_length=4, max_length=4)
    solution: ShapeItem
    explanation: str


class GeneratedAnagram(BaseModel):
    scrambled_word: str
    hint: str | None = None
    prompt: str | None = "Unscramble the letters to reveal the target word"
    solution: str
    explanation: str


class GeneratedNewsQuiz(BaseModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
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


class PermanentGeminiError(GenerationError):
    """API key, permission, or rejected-request errors. Do not retry these."""


class TransientGeminiError(Exception):
    """Rate limit, timeout, or Gemini outage. `delay` is the wait before a retry."""

    def __init__(self, delay: float, message: str):
        self.delay = delay
        super().__init__(message)


_SERVICE_DELAY = 13.0
_TRANSIENT_CLIENT_CODES = {408, 429}


def _require_api_key() -> str:
    key = get_settings().GEMINI_API_KEY
    if not key:
        raise GenerationError("GEMINI_API_KEY is not configured")
    return key


def _generate_structured[T: BaseModel](
    prompt: str,
    schema: type[T],
    *,
    system_instruction: str,
    model: str,
) -> T:
    """Create a fresh Client per call (safe for asyncio.to_thread workers)."""
    # Never reuse a module-level/shared Client across threads — each worker owns
    # its own HTTP session for the duration of this call.
    with genai.Client(api_key=_require_api_key()) as client:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
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


def _retry_delay(exc: APIError) -> float:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        return _SERVICE_DELAY
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw is None:
        return _SERVICE_DELAY
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return _SERVICE_DELAY


def _classify_api_error(exc: APIError) -> None:
    if isinstance(exc, ServerError) or exc.code in _TRANSIENT_CLIENT_CODES:
        raise TransientGeminiError(_retry_delay(exc), str(exc)) from exc
    raise PermanentGeminiError(f"Gemini request rejected: {exc}") from exc


def _generate_once[T: BaseModel](
    prompt: str,
    schema: type[T],
    *,
    system_instruction: str,
    model: str,
    check: Callable[[T], None],
) -> T:
    try:
        raw = _generate_structured(
            prompt,
            schema,
            system_instruction=system_instruction,
            model=model,
        )
    except APIError as exc:
        _classify_api_error(exc)
        raise
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise TransientGeminiError(_SERVICE_DELAY, str(exc)) from exc
    check(raw)
    return raw


def _attempt_model[T: BaseModel](
    prompt: str,
    schema: type[T],
    *,
    system_instruction: str,
    model: str,
    check: Callable[[T], None],
) -> T:
    """Two immediate tries for a bad puzzle. A service error waits, then tries once more."""
    error: GenerationError | None = None
    for _ in range(2):
        try:
            return _generate_once(
                prompt,
                schema,
                system_instruction=system_instruction,
                model=model,
                check=check,
            )
        except TransientGeminiError as exc:
            time.sleep(exc.delay)
            try:
                return _generate_once(
                    prompt,
                    schema,
                    system_instruction=system_instruction,
                    model=model,
                    check=check,
                )
            except PermanentGeminiError:
                raise
            except GenerationError as inner:
                error = inner
        except PermanentGeminiError:
            raise
        except GenerationError as exc:
            error = exc
    assert error is not None
    raise error


def _generate_checked[T: BaseModel](
    prompt: str,
    schema: type[T],
    *,
    system_instruction: str,
    check: Callable[[T], None],
) -> T:
    """Try the primary model, then the fallback model after a service pause."""
    settings = get_settings()
    models = [settings.GEMINI_MODEL]
    if settings.GEMINI_FALLBACK_MODEL and settings.GEMINI_FALLBACK_MODEL != settings.GEMINI_MODEL:
        models.append(settings.GEMINI_FALLBACK_MODEL)
    error: GenerationError | None = None
    for index, model in enumerate(models):
        if index:
            time.sleep(_SERVICE_DELAY)
        try:
            return _attempt_model(
                prompt,
                schema,
                system_instruction=system_instruction,
                model=model,
                check=check,
            )
        except TransientGeminiError as exc:
            error = GenerationError(str(exc))
            if index == len(models) - 1:
                raise error from exc
        except PermanentGeminiError:
            raise
        except GenerationError as exc:
            error = exc
    assert error is not None
    raise error


ANAGRAM_SYSTEM = """You are a world-class word puzzle master for top daily newspapers like The New York Times.

Before you fill the JSON, draft a candidate word and a scrambled version internally, then rate difficulty from 1 to 10. Emit the puzzle only when that score is 5, 6, or 7. Do not include the draft, the score, or any reasoning in the JSON.

Constraints:
- solution is one English word of 6 to 8 letters, familiar to a general audience, and non-obvious once scrambled.
- scrambled_word uses exactly the same letters as solution and is not the word itself.
- hint is a subtle contextual clue that creates a rewarding aha moment, not a definition that gives the word away.
- hint must not contain the solution, a root or inflected form of it, or a direct synonym. "whispering" and "hushed" both give away WHISPER.
- prompt stays a short instruction to unscramble the letters.
- explanation states the word and why the hint fits, in one or two sentences.
"""

PATTERN_SYSTEM = """You are a senior logic and intelligence puzzle writer for Mensa and GCHQ.

Before you fill the JSON, confirm internally that the transformation rule is fully deterministic and unambiguous, and that solving it takes at least two logical steps. Rate it from 1 to 10 and emit it only when that score is 5, 6, or 7. Do not include that reasoning in the JSON.

Shared rules:
- grid is 3 rows of 3 cells with exactly one null blank.
- choices has exactly 3 distinct options, and solution equals the blank cell and is one of the choices.
- prompt is ignored by the app (a fixed player instruction is applied later). Put any short placeholder.
- explanation must name the exact rule and walk through enough cells that a reader can confirm every filled cell fits. If your stated rule does not reproduce all filled cells, discard the puzzle and invent a different one.
"""

SHAPE_SYSTEM = """You are a senior logic and intelligence puzzle writer for Mensa and GCHQ.

Before you fill the JSON, confirm internally that the transformation rule is fully deterministic and unambiguous, and that solving it takes at least two logical steps. Rate it from 1 to 10 and emit it only when that score is 5, 6, or 7. Do not include that reasoning in the JSON.

Shared rules for shape puzzles:
- grid is 4 rows of 4 cells with exactly one null blank.
- choices has exactly 4 distinct options, and solution equals the blank cell and is one of the choices.
- prompt is ignored by the app (a fixed player instruction is applied later). Put any short placeholder.
- explanation must name the exact rule and confirm the blank from that rule. If the rule does not fit the filled cells, discard and invent a different puzzle.
"""

# Shown on the board. Never trust the model to write these (it often spoils the rule).
PATTERN_BOARD_PROMPTS: dict[PatternKind, str] = {
    "numerical": "Identify the missing number that completes the pattern.",
    "unicode": "Identify the missing symbol to complete the pattern.",
    "shape": "Identify the missing shape that completes the pattern.",
}

NEWS_SYSTEM = """You are a lead editor for a premier weekly global current events quiz.

Before you fill the JSON, draft the question and three distractors internally, then rate difficulty from 1 to 10. Emit the puzzle only when that score is 5, 6, or 7. Do not include that draft in the JSON.

Constraints:
- One multiple-choice question on significant science, technology, global culture, or major news.
- Avoid trivial micro-details, dates of minor incidents, and obscure proper nouns.
- options has exactly 4 distinct choices. solution is one of them.
- The four options are distinct concepts, not synonyms, subtypes, or rephrasings of one another.
- The other three options are plausible educated guesses, not jokes or obvious throwaways.
- source_headline is a short plausible headline about the event. hint may be null or a light nudge.
- question, source_headline, and hint must not contain the solution phrase or any of its root words, including hyphenated or inflected forms. "nitrogen-fixing" is an echo of "nitrogen fixation" and is not allowed.
- question and hint must not share a stem with any option. A player must not be able to eliminate a choice by matching a word in the question or hint to a word in an option.
- A reader who sees only the headline must still need the question to choose an answer.
- explanation says why the answer is right in one or two sentences.
"""

_PATTERN_PROMPTS: dict[PatternKind, str] = {
    "numerical": (
        "Create one original multi-step numerical progression on a 3x3 grid. "
        "Use JSON integers only. The rule must need at least two steps, such as "
        "alternating operations (+2 then ×3) or a Fibonacci-style offset. "
        "Do not use a single constant add or multiply along any row or column. "
        "A grid such as 2 4 6 / 3 6 9 / 4 8 12 is rejected. "
        "Before returning JSON, verify that your explanation's rule reproduces every "
        "filled cell; if it does not, invent a different grid and rule. "
        "Do not put the solving rule in prompt."
    ),
    "unicode": (
        "Create one original Unicode symbol grid transformation. "
        "Every filled cell, every choice, and the solution is a short Unicode symbol "
        "string such as ▲, ■, ◯, or ➔. The rule is a rotation, reflection, or matrix "
        "balance that is unambiguous. Do not use numbers or shape objects. "
        "Do not put the solving rule in prompt."
    ),
}


def _shape_task_prompt() -> str:
    return (
        "Create one original 4x4 shape puzzle at difficulty 5, 6, or 7. "
        "Exactly one cell is null. Count is 1 in every cell and every choice. "
        "Use only triangle (3 sides), square (4), pentagon (5), and hexagon (6). "
        "Colors are red, blue, green, purple, yellow, and orange. Use at least two colors. "
        "Along each row, side count changes by the same step of +1, +2, -1, or -2, "
        "and rotation changes by the same 90, 180, or 270 degrees, wrapping at 360. "
        "Alternate the direction from row to row so the rows are not copies of each other. "
        "The blank's shape must be a triangle, pentagon, or hexagon so its turn is visible. "
        "Color is either a row or column tint, or a further step in the rule. "
        "Tint: every cell in a row shares one color, or every cell in a column shares one color, "
        "and different rows or columns use different colors, such as row 1 purple and row 2 orange. "
        "When color is only a tint, every choice uses the blank row's color, or the blank column's "
        "color if columns are tinted, so color cannot eliminate a button. "
        "When color changes inside the rows and columns as part of the rule, at least two choices "
        "must share both the solution color and the solution shape, so the solver still has to "
        "use rotation or side-count arithmetic. "
        "Provide exactly 4 distinct choices, and include the solution. "
        "One distractor is a strict near miss: the solution shape and color turned by one step "
        "of that row's rotation, or the same color whose side count is that row's side step reversed. "
        "Another distractor keeps the solution shape at a different rotation. "
        "Shape alone and color alone must not identify the answer. "
        "Forbidden: a row or column that merely contains one of each color, or one of each shape, "
        "and any rule where the missing color is the answer. "
        "Do not use numbers or plain strings. "
        "Do not put the solving rule in prompt."
    )


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _matches_kind(value: object, kind: PatternKind) -> bool:
    if kind == "numerical":
        return _is_int(value)
    if kind == "unicode":
        return isinstance(value, str) and bool(value.strip())
    return isinstance(value, ShapeItem)


def _choice_identity(value: object) -> str:
    if isinstance(value, ShapeItem):
        return json.dumps(value.model_dump(), sort_keys=True, separators=(",", ":"))
    return json.dumps(value)


def stored_pattern_solution(solution: int | str | ShapeItem) -> object:
    if isinstance(solution, ShapeItem):
        return solution.model_dump()
    return solution


def _plain_json(value: object) -> object:
    if isinstance(value, ShapeItem):
        return value.model_dump()
    if isinstance(value, list):
        return [_plain_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _plain_json(item) for key, item in value.items()}
    return value


def _fingerprint(value: object) -> str:
    return json.dumps(_plain_json(value), sort_keys=True, separators=(",", ":"))


def anagram_identity(solution: object) -> str:
    text = solution if isinstance(solution, str) else ""
    return text.strip().casefold()


def news_identity(question: object) -> str:
    return _compact(question if isinstance(question, str) else "")


def pattern_identity(grid: object, solution: object) -> str:
    return _fingerprint({"grid": grid, "solution": stored_pattern_solution(solution)})


def stored_puzzle_identity(puzzle_type: PuzzleType, content: object, solution: object) -> str:
    payload = content if isinstance(content, dict) else {}
    if puzzle_type == PuzzleType.ANAGRAM:
        return anagram_identity(solution)
    if puzzle_type == PuzzleType.NEWS_QUIZ:
        return news_identity(payload.get("question"))
    return pattern_identity(payload.get("grid"), solution)


def _reject_repeat(key: str, taken: set[str] | None) -> None:
    if taken is not None and key in taken:
        raise GenerationError("Puzzle repeats one that is already stored")


def _arithmetic_blank(values: list[int | None]) -> int | None:
    known = [(index, value) for index, value in enumerate(values) if value is not None]
    blanks = [index for index, value in enumerate(values) if value is None]
    if len(blanks) != 1 or len(known) < 2:
        return None
    origin, origin_value = known[0]
    span = known[1][0] - origin
    if span == 0 or (known[1][1] - origin_value) % span != 0:
        return None
    step = (known[1][1] - origin_value) // span
    for index, value in known:
        if value != origin_value + step * (index - origin):
            return None
    return origin_value + step * (blanks[0] - origin)


def _integer_root(value: int, power: int) -> int | None:
    if value < 0 or power < 1:
        return None
    root = round(value ** (1 / power))
    if root**power == value:
        return int(root)
    return None


def _geometric_blank(values: list[int | None]) -> int | None:
    known = [(index, value) for index, value in enumerate(values) if value is not None]
    blanks = [index for index, value in enumerate(values) if value is None]
    if len(blanks) != 1 or len(known) < 2 or any(value == 0 for _, value in known):
        return None
    origin, origin_value = known[0]
    span = known[1][0] - origin
    if span <= 0 or known[1][1] % origin_value != 0:
        return None
    ratio = _integer_root(known[1][1] // origin_value, span)
    if ratio is None:
        return None
    for index, value in known:
        if value != origin_value * ratio ** (index - origin):
            return None
    return origin_value * ratio ** (blanks[0] - origin)


def _reject_one_step_numbers(raw: GeneratedPattern) -> None:
    if not isinstance(raw.solution, int):
        return
    columns = list(zip(*raw.grid, strict=True))
    for line in (*raw.grid, *columns):
        numbers: list[int | None] = []
        for cell in line:
            if cell is None:
                numbers.append(None)
            elif isinstance(cell, int) and not isinstance(cell, bool):
                numbers.append(cell)
            else:
                return
        for predicted in (_arithmetic_blank(numbers), _geometric_blank(numbers)):
            if predicted is not None and predicted == raw.solution:
                raise GenerationError(
                    "Numerical pattern is solved by one constant add or multiply"
                )


def _reject_repeated_symbol(raw: GeneratedPattern) -> None:
    if not isinstance(raw.solution, str):
        return
    filled = [cell for row in raw.grid for cell in row if isinstance(cell, str)]
    if len(filled) >= 2 and len(set(filled)) < 3:
        raise GenerationError("Unicode pattern needs at least three distinct symbols")
    columns = list(zip(*raw.grid, strict=True))
    for line in (*raw.grid, *columns):
        symbols = [cell for cell in line if isinstance(cell, str)]
        blanks = sum(cell is None for cell in line)
        if blanks == 1 and len(symbols) >= 2 and len(set(symbols)) == 1 and symbols[0] == raw.solution:
            raise GenerationError("Unicode pattern is solved by repeating one symbol")


def _validate_pattern(
    raw: GeneratedPattern,
    kind: PatternKind,
    taken: set[str] | None = None,
) -> None:
    raw.grid = [[coerce_pattern_cell(cell) for cell in row] for row in raw.grid]
    size = 4 if kind == "shape" else 3
    if len(raw.grid) != size or any(len(row) != size for row in raw.grid):
        raise GenerationError(f"Pattern grid must be {size}x{size}")
    blanks = sum(cell is None for row in raw.grid for cell in row)
    if blanks != 1:
        raise GenerationError("Pattern grid must contain exactly one blank")
    choice_count = 4 if kind == "shape" else 3
    if len(raw.choices) != choice_count:
        raise GenerationError(f"Pattern must provide exactly {choice_count} choices")
    if len({_choice_identity(choice) for choice in raw.choices}) != choice_count:
        raise GenerationError("Pattern choices must be distinct")
    filled = [cell for row in raw.grid for cell in row if cell is not None]
    for value in (*filled, *raw.choices, raw.solution):
        if not _matches_kind(value, kind):
            raise GenerationError(f"Pattern value does not match {kind}")
    if raw.solution not in raw.choices:
        raise GenerationError("Pattern solution must appear in choices")
    if kind == "numerical":
        _reject_one_step_numbers(raw)
    elif kind == "unicode":
        _reject_repeated_symbol(raw)
    elif kind == "shape":
        _validate_shape_rules(raw)
    _reject_repeat(pattern_identity(raw.grid, raw.solution), taken)


_STEM_SUFFIXES = (
    "ization",
    "isation",
    "ation",
    "tion",
    "sion",
    "ing",
    "ers",
    "ies",
    "ied",
    "ed",
    "es",
    "s",
)


_SIDE_COUNTS = {"triangle": 3, "square": 4, "pentagon": 5, "hexagon": 6}
_VISIBLE_TURN = {"triangle", "pentagon", "hexagon"}


def _adjacent_step(values: list[int | None], *, modulo: int | None = None) -> int | None:
    deltas: list[int] = []
    for left, right in zip(values, values[1:], strict=False):
        if left is None or right is None:
            continue
        delta = right - left
        if modulo is not None:
            delta %= modulo
        deltas.append(delta)
    if not deltas or len(set(deltas)) != 1 or deltas[0] == 0:
        return None
    return deltas[0]


def _predictions(
    values: list[int | None],
    index: int,
    step: int,
    *,
    modulo: int | None = None,
) -> list[int]:
    predicted: list[int] = []
    for anchor, value in enumerate(values):
        if value is None or anchor == index:
            continue
        result = value + step * (index - anchor)
        if modulo is not None:
            result %= modulo
        predicted.append(result)
    return predicted


def _line_color(cells: list[object] | tuple[object, ...]) -> str | None:
    found = {cell.color for cell in cells if isinstance(cell, ShapeItem)}
    if len(found) == 1:
        return next(iter(found))
    return None


def _reject_missing_color(
    lines: list[list[object]] | list[tuple[object, ...]],
    blank_index: int,
    solution_color: str,
) -> None:
    def colors(line: list[object] | tuple[object, ...]) -> tuple[str, ...]:
        return tuple(sorted(cell.color for cell in line if isinstance(cell, ShapeItem)))

    complete = [
        colors(line) for index, line in enumerate(lines) if index != blank_index
    ]
    if not complete or len(set(complete)) != 1 or len(complete[0]) != 4:
        return
    blank_colors = set(colors(lines[blank_index]))
    missing = set(complete[0]) - blank_colors
    if missing == {solution_color} and solution_color not in blank_colors:
        raise GenerationError("Missing color must not be the answer")


def _validate_shape_rules(raw: GeneratedPattern) -> None:
    if not isinstance(raw.solution, ShapeItem):
        raise GenerationError("Shape solution must be a shape object")
    solution = raw.solution
    choice_items = [choice for choice in raw.choices if isinstance(choice, ShapeItem)]
    if solution.shape not in _VISIBLE_TURN:
        raise GenerationError("The blank shape must show its rotation")
    blank = next(
        (row_index, col_index)
        for row_index, row in enumerate(raw.grid)
        for col_index, cell in enumerate(row)
        if cell is None
    )
    shape_rows: list[tuple[str, ...]] = []
    blank_side_step = 0
    blank_turn_step = 0
    for row_index, row in enumerate(raw.grid):
        sides: list[int | None] = []
        turns: list[int | None] = []
        shapes: list[str] = []
        for cell in row:
            if not isinstance(cell, ShapeItem):
                sides.append(None)
                turns.append(None)
                continue
            if cell.shape not in _SIDE_COUNTS:
                raise GenerationError(
                    "Shape progression must use triangle, square, pentagon, or hexagon"
                )
            if cell.count != 1:
                raise GenerationError("Shape cells must have a count of 1")
            sides.append(_SIDE_COUNTS[cell.shape])
            turns.append(cell.rotation)
            shapes.append(cell.shape)
        side_step = _adjacent_step(sides)
        turn_step = _adjacent_step(turns, modulo=360)
        if side_step not in (-2, -1, 1, 2):
            raise GenerationError("Each row must change side count by 1 or 2")
        if turn_step not in (90, 180, 270):
            raise GenerationError("Each row must turn by a constant 90, 180, or 270 degrees")
        if row_index != blank[0]:
            shape_rows.append(tuple(shapes))
            continue
        blank_side_step = side_step
        blank_turn_step = turn_step
        side_matches = _predictions(sides, blank[1], side_step)
        turn_matches = _predictions(turns, blank[1], turn_step, modulo=360)
        if len(set(side_matches)) != 1 or side_matches[0] != _SIDE_COUNTS[solution.shape]:
            raise GenerationError("Solution shape does not fit the side-count step")
        if len(set(turn_matches)) != 1 or turn_matches[0] != solution.rotation:
            raise GenerationError("Solution rotation does not fit the turn step")
    if len(set(shape_rows)) < 2:
        raise GenerationError("Rows must not repeat one shape sequence")
    colors_used = {
        cell.color
        for row in raw.grid
        for cell in row
        if isinstance(cell, ShapeItem)
    }
    if len(colors_used) < 2:
        raise GenerationError("Shape puzzles must use at least two colors")
    row_tint = all(_line_color(row) is not None for row in raw.grid)
    columns = [tuple(row[index] for row in raw.grid) for index in range(len(raw.grid))]
    column_tint = all(_line_color(column) is not None for column in columns)
    if row_tint or column_tint:
        if row_tint and _line_color(raw.grid[blank[0]]) != solution.color:
            raise GenerationError("Solution color must match the blank row")
        blank_column = columns[blank[1]]
        if column_tint and _line_color(blank_column) != solution.color:
            raise GenerationError("Solution color must match the blank column")
        if any(choice.color != solution.color for choice in choice_items):
            raise GenerationError(
                "Tinted puzzles must use the target line's color on every choice"
            )
    else:
        shared = sum(
            choice.shape == solution.shape and choice.color == solution.color
            for choice in choice_items
        )
        if shared < 2:
            raise GenerationError(
                "When color is part of the rule, two choices must share the solution shape and color"
            )
        _reject_missing_color(raw.grid, blank[0], solution.color)
        _reject_missing_color(columns, blank[1], solution.color)
    if any(choice.count != 1 for choice in choice_items):
        raise GenerationError("Shape choices must have a count of 1")
    others = [choice for choice in choice_items if choice != solution]
    if not any(
        choice.shape == solution.shape and choice.rotation != solution.rotation
        for choice in others
    ):
        raise GenerationError(
            "A distractor must share the solution shape at a different rotation"
        )
    if sum(choice.shape == solution.shape for choice in choice_items) < 2:
        raise GenerationError("Shape alone must not identify the answer")
    if sum(choice.color == solution.color for choice in choice_items) < 2:
        raise GenerationError("Color alone must not identify the answer")
    off_rotations = {
        (solution.rotation + blank_turn_step) % 360,
        (solution.rotation - blank_turn_step) % 360,
    } - {solution.rotation}
    inverse_sides = _SIDE_COUNTS[solution.shape] - blank_side_step
    inverse_shape = next(
        (name for name, sides in _SIDE_COUNTS.items() if sides == inverse_sides),
        None,
    )

    def _near_miss(choice: ShapeItem) -> bool:
        if choice.color != solution.color:
            return False
        if choice.shape == solution.shape and choice.rotation in off_rotations:
            return True
        return inverse_shape is not None and choice.shape == inverse_shape

    if not any(_near_miss(choice) for choice in others):
        raise GenerationError(
            "A distractor must be a one-step rotation or reversed side-count near miss"
        )


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def _stem(word: str) -> str:
    for suffix in _STEM_SUFFIXES:
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _roots(text: str) -> set[str]:
    roots: set[str] = set()
    for token in _tokens(text):
        if len(token) < 4:
            continue
        roots.add(token)
        stem = _stem(token)
        if len(stem) >= 3:
            roots.add(stem)
    return roots


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _validate_news_quiz(raw: GeneratedNewsQuiz, taken: set[str] | None = None) -> None:
    if len(raw.options) != 4 or len(set(raw.options)) != 4:
        raise GenerationError("News quiz must have exactly 4 distinct options")
    if raw.solution not in raw.options:
        raise GenerationError("News quiz solution must be one of the options")
    context = " ".join(
        part
        for part in (raw.question, raw.source_headline or "", raw.hint or "")
        if part
    )
    solution = raw.solution.strip()
    if _compact(solution) and _compact(solution) in _compact(context):
        raise GenerationError("News quiz context repeats the solution phrase")
    leaked = sorted(_roots(solution) & _roots(context))
    if leaked:
        raise GenerationError(
            "News quiz question, headline, or hint echoes the solution: "
            + ", ".join(leaked)
        )
    prompt_context = " ".join(
        part for part in (raw.question, raw.hint or "") if part
    )
    for option in raw.options:
        shared = sorted(_roots(option) & _roots(prompt_context))
        if shared:
            raise GenerationError(
                "News quiz question or hint shares a stem with an option: "
                + ", ".join(shared)
            )
    _reject_repeat(news_identity(raw.question), taken)


def _load_english_anagram_words() -> frozenset[str]:
    path = Path(__file__).resolve().parents[1] / "data" / "anagram_words.txt"
    words: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        word = line.strip().casefold()
        if not word or word.startswith("#"):
            continue
        words.add(word)
    return frozenset(words)


# 6–8 letter English words that appear in normal writing. Not a menu of puzzle answers.
_ENGLISH_ANAGRAM_WORDS = _load_english_anagram_words()


# Very common 6–8 letter words. A scrambled form of these is still obvious.
_EASY_ANAGRAM_WORDS = frozenset(
    {
        "people",
        "little",
        "before",
        "should",
        "number",
        "system",
        "public",
        "around",
        "another",
        "because",
        "through",
        "between",
        "without",
        "something",
        "nothing",
        "already",
        "always",
        "change",
        "during",
        "family",
        "friend",
        "school",
        "second",
        "water",
        "world",
        "country",
        "problem",
        "company",
        "service",
        "student",
        "history",
        "morning",
        "answer",
        "letter",
        "mother",
        "father",
        "sister",
        "brother",
        "garden",
        "window",
        "yellow",
        "animal",
        "simple",
        "really",
        "please",
        "person",
        "things",
        "thinks",
        "called",
        "enough",
        "almost",
        "better",
        "having",
        "myself",
        "others",
        "house",
        "place",
        "great",
        "again",
        "still",
        "never",
        "every",
        "where",
        "after",
        "about",
        "would",
        "could",
        "there",
        "their",
        "which",
        "these",
        "those",
        "other",
        "first",
        "being",
        "under",
        "while",
        "might",
        "going",
        "years",
        "three",
        "small",
        "large",
        "right",
        "sound",
        "found",
        "house",
    }
)


def _validate_anagram(raw: GeneratedAnagram, taken: set[str] | None = None) -> None:
    word = raw.solution.strip()
    if word.casefold() in _EASY_ANAGRAM_WORDS:
        raise GenerationError("Anagram solution is too common")
    scrambled = raw.scrambled_word.strip()
    if not word.isalpha() or not 6 <= len(word) <= 8:
        raise GenerationError("Anagram solution must be a single word of 6 to 8 letters")
    if word.casefold() not in _ENGLISH_ANAGRAM_WORDS:
        raise GenerationError("Anagram solution is not an English word")
    if not scrambled.isalpha():
        raise GenerationError("scrambled_word must contain only letters")
    if Counter(scrambled.casefold()) != Counter(word.casefold()):
        raise GenerationError("scrambled_word must use the same letters as solution")
    if scrambled.casefold() == word.casefold():
        raise GenerationError("scrambled_word must not be the solution itself")
    if raw.hint is None or not raw.hint.strip():
        raise GenerationError("Anagram hint must be non-empty")
    echoed = _hint_echoes_solution(word, raw.hint)
    if echoed:
        raise GenerationError(
            f"Anagram hint contains a root of the solution: {echoed}"
        )
    _reject_repeat(anagram_identity(word), taken)


def _hint_echoes_solution(word: str, hint: str) -> str | None:
    shared = sorted(_roots(word) & _roots(hint))
    if shared:
        return ", ".join(shared)
    compact = _compact(hint).replace(" ", "")
    for token in _tokens(word):
        if len(token) < 4:
            continue
        if token in compact:
            return token
        stem = _stem(token)
        if len(stem) >= 4 and stem in compact:
            return stem
    return None


def _shape_as_pattern(raw: GeneratedShape) -> GeneratedPattern:
    return GeneratedPattern(
        grid=raw.grid,
        prompt=raw.prompt,
        choices=raw.choices,
        solution=raw.solution,
        explanation=raw.explanation,
    )


def generate_pattern_puzzle(taken: set[str] | None = None) -> GeneratedPuzzle:
    kind = random.choice(("numerical", "unicode", "shape"))
    if kind == "shape":
        shape = _generate_checked(
            _shape_task_prompt(),
            GeneratedShape,
            system_instruction=SHAPE_SYSTEM,
            check=lambda payload: _validate_pattern(_shape_as_pattern(payload), "shape", taken),
        )
        raw = _shape_as_pattern(shape)
    else:
        raw = _generate_checked(
            _PATTERN_PROMPTS[kind],
            GeneratedPattern,
            system_instruction=PATTERN_SYSTEM,
            check=lambda payload: _validate_pattern(payload, kind, taken),
        )
    content = PatternContent(
        grid=raw.grid,
        prompt=PATTERN_BOARD_PROMPTS[kind],
        choices=raw.choices,
    ).model_dump()
    solution = stored_pattern_solution(raw.solution)
    return GeneratedPuzzle(
        puzzle_type=PuzzleType.PATTERN,
        content=content,
        solution=solution,
        explanation=raw.explanation,
        solution_hash=hash_solution(solution),
    )


def generate_anagram_puzzle(taken: set[str] | None = None) -> GeneratedPuzzle:
    raw = _generate_checked(
        "Create one original anagram that follows the system constraints.",
        GeneratedAnagram,
        system_instruction=ANAGRAM_SYSTEM,
        check=lambda payload: _validate_anagram(payload, taken),
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


def generate_news_quiz_puzzle(taken: set[str] | None = None) -> GeneratedPuzzle:
    raw = _generate_checked(
        "Create one original news-quiz item that follows the system constraints.",
        GeneratedNewsQuiz,
        system_instruction=NEWS_SYSTEM,
        check=lambda payload: _validate_news_quiz(payload, taken),
    )
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


def generate_puzzle(
    puzzle_type: PuzzleType,
    taken: set[str] | None = None,
) -> GeneratedPuzzle:
    if puzzle_type == PuzzleType.PATTERN:
        return generate_pattern_puzzle(taken)
    if puzzle_type == PuzzleType.ANAGRAM:
        return generate_anagram_puzzle(taken)
    if puzzle_type == PuzzleType.NEWS_QUIZ:
        return generate_news_quiz_puzzle(taken)
    raise GenerationError(f"Unsupported puzzle type: {puzzle_type}")
