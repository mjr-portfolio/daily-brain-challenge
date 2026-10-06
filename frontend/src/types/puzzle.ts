export type CellValue = string | number | null

export type PatternContent = {
  grid: CellValue[][]
  prompt: string
  choices: Array<string | number> | null
}

export type PatternPuzzle = {
  id: string
  puzzle_type: 'pattern'
  assigned_date: string | null
  created_at: string
  content: PatternContent
}

export type AnagramContent = {
  scrambled_word: string
  hint?: string | null
  prompt?: string | null
}

export type AnagramPuzzle = {
  id: string
  puzzle_type: 'anagram'
  assigned_date: string | null
  created_at: string
  content: AnagramContent
}

export type UnsupportedPuzzle = {
  id: string
  puzzle_type: string
  assigned_date: string | null
  created_at: string
  content: Record<string, unknown>
}

export type Puzzle = PatternPuzzle | AnagramPuzzle | UnsupportedPuzzle

export function isPatternPuzzle(puzzle: Puzzle): puzzle is PatternPuzzle {
  return puzzle.puzzle_type === 'pattern'
}

export function isAnagramPuzzle(puzzle: Puzzle): puzzle is AnagramPuzzle {
  return puzzle.puzzle_type === 'anagram'
}
