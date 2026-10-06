import { useEffect, useMemo, useState } from 'react'
import type { AnagramContent } from '@/types/puzzle.ts'

const DEFAULT_PROMPT = 'Unscramble the letters to reveal the target word'

type Tile = {
  id: string
  letter: string
}

type AnagramBoardProps = {
  content: AnagramContent
  disabled: boolean
  onSubmit: (answer: string) => void
}

function buildTiles(scrambledWord: string): Tile[] {
  return scrambledWord
    .replace(/\s/g, '')
    .split('')
    .map((letter, index) => ({ id: `${index}-${letter}`, letter }))
}

function isTypingTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    (target instanceof HTMLElement && target.isContentEditable)
  )
}

export function AnagramBoard({ content, disabled, onSubmit }: AnagramBoardProps) {
  const tiles = useMemo(() => buildTiles(content.scrambled_word), [content.scrambled_word])
  const [slots, setSlots] = useState<(string | null)[]>(() => tiles.map(() => null))

  useEffect(() => {
    if (disabled) return

    function onKeyDown(event: KeyboardEvent) {
      if (event.metaKey || event.ctrlKey || event.altKey || isTypingTarget(event.target)) return

      if (event.key === 'Backspace') {
        event.preventDefault()
        setSlots((current) => {
          const next = [...current]
          for (let index = next.length - 1; index >= 0; index -= 1) {
            if (next[index] != null) {
              next[index] = null
              return next
            }
          }
          return current
        })
        return
      }

      if (event.key.length !== 1 || !/\p{L}/u.test(event.key)) return
      event.preventDefault()
      const wanted = event.key.toLocaleLowerCase()
      setSlots((current) => {
        const used = new Set(current.filter((id): id is string => id != null))
        const tile = tiles.find(
          (item) => !used.has(item.id) && item.letter.toLocaleLowerCase() === wanted,
        )
        if (!tile) return current
        const nextIndex = current.indexOf(null)
        if (nextIndex === -1) return current
        const next = [...current]
        next[nextIndex] = tile.id
        return next
      })
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [disabled, tiles])

  const placed = new Set(slots.filter((id): id is string => id != null))
  const bank = tiles.filter((tile) => !placed.has(tile.id))
  const answer = slots
    .map((id) => tiles.find((tile) => tile.id === id)?.letter ?? '')
    .join('')
  const complete = tiles.length > 0 && slots.every((id) => id != null)
  const prompt = content.prompt?.trim() ? content.prompt : DEFAULT_PROMPT
  const hint = content.hint?.trim() ? content.hint : null

  function placeTile(tileId: string) {
    if (disabled) return
    setSlots((current) => {
      if (current.includes(tileId)) return current
      const nextIndex = current.indexOf(null)
      if (nextIndex === -1) return current
      const next = [...current]
      next[nextIndex] = tileId
      return next
    })
  }

  function clearSlot(index: number) {
    if (disabled) return
    setSlots((current) => {
      if (current[index] == null) return current
      const next = [...current]
      next[index] = null
      return next
    })
  }

  function clearAll() {
    if (disabled) return
    setSlots(tiles.map(() => null))
  }

  return (
    <div className="space-y-5">
      <p className="text-center text-slate-200">{prompt}</p>
      {hint ? <p className="text-center text-sm text-slate-400">{hint}</p> : null}
      <div className="flex flex-wrap justify-center gap-2" aria-label="Answer">
        {slots.map((tileId, index) => {
          const letter =
            tileId == null ? null : (tiles.find((tile) => tile.id === tileId)?.letter ?? null)
          if (letter == null) {
            return (
              <div
                key={`slot-${index}`}
                role="img"
                aria-label={`Empty slot ${index + 1}`}
                className="flex h-12 min-h-11 w-12 min-w-11 items-center justify-center rounded-lg border border-dashed border-amber-400/70 bg-slate-950"
              />
            )
          }
          return (
            <button
              key={`slot-${index}`}
              type="button"
              disabled={disabled}
              onClick={() => clearSlot(index)}
              aria-label={`Slot ${index + 1}, letter ${letter}. Tap to return it to the letter bank.`}
              className="flex h-12 min-h-11 w-12 min-w-11 items-center justify-center rounded-lg border border-amber-300 bg-amber-400 text-lg font-semibold text-slate-950"
            >
              {letter}
            </button>
          )
        })}
      </div>
      <div className="flex min-h-12 flex-wrap justify-center gap-2" aria-label="Letter bank">
        {bank.map((tile) => (
          <button
            key={tile.id}
            type="button"
            disabled={disabled}
            onClick={() => placeTile(tile.id)}
            aria-label={`Letter ${tile.letter}`}
            className="flex h-12 min-h-11 w-12 min-w-11 items-center justify-center rounded-lg border border-slate-600 bg-slate-800 text-lg font-semibold text-white hover:border-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {tile.letter}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap justify-center gap-3">
        <button
          type="button"
          disabled={disabled || placed.size === 0}
          onClick={clearAll}
          className="rounded-full border border-slate-600 bg-slate-800 px-5 py-2 font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          Clear
        </button>
        <button
          type="button"
          disabled={disabled || !complete}
          onClick={() => onSubmit(answer)}
          className="rounded-full bg-amber-400 px-5 py-2 font-medium text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Submit Answer
        </button>
      </div>
    </div>
  )
}
