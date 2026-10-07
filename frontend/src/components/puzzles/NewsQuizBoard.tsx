import { useState } from 'react'
import type { NewsQuizContent } from '@/types/puzzle.ts'

type NewsQuizBoardProps = {
  content: NewsQuizContent
  disabled: boolean
  onSubmit: (answer: string) => void
}

export function NewsQuizBoard({ content, disabled, onSubmit }: NewsQuizBoardProps) {
  const [selected, setSelected] = useState<string | null>(null)
  const headline = content.source_headline?.trim() ? content.source_headline : null
  const hint = content.hint?.trim() ? content.hint : null

  return (
    <div className="space-y-5">
      {headline ? (
        <blockquote className="rounded-r-lg border-l-4 border-amber-400 bg-slate-950/80 px-4 py-3 text-left text-sm italic text-slate-300">
          {headline}
        </blockquote>
      ) : null}
      <p className="text-center text-lg font-medium text-slate-100">{content.question}</p>
      {hint ? <p className="text-center text-sm text-slate-400">{hint}</p> : null}
      <div className="flex flex-col gap-2" role="listbox" aria-label="Answer options">
        {content.options.map((option) => {
          const active = selected === option
          return (
            <button
              key={option}
              type="button"
              role="option"
              aria-selected={active}
              disabled={disabled}
              onClick={() => setSelected(option)}
              className={`min-h-11 w-full rounded-lg border px-4 py-3 text-left text-sm font-medium transition-colors ${
                active
                  ? 'border-amber-300 bg-amber-400 text-slate-950'
                  : 'border-slate-600 bg-slate-800 text-white hover:border-amber-400'
              } disabled:cursor-not-allowed disabled:opacity-40`}
            >
              {option}
            </button>
          )
        })}
      </div>
      <div className="text-center">
        <button
          type="button"
          disabled={disabled || selected == null}
          onClick={() => {
            if (selected != null) onSubmit(selected)
          }}
          className="rounded-full bg-amber-400 px-5 py-2 font-medium text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Submit Answer
        </button>
      </div>
    </div>
  )
}
