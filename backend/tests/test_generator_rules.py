import pytest

from app.schemas.puzzle import PatternContent
from app.services.generator import (
    GeneratedAnagram,
    GeneratedNewsQuiz,
    GeneratedPattern,
    GenerationError,
    _validate_anagram,
    _validate_news_quiz,
    _validate_pattern,
    anagram_identity,
    news_identity,
    pattern_identity,
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


def _anagram(solution: str, scrambled: str) -> GeneratedAnagram:
    return GeneratedAnagram(
        scrambled_word=scrambled,
        hint="A useful clue.",
        solution=solution,
        explanation="Rearrange.",
    )


def test_real_anagram_is_accepted() -> None:
    _validate_anagram(_anagram("monarch", "charomn"))


def test_invented_anagram_is_rejected() -> None:
    raw = _anagram("chroned", "dorenhc")
    with pytest.raises(GenerationError, match="not an English word"):
        _validate_anagram(raw)


def test_repeated_anagram_is_rejected() -> None:
    raw = _anagram("monarch", "charomn")
    with pytest.raises(GenerationError, match="already stored"):
        _validate_anagram(raw, {anagram_identity(raw.solution)})


def test_repeated_pattern_is_rejected() -> None:
    raw = _pattern([[2, 4, 12], [3, 6, 24], [4, 8, None]], 24)
    with pytest.raises(GenerationError, match="already stored"):
        _validate_pattern(raw, "numerical", {pattern_identity(raw.grid, raw.solution)})


def test_repeated_news_question_is_rejected() -> None:
    raw = GeneratedNewsQuiz(
        question="Which city hosted the closing ceremony?",
        options=["Lisbon", "Oslo", "Riga", "Bern"],
        solution="Lisbon",
        explanation="Lisbon hosted the ceremony.",
        source_headline="Ceremony ends",
        hint=None,
    )
    _validate_news_quiz(raw)
    with pytest.raises(GenerationError, match="already stored"):
        _validate_news_quiz(raw, {news_identity(raw.question)})


def test_common_anagram_is_rejected() -> None:
    raw = GeneratedAnagram(
        scrambled_word="elpoep",
        hint="A group.",
        solution="people",
        explanation="Rearrange.",
    )
    with pytest.raises(GenerationError, match="too common"):
        _validate_anagram(raw)
