# Product Requirements Document (PRD) - Daily Challenge App

## Project Overview
A daily brain-training application serving one synchronized daily puzzle to all users globally.
Supports guest play with immediate feedback, account registration for global percentile tracking, and an archive catch-up engine for past uncompleted puzzles.

---

## Phase 1: Core Database & Backend Foundation
- [ ] Set up FastAPI with SQLAlchemy (async) and PostgreSQL connection.
- [ ] Create database models: `User`, `Puzzle`, and `UserCompletion`.
- [ ] Ensure `user_completions` schema supports optional/nullable guest tracking or distinct submission modes.
- [ ] Write database migrations using Alembic.
- [ ] Create seed script for sample Pattern Recognition puzzles.

---

## Phase 2: API Endpoints (Guest & Auth Modes)
- [ ] Implement `GET /api/puzzles/daily` (publicly accessible; returns today's puzzle without solution keys).
- [ ] Implement `POST /api/puzzles/{id}/submit` with **optional authentication**:
  - **Authenticated Users:** Validates answer, records completion in `user_completions`, and returns time + global percentile ranking.
  - **Guest Users:** Validates answer and returns `is_correct` status + completion time without percentile/DB logging.
- [ ] Implement `GET /api/puzzles/archive/next` (requires auth; fetches next uncompleted historical puzzle for user).

---

## Phase 3: Frontend UI, Guest Flow & Game Engines
- [ ] Set up React + TypeScript + Tailwind CSS structure.
- [ ] Build `<PuzzleContainer />` and `<PatternBoard />` for pattern recognition gameplay.
- [ ] Implement game timer and submission handler (supports both guest state and auth token headers).
- [ ] Implement `localStorage` caching for guest completion status and current daily streak.
- [ ] Build Post-Submission Modal:
  - **Guest View:** Displays correctness, completion time, and an upsell banner (*"Sign up to see your global percentile rank and unlock past puzzles!"*).
  - **Auth View:** Displays full global percentile ranking and catch-up archive launcher.
- [ ] Build Account Migration flow: Transfer `localStorage` guest stats to database upon account creation.
