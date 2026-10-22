from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import Puzzle, PuzzleType, UserCompletion
from tests.conftest import (
    auth_header,
    cleanup_puzzle,
    cleanup_user,
    create_puzzle,
    create_user,
)


def _assert_public_item(item: dict) -> None:
    assert "solution" not in item
    assert "solution_hash" not in item
    assert "explanation" not in item
    content = item["content"]
    assert "solution" not in content
    assert "solution_hash" not in content
    assert "explanation" not in content


async def _free_dates(
    session,
    today: date,
    count: int,
    *,
    future: bool = False,
) -> list[date]:
    taken = set(
        (
            await session.scalars(
                select(Puzzle.assigned_date).where(Puzzle.assigned_date.is_not(None))
            )
        ).all()
    )
    found: list[date] = []
    day = today + timedelta(days=1) if future else today
    step = timedelta(days=1 if future else -1)
    while len(found) < count:
        if day not in taken:
            found.append(day)
        day += step
    return found


async def _archive(client, **params):
    headers = params.pop("headers", None)
    response = await client.get("/api/puzzles/archive", params=params, headers=headers)
    return response


async def _find_archive_item(client, puzzle_id: str, **params) -> dict:
    page = 1
    while page < 40:
        response = await _archive(client, page=page, limit=50, **params)
        assert response.status_code == 200
        body = response.json()
        match = next((item for item in body["items"] if item["id"] == puzzle_id), None)
        if match is not None:
            return match
        if not body["items"] or page * 50 >= body["total"]:
            break
        page += 1
    raise AssertionError(f"{puzzle_id} was not in the archive list")


@pytest.mark.asyncio
async def test_archive_list_requires_auth(client) -> None:
    response = await client.get("/api/puzzles/archive")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_guest_archive_submit_requires_auth(client, session, today_utc) -> None:
    assigned, = await _free_dates(session, today_utc - timedelta(days=1), 1)
    puzzle = await create_puzzle(session, assigned=assigned, solution=9)

    response = await client.post(
        f"/api/puzzles/{puzzle.id}/submit",
        json={"answer": 9, "time_taken_seconds": 10},
    )
    assert response.status_code == 401
    assert "correct_answer" not in response.json()
    assert "explanation" not in response.json()

    await cleanup_puzzle(session, puzzle.id)


