from unittest.mock import patch

import pytest

from app.models.puzzle import PuzzleType
from app.schemas.puzzle import PatternContent, ShapeItem
from app.services.generator import (
    PATTERN_BOARD_PROMPTS,
    GeneratedAnagram,
    GeneratedNewsQuiz,
    GeneratedPattern,
    GeneratedShape,
    GenerationError,
    _validate_anagram,
    _validate_news_quiz,
    _validate_pattern,
    anagram_identity,
    generate_pattern_puzzle,
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


def test_pattern_board_prompts_are_fixed_player_copy() -> None:
    assert PATTERN_BOARD_PROMPTS["numerical"] == (
        "Identify the missing number that completes the pattern."
    )
    assert PATTERN_BOARD_PROMPTS["unicode"] == (
        "Identify the missing symbol to complete the pattern."
    )
    assert PATTERN_BOARD_PROMPTS["shape"] == (
        "Identify the missing shape that completes the pattern."
    )


def test_generate_pattern_puzzle_overwrites_model_prompt() -> None:
    spoiler = GeneratedPattern(
        grid=[[2, 4, 12], [3, 6, 24], [4, 8, None]],
        prompt="Multiply the middle number by 3 to get the third.",
        choices=[16, 20, 24],
        solution=24,
        explanation="Third equals middle times 3.",
    )

    with (
        patch("app.services.generator.random.choice", return_value="numerical"),
        patch("app.services.generator._generate_checked", return_value=spoiler),
    ):
        puzzle = generate_pattern_puzzle()

    assert puzzle.puzzle_type == PuzzleType.PATTERN
    assert puzzle.content["prompt"] == PATTERN_BOARD_PROMPTS["numerical"]
    assert puzzle.content["prompt"] != spoiler.prompt


def test_generate_shape_pattern_overwrites_model_prompt() -> None:
    solution = ShapeItem(shape="triangle", color="red", rotation=90, count=1)
    near = ShapeItem(shape="triangle", color="red", rotation=180, count=1)
    other_a = ShapeItem(shape="pentagon", color="red", rotation=90, count=1)
    other_b = ShapeItem(shape="hexagon", color="blue", rotation=0, count=1)
    # Minimal shape payload for the board-prompt overwrite path; validation is skipped
    # because _generate_checked is mocked after the kind is forced to shape.
    spoiler = GeneratedShape(
        grid=[[solution, solution, solution, solution]] * 4,
        prompt="Count the sides then rotate by 90.",
        choices=[solution, near, other_a, other_b],
        solution=solution,
        explanation="Sides and rotation.",
    )

    with (
        patch("app.services.generator.random.choice", return_value="shape"),
        patch("app.services.generator._generate_checked", return_value=spoiler),
    ):
        puzzle = generate_pattern_puzzle()

    assert puzzle.content["prompt"] == PATTERN_BOARD_PROMPTS["shape"]
    assert puzzle.content["prompt"] != spoiler.prompt
