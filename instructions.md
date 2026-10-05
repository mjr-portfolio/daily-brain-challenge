# Instructions & Architecture Rules

## 1. Project Overview
A daily brain-training application serving one synchronized daily puzzle to all users globally.
Includes an archive catch-up mode allowing users to play past uncompleted puzzles, and a daily performance percentile response upon completion.

## 2. Core Technical Constraints & Architecture

### Server-Side Ground Truth
- Solution verification, score calculation, and daily puzzle assignment MUST happen strictly server-side.
- The client receives puzzle structure and clues via GET endpoints, but NEVER the answer payload.

### Single-Table Polymorphic Puzzle Storage
- All puzzles (Pattern Recognition, Anagrams, News Quiz) are stored in a unified `puzzles` table using a `puzzle_type` discriminator and JSONB `content`.
- Daily puzzles are assigned via a unique `assigned_date` column (UTC).

### Catch-Up Engine Logic
- Requires authentication (registered users only).
- Fetching historical puzzles checks for past assigned puzzles (`assigned_date < TODAY`) NOT present in the user's `user_completions` records.

### Global Performance Percentile
- Completions track `time_taken_seconds` and `is_daily_official` (played on release day vs catch-up).
- Upon submission, the API returns the user's percentile rank compared to all official daily completers.

### Guest Mode & Account Funnel
- `GET /api/puzzles/daily` is completely public.
- `POST /api/puzzles/{id}/submit` handles optional authentication:
  - Unauthenticated (Guest): Validates solution server-side, returns correctness + time.
  - Authenticated: Validates solution, logs to `user_completions`, and returns time + global percentile rank.
- Guest stats (daily completion & streak) are preserved in `localStorage` on the frontend and can be migrated upon registration.

## 3. Database Schema Blueprint
- `users`: id, email, created_at
- `puzzles`: id, puzzle_type, assigned_date (nullable, unique), content (JSONB), solution_hash, created_at
- `user_completions`: id, user_id (nullable, FK to users), puzzle_id (FK to puzzles), is_correct, score, time_taken_seconds, is_daily_official, completed_at