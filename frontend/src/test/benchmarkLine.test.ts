import { describe, expect, it } from 'vitest'
import { benchmarkLine } from '@/components/ArchiveCompletionModal.tsx'
import type { ArchiveBenchmark } from '@/types/leaderboard.ts'

function benchmark(overrides: Partial<ArchiveBenchmark> = {}): ArchiveBenchmark {
  return {
    puzzle_id: 'puzzle-1',
    assigned_date: '2026-10-20',
    solver_count: 1,
    fastest_completion_time_seconds: 2,
    median_completion_time_seconds: 2,
    average_score: 100,
    viewer: {
      time_taken_seconds: 2,
      score: 80,
      is_correct: true,
      faster_than_percent: 0,
    },
    ...overrides,
  }
}

describe('archive benchmark copy', () => {
  it('treats a matching fastest time as a tie', () => {
    expect(benchmarkLine(benchmark())).toBe('Matched the fastest time on this day')
  })

  it('says when the archive time was slower than every live solver', () => {
    expect(
      benchmarkLine(
        benchmark({
          viewer: {
            time_taken_seconds: 90,
            score: 1,
            is_correct: true,
            faster_than_percent: 0,
          },
        }),
      ),
    ).toBe('Slower than the solvers on this day')
  })

  it('keeps a faster-than line when the player beat someone', () => {
    expect(
      benchmarkLine(
        benchmark({
          fastest_completion_time_seconds: 40,
          viewer: {
            time_taken_seconds: 20,
            score: 90,
            is_correct: true,
            faster_than_percent: 78,
          },
        }),
      ),
    ).toBe('Faster than 78% of solvers on this day')
  })
})