from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models import User, UserCompletion
from tests.conftest import (
    auth_header,
    cleanup_puzzle,
    cleanup_user,
    create_puzzle,
    create_user,
    replace_daily_puzzle,
)

PASSWORD = "password1"


def _email() -> str:
    return f"ada-{uuid4().hex}@example.com"


def _cookie(client, name: str) -> str | None:
    for cookie in client.cookies.jar:
        if cookie.name == name:
            return cookie.value
    return None


def _use_refresh(client, value: str) -> None:
    client.cookies.clear()
    # httpx treats a dotless host as host.local when it stores Set-Cookie.
    client.cookies.set("refresh_token", value, domain="test.local", path="/api/auth/refresh")


async def _register(client, email: str, *, display_name: str | None = None, password: str = PASSWORD):
    payload: dict[str, str] = {
        "email": email,
        "password": password,
        "display_name": display_name or f"Ada_{uuid4().hex[:6]}",
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "access_token" not in body
    assert "refresh_token" not in body
    issued = " ".join(response.headers.get_list("set-cookie")).lower()
    assert "httponly" in issued
    assert _cookie(client, "access_token")
    assert _cookie(client, "refresh_token")
    return body


async def _user_id(session, email: str):
    return await session.scalar(select(User.id).where(User.email == email))


@pytest.mark.asyncio
async def test_register_login_refresh_and_logout(client, session) -> None:
    email = _email()
    created = await _register(client, email, display_name="Ada_Lovelace")
    assert created["email"] == email

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["display_name"] == "Ada_Lovelace"
    assert me.json()["preferences"]["theme"] == "dark"

    wrong = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "not-the-password"},
    )
    assert wrong.status_code == 401

    missing = await client.post(
        "/api/auth/login",
        json={"email": _email(), "password": PASSWORD},
    )
    assert missing.status_code == 401

    signed_in = await client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert signed_in.status_code == 200
    assert "refresh_token" not in signed_in.json()
    first_refresh = _cookie(client, "refresh_token")
    assert first_refresh

    rotated = await client.post("/api/auth/refresh")
    assert rotated.status_code == 200
    assert "access_token" not in rotated.json()
    next_refresh = _cookie(client, "refresh_token")
    assert next_refresh and next_refresh != first_refresh

    _use_refresh(client, first_refresh)
    reused = await client.post("/api/auth/refresh")
    assert reused.status_code == 401

    _use_refresh(client, next_refresh)
    still_valid = await client.post("/api/auth/refresh")
    assert still_valid.status_code == 200
    current_refresh = _cookie(client, "refresh_token")
    assert current_refresh

    logged_out = await client.post("/api/auth/logout")
    assert logged_out.status_code == 204
    _use_refresh(client, current_refresh)
    revoked = await client.post("/api/auth/refresh")
    assert revoked.status_code == 401

    duplicate = await client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Ada_Lovelace"},
    )
    assert duplicate.status_code == 409

    removed = await client.post("/api/auth/token", json={"email": email})
    assert removed.status_code == 404

    user_id = await _user_id(session, email)
    assert user_id is not None
    await cleanup_user(session, user_id)


@pytest.mark.asyncio
async def test_register_requires_a_display_name(client) -> None:
    email = _email()
    missing = await client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD},
    )
    assert missing.status_code == 422

    blank = await client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": " "},
    )
    assert blank.status_code == 422

    spaced = await client.post(
        "/api/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "Ada Lovelace"},
    )
    assert spaced.status_code == 422


@pytest.mark.asyncio
async def test_claim_sets_a_password_once(client, session) -> None:
    email = _email()
    legacy = await create_user(session, email=email)
    assert legacy.password_hash is None

    denied = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert denied.status_code == 401

    claimed = await _register(client, email, display_name="Legacy_Ada")
    assert claimed["email"] == email
    assert claimed["display_name"] == "Legacy_Ada"

    again = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "password2", "display_name": "Legacy_Ada"},
    )
    assert again.status_code == 409

    signed_in = await client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert signed_in.status_code == 200
    await cleanup_user(session, legacy.id)


