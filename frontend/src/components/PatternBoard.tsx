import { useState } from 'react'
import type { PatternContent } from '@/types/puzzle.ts'

type PatternBoardProps = {
  content: PatternContent
  disabled: boolean
  onSubmit: (answer: string | number) => void
}

export function PatternBoard({ content, disabled, onSubmit }: PatternBoardProps) {
  const [selected, setSelected] = useState<string | number | null>(null)
  const choices = content.choices ?? []

  return (
    <div className="space-y-5">
      <p className="text-center text-slate-200">{content.prompt}</p>
      <div className="mx-auto grid max-w-xs grid-cols-3 gap-2">
        {content.grid.flatMap((row, rowIndex) =>
          row.map((cell, colIndex) => {
            const filled = cell == null ? selected : cell
            const isBlank = cell == null
            return (
              <div
                key={`${rowIndex}-${colIndex}`}
                className={`flex h-16 items-center justify-center rounded-lg text-xl font-semibold ${
                  isBlank
                    ? 'border border-dashed border-amber-400/70 bg-slate-950 text-amber-200'
                    : 'bg-slate-800 text-white'
                }`}
              >
                {filled == null ? '?' : String(filled)}
              </div>
            )
          }),
        )}
      </div>
      {choices.length > 0 ? (
        <div className="flex flex-wrap justify-center gap-2">
          {choices.map((choice) => {
            const active = selected === choice
            return (
              <button
                key={String(choice)}
                type="button"
                disabled={disabled}
                onClick={() => setSelected(choice)}
                className={`min-w-14 rounded-lg border px-3 py-2 text-sm font-medium ${
                  active
                    ? 'border-amber-300 bg-amber-400 text-slate-950'
                    : 'border-slate-600 bg-slate-800 text-white hover:border-amber-400'
                }`}
              >
                {String(choice)}
              </button>
            )
          })}
        </div>
      ) : null}
      <div className="text-center">
        <button
          type="button"
          disabled={disabled || selected == null}
          onClick={() => {
            if (selected != null) onSubmit(selected)
          }}
          className="rounded-full bg-amber-400 px-5 py-2 font-medium text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Submit
        </button>
      </div>
    </div>
  )
}
