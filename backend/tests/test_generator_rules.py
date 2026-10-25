import pytest

from app.schemas.puzzle import PatternContent
from app.services.generator import (
    GeneratedAnagram,
    GeneratedPattern,
    GenerationError,
    _validate_anagram,
    _validate_pattern,
)


def _pattern(grid: list[list[object]], solution: int | str) -> GeneratedPattern:
    return GeneratedPattern(
        grid=grid,
        prompt="Find the missing value.",
        choices=[16, 20, solution] if isinstance(solution, int) else ["a", "b", solution],
        solution=solution,
        explanation="Two steps.",
    )


def test_times_table_is_rejected() -> None:
    raw = _pattern([[2, 4, 6], [3, 6, 9], [4, 8, None]], 12)
    with pytest.raises(GenerationError, match="one constant add or multiply"):
        _validate_pattern(raw, "numerical")


def test_two_step_number_grid_is_accepted() -> None:
    raw = _pattern([[2, 4, 12], [3, 6, 24], [4, 8, None]], 24)
    _validate_pattern(raw, "numerical")


def test_null_word_is_the_blank() -> None:
    raw = _pattern([[2, 4, 12], [3, 6, 24], [4, 8, "null"]], 24)
    _validate_pattern(raw, "numerical")
    assert raw.grid[2][2] is None

    stored = PatternContent.model_validate(
        {"grid": [[1, 2, "NONE"], [4, 5, 6], [7, 8, 9]], "prompt": "Find it."}
    )
    assert stored.grid[0][2] is None


def test_common_anagram_is_rejected() -> None:
    raw = GeneratedAnagram(
        scrambled_word="elpoep",
        hint="A group.",
        solution="people",
        explanation="Rearrange.",
    )
    with pytest.raises(GenerationError, match="too common"):
        _validate_anagram(raw)
