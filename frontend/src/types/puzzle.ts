export type ShapeName =
  | 'circle'
  | 'triangle'
  | 'square'
  | 'diamond'
  | 'star'
  | 'pentagon'
  | 'hexagon'
export type ShapeColor = 'red' | 'blue' | 'green' | 'purple' | 'yellow' | 'orange'

export type ShapeItem = {
  shape: ShapeName
  color: ShapeColor
  rotation?: number
  count?: number
}

export type CellValue = string | number | ShapeItem | null

export type PatternContent = {
  grid: CellValue[][]
  prompt: string
  choices: Array<string | number | ShapeItem> | null
}

export type PatternPuzzle = {
  id: string
  puzzle_type: 'pattern'
  assigned_date: string | null
  created_at: string
  content: PatternContent
  is_completed?: boolean
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
  is_completed?: boolean
}

export type NewsQuizContent = {
  question: string
  options: string[]
  source_headline?: string | null
  hint?: string | null
}

export type NewsQuizPuzzle = {
  id: string
  puzzle_type: 'news_quiz'
  assigned_date: string | null
  created_at: string
  content: NewsQuizContent
  is_completed?: boolean
}

export type UnsupportedPuzzle = {
  id: string
  puzzle_type: string
  assigned_date: string | null
  created_at: string
  content: Record<string, unknown>
  is_completed?: boolean
}

export type Puzzle = PatternPuzzle | AnagramPuzzle | NewsQuizPuzzle | UnsupportedPuzzle

export type ArchivePuzzleType = 'pattern' | 'anagram' | 'news_quiz'

export type ArchivePuzzleItem = (PatternPuzzle | AnagramPuzzle | NewsQuizPuzzle) & {
  assigned_date: string
  is_completed: boolean
  is_correct: boolean | null
  score: number | null
}

export type DailyPreview = {
  id: string
  puzzle_type: ArchivePuzzleType
  assigned_date: string
  is_completed: boolean
  started_at: string | null
}

export type DailySession = {
  puzzle: Puzzle
  started_at: string | null
  server_now: string
}

export type ArchivePage = {
  items: ArchivePuzzleItem[]
  page: number
  limit: number
  total: number
}

export function isPatternPuzzle(puzzle: Puzzle): puzzle is PatternPuzzle {
  return puzzle.puzzle_type === 'pattern'
}

export function isAnagramPuzzle(puzzle: Puzzle): puzzle is AnagramPuzzle {
  return puzzle.puzzle_type === 'anagram'
}

export function isNewsQuizPuzzle(puzzle: Puzzle): puzzle is NewsQuizPuzzle {
  return puzzle.puzzle_type === 'news_quiz'
}