@pytest.mark.asyncio
async def test_profile_updates_validate_password_and_handle(client, session) -> None:
    email = _email()
    await _register(client, email, display_name="Ada")
    other_email = _email()
    await _register(client, other_email, display_name="Bea")
    signed_in = await client.post(
        "/api/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert signed_in.status_code == 200

    invalid = await client.patch(
        "/api/users/me",
        json={"display_name": "ada@example.com"},
    )
    assert invalid.status_code == 422

    cleared = await client.patch("/api/users/me", json={"display_name": None})
    assert cleared.status_code == 422
    assert (await client.get("/api/auth/me")).json()["display_name"] == "Ada"

    taken = await client.patch(
        "/api/users/me",
        json={"display_name": "bea"},
    )
    assert taken.status_code == 409

    renamed = await client.patch(
        "/api/users/me",
        json={"display_name": "Ada_L"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["display_name"] == "Ada_L"
    assert "access_token" not in renamed.json()

    missing_password = await client.patch(
        "/api/users/me",
        json={"email": _email()},
    )
    assert missing_password.status_code == 422

    bad_theme = await client.patch(
        "/api/users/me",
        json={"theme": "blue"},
    )
    assert bad_theme.status_code == 422

    themed = await client.patch(
        "/api/users/me",
        json={"theme": "light"},
    )
    assert themed.status_code == 200
    assert themed.json()["preferences"]["theme"] == "light"

    previous_refresh = _cookie(client, "refresh_token")
    assert previous_refresh
    changed = await client.patch(
        "/api/users/me",
        json={"current_password": PASSWORD, "new_password": "password2"},
    )
    assert changed.status_code == 200
    assert "access_token" not in changed.json()
    assert _cookie(client, "refresh_token") != previous_refresh

    _use_refresh(client, previous_refresh)
    old_refresh = await client.post("/api/auth/refresh")
    assert old_refresh.status_code == 401

    restored = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "password2"},
    )
    assert restored.status_code == 200
    next_email = _email()
    moved = await client.patch(
        "/api/users/me",
        json={"email": next_email, "current_password": "password2"},
    )
    assert moved.status_code == 200
    assert moved.json()["email"] == next_email

    old_login = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "password2"},
    )
    assert old_login.status_code == 401
    new_login = await client.post(
        "/api/auth/login",
        json={"email": next_email, "password": "password2"},
    )
    assert new_login.status_code == 200

    for address in (next_email, other_email):
        user_id = await _user_id(session, address)
        if user_id is not None:
            await cleanup_user(session, user_id)


@pytest.mark.asyncio
async def test_delete_account_requires_password(client, session) -> None:
    email = _email()
    await _register(client, email)

    rejected = await client.request(
        "DELETE",
        "/api/users/me",
        json={"password": "nope"},
    )
    assert rejected.status_code == 401
    still_there = await client.get("/api/auth/me")
    assert still_there.status_code == 200

    deleted = await client.request(
        "DELETE",
        "/api/users/me",
        json={"password": PASSWORD},
    )
    assert deleted.status_code == 204
    gone = await client.get("/api/auth/me")
    assert gone.status_code == 401
    assert await _user_id(session, email) is None


@pytest.mark.asyncio
async def test_replaying_a_completion_does_not_duplicate_or_bump_streak(
    client, session, today_utc
) -> None:
    user = await create_user(session)
    user.streak_count = 5
    user.streak_date = today_utc
    user.best_streak = 5
    await session.commit()
    puzzle = await replace_daily_puzzle(session, today_utc, solution=9)
    headers = auth_header(user)
    payload = {"answer": 9, "time_taken_seconds": 20}

    first = await client.post(f"/api/puzzles/{puzzle.id}/submit", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["streak"] == 5

    second = await client.post(f"/api/puzzles/{puzzle.id}/submit", json=payload, headers=headers)
    assert second.status_code == 409

    await session.refresh(user)
    assert user.streak_count == 5
    stored = await session.scalar(
        select(func.count())
        .select_from(UserCompletion)
        .where(UserCompletion.user_id == user.id, UserCompletion.puzzle_id == puzzle.id)
    )
    assert stored == 1

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, puzzle.id)


@pytest.mark.asyncio
async def test_replaying_an_older_puzzle_stores_one_row(client, session, today_utc) -> None:
    user = await create_user(session)
    user.streak_count = 4
    user.streak_date = today_utc - timedelta(days=1)
    user.best_streak = 4
    await session.commit()
    puzzle = await create_puzzle(session, assigned=today_utc - timedelta(days=10), solution=9)
    headers = auth_header(user)
    payload = {"answer": 9, "time_taken_seconds": 30}

    first = await client.post(f"/api/puzzles/{puzzle.id}/submit", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["streak"] == 4

    second = await client.post(f"/api/puzzles/{puzzle.id}/submit", json=payload, headers=headers)
    assert second.status_code == 409

    await session.refresh(user)
    assert user.streak_count == 4
    stored = await session.scalar(
        select(func.count())
        .select_from(UserCompletion)
        .where(UserCompletion.user_id == user.id, UserCompletion.puzzle_id == puzzle.id)
    )
    assert stored == 1

    await cleanup_user(session, user.id)
    await cleanup_puzzle(session, puzzle.id)


@pytest.mark.asyncio
async def test_cookie_writes_reject_a_foreign_origin(client) -> None:
    blocked = await client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert blocked.status_code == 403

    allowed = await client.post(
        "/api/auth/login",
        json={"email": "ada@example.com", "password": PASSWORD},
        headers={"Origin": "http://localhost:5173"},
    )
    assert allowed.status_code == 401