@pytest.mark.asyncio
async def test_archive_list_hides_future_and_solutions(client, session, today_utc) -> None:
    viewer = await create_user(session)
    headers = auth_header(viewer)
    past_day, = await _free_dates(session, today_utc - timedelta(days=1), 1)
    future_day, = await _free_dates(session, today_utc, 1, future=True)
    past = await create_puzzle(
        session,
        assigned=past_day,
        solution="I",
        explanation="The missing letter is I.",
        content={
            "grid": [["A", "B", "C"], ["D", "E", "F"], ["G", "H", None]],
            "prompt": "letter?",
            "choices": ["I", "J", "K"],
        },
    )
    future = await create_puzzle(session, assigned=future_day, solution=4)

    response = await _archive(client, page=1, limit=50, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["limit"] == 50
    assert body["total"] >= 1
    ids = [item["id"] for item in body["items"]]
    assert str(future.id) not in ids
    assert all(item["assigned_date"] < today_utc.isoformat() for item in body["items"])
    for item in body["items"]:
        _assert_public_item(item)
        assert item["is_completed"] is False
        assert item["is_correct"] is None
        assert item["score"] is None

    match = await _find_archive_item(client, str(past.id), headers=headers)
    assert match["puzzle_type"] == "pattern"
    assert match["content"]["prompt"] == "letter?"
    assert match["is_completed"] is False
    assert match["is_correct"] is None
    assert match["score"] is None

    await cleanup_user(session, viewer.id)
    await cleanup_puzzle(session, past.id)
    await cleanup_puzzle(session, future.id)


@pytest.mark.asyncio
async def test_archive_list_paginates_newest_first(client, session, today_utc) -> None:
    viewer = await create_user(session)
    headers = auth_header(viewer)
    newer_day, older_day = await _free_dates(session, today_utc - timedelta(days=1), 2)
    newer = await create_puzzle(session, assigned=newer_day, solution=1)
    older = await create_puzzle(session, assigned=older_day, solution=2)

    first = await _archive(client, page=1, limit=1, headers=headers)
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["limit"] == 1
    assert len(first_body["items"]) == 1
    assert first_body["total"] >= 2

    second = await _archive(client, page=2, limit=1, headers=headers)
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["items"][0]["id"] != first_body["items"][0]["id"]
    assert second_body["items"][0]["assigned_date"] <= first_body["items"][0]["assigned_date"]

    seen: list[dict] = []
    page = 1
    while len(seen) < first_body["total"]:
        page_body = (await _archive(client, page=page, limit=50, headers=headers)).json()
        seen.extend(page_body["items"])
        if not page_body["items"]:
            break
        page += 1
    positions = {item["id"]: index for index, item in enumerate(seen)}
    assert positions[str(newer.id)] < positions[str(older.id)]

    await cleanup_user(session, viewer.id)
    await cleanup_puzzle(session, newer.id)
    await cleanup_puzzle(session, older.id)


@pytest.mark.asyncio
async def test_archive_list_filters_puzzle_type(client, session, today_utc) -> None:
    viewer = await create_user(session)
    headers = auth_header(viewer)
    assigned, = await _free_dates(session, today_utc - timedelta(days=1), 1)
    anagram = await create_puzzle(
        session,
        assigned=assigned,
        solution="TRACE",
        content={
            "scrambled_word": "ECRAT",
            "hint": "follow a path",
            "prompt": "Unscramble the letters",
        },
    )
    anagram.puzzle_type = PuzzleType.ANAGRAM
    await session.commit()

    filtered = await _archive(client, puzzle_type="anagram", limit=50, headers=headers)
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["items"]
    assert all(item["puzzle_type"] == "anagram" for item in body["items"])
    match = await _find_archive_item(
        client, str(anagram.id), puzzle_type="anagram", headers=headers
    )
    assert match["content"]["scrambled_word"] == "ECRAT"

    with pytest.raises(AssertionError):
        await _find_archive_item(client, str(anagram.id), puzzle_type="pattern", headers=headers)

    invalid = await _archive(client, puzzle_type="crossword", headers=headers)
    assert invalid.status_code == 422

    await cleanup_user(session, viewer.id)
    await cleanup_puzzle(session, anagram.id)


@pytest.mark.asyncio
async def test_archive_list_completion_is_per_user(client, session, today_utc) -> None:
    solved_day, incorrect_day = await _free_dates(session, today_utc - timedelta(days=1), 2)
    puzzle = await create_puzzle(session, assigned=solved_day, solution=9)
    incorrect = await create_puzzle(session, assigned=incorrect_day, solution=4)
    owner = await create_user(session)
    other = await create_user(session)
    session.add_all(
        [
            UserCompletion(
                user_id=owner.id,
                puzzle_id=puzzle.id,
                is_correct=True,
                score=80,
                time_taken_seconds=15,
                is_daily_official=False,
            ),
            UserCompletion(
                user_id=owner.id,
                puzzle_id=incorrect.id,
                is_correct=False,
                score=0,
                time_taken_seconds=20,
                is_daily_official=False,
            ),
        ]
    )
    await session.commit()

    async def item_for(puzzle_id, headers) -> dict:
        return await _find_archive_item(client, str(puzzle_id), headers=headers)

    anonymous = await client.get("/api/puzzles/archive")
    assert anonymous.status_code == 401

    stranger = await item_for(puzzle.id, auth_header(other))
    assert stranger["is_completed"] is False
    assert stranger["is_correct"] is None
    assert stranger["score"] is None

    completed = await item_for(puzzle.id, auth_header(owner))
    assert completed["is_completed"] is True
    assert completed["is_correct"] is True
    assert completed["score"] == 80
    _assert_public_item(completed)

    wrong = await item_for(incorrect.id, auth_header(owner))
    assert wrong["is_completed"] is True
    assert wrong["is_correct"] is False
    assert wrong["score"] == 0

    await cleanup_user(session, owner.id)
    await cleanup_user(session, other.id)
    await cleanup_puzzle(session, puzzle.id)
    await cleanup_puzzle(session, incorrect.id)
