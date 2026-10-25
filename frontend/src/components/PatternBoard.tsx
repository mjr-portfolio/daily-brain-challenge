import { useState } from 'react'
import type { PatternContent, ShapeColor, ShapeItem, ShapeName } from '@/types/puzzle.ts'

type PatternChoice = string | number | ShapeItem

type PatternBoardProps = {
  content: PatternContent
  disabled: boolean
  onSubmit: (answer: PatternChoice) => void
}

const SHAPE_FILL: Record<ShapeColor, string> = {
  red: '#f87171',
  blue: '#60a5fa',
  green: '#4ade80',
  purple: '#c084fc',
  yellow: '#facc15',
  orange: '#fb923c',
}

function ShapeIcon({
  shape,
  color,
  size,
}: {
  shape: ShapeName
  color: ShapeColor
  size: number
}) {
  const fill = SHAPE_FILL[color]
  const shared = { width: size, height: size, viewBox: '0 0 24 24', 'aria-hidden': true as const }
  if (shape === 'circle') {
    return (
      <svg {...shared}>
        <circle cx="12" cy="12" r="8" fill={fill} />
        <OrientationMark />
      </svg>
    )
  }
  if (shape === 'square') {
    return (
      <svg {...shared}>
        <rect x="4" y="4" width="16" height="16" rx="1.5" fill={fill} />
        <OrientationMark />
      </svg>
    )
  }
  if (shape === 'triangle') {
    return (
      <svg {...shared}>
        <polygon points="12,3 21,20 3,20" fill={fill} />
        <OrientationMark />
      </svg>
    )
  }
  if (shape === 'diamond') {
    return (
      <svg {...shared}>
        <polygon points="12,2 22,12 12,22 2,12" fill={fill} />
        <OrientationMark />
      </svg>
    )
  }
  if (shape === 'pentagon') {
    return (
      <svg {...shared}>
        <polygon points="12,3 20.6,9.2 17.3,19.3 6.7,19.3 3.4,9.2" fill={fill} />
        <OrientationMark />
      </svg>
    )
  }
  if (shape === 'hexagon') {
    return (
      <svg {...shared}>
        <polygon points="12,3.5 18.9,7.5 18.9,16.5 12,20.5 5.1,16.5 5.1,7.5" fill={fill} />
        <OrientationMark />
      </svg>
    )
  }
  return (
    <svg {...shared}>
      <polygon
        points="12,2 14.8,8.8 22,9.2 16.6,14 18.4,21.2 12,17.2 5.6,21.2 7.4,14 2,9.2 9.2,8.8"
        fill={fill}
      />
      <OrientationMark />
    </svg>
  )
}

function OrientationMark() {
  return <circle cx="12" cy="4.2" r="1.25" fill="#020617" />
}

function ShapeGlyph({ item, size = 22 }: { item: ShapeItem; size?: number }) {
  const count = item.count ?? 1
  const rotation = item.rotation ?? 0
  const iconSize = count > 2 ? 14 : size
  return (
    <span
      className="inline-flex items-center justify-center gap-0.5"
      style={{ transform: `rotate(${rotation}deg)` }}
    >
      {Array.from({ length: count }, (_, index) => (
        <ShapeIcon key={index} shape={item.shape} color={item.color} size={iconSize} />
      ))}
    </span>
  )
}

function isBlankCell(cell: PatternChoice | null): boolean {
  if (cell == null) return true
  return typeof cell === 'string' && ['null', 'none'].includes(cell.trim().toLowerCase())
}

function CellFace({ value, size = 22 }: { value: PatternChoice; size?: number }) {
  if (typeof value === 'object') return <ShapeGlyph item={value} size={size} />
  return <>{String(value)}</>
}

function choiceKey(choice: PatternChoice): string {
  return JSON.stringify(choice)
}

function choiceLabel(choice: PatternChoice): string {
  if (typeof choice !== 'object') return String(choice)
  const count = choice.count ?? 1
  const rotation = choice.rotation ?? 0
  const noun = count === 1 ? choice.shape : `${choice.shape}s`
  const turn = rotation ? `, rotated ${rotation} degrees` : ''
  return `${count} ${choice.color} ${noun}${turn}`
}

export function PatternBoard({ content, disabled, onSubmit }: PatternBoardProps) {
  const [selected, setSelected] = useState<PatternChoice | null>(null)
  const choices = content.choices ?? []
  const selectedKey = selected == null ? null : choiceKey(selected)
  const columns = Math.max(content.grid[0]?.length ?? 1, 1)

  return (
    <div className="space-y-5">
      <p className="text-center text-slate-200">{content.prompt}</p>
      <div
        className={`mx-auto grid gap-2 ${columns > 3 ? 'w-full max-w-sm' : 'max-w-xs'}`}
        style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
      >
        {content.grid.flatMap((row, rowIndex) =>
          row.map((cell, colIndex) => {
            const isBlank = isBlankCell(cell)
            const filled = isBlank ? selected : cell
            return (
              <div
                key={`${rowIndex}-${colIndex}`}
                className={`flex items-center justify-center rounded-lg text-xl font-semibold ${
                  columns > 3 ? 'h-14' : 'h-16'
                } ${
                  isBlank
                    ? 'border border-dashed border-amber-400/70 bg-slate-950 text-amber-200'
                    : 'bg-slate-800 text-white'
                }`}
              >
                {filled == null ? (
                  '?'
                ) : (
                  <CellFace value={filled} size={columns > 3 ? 32 : 22} />
                )}
              </div>
            )
          }),
        )}
      </div>
      {choices.length > 0 ? (
        <div className="flex flex-wrap justify-center gap-2">
          {choices.map((choice) => {
            const active = selectedKey === choiceKey(choice)
            return (
              <button
                key={choiceKey(choice)}
                type="button"
                aria-label={choiceLabel(choice)}
                disabled={disabled}
                onClick={() => setSelected(choice)}
                className={`flex min-w-14 items-center justify-center rounded-lg border px-3 py-2 text-sm font-medium ${
                  active
                    ? 'border-amber-300 bg-amber-400 text-slate-950'
                    : 'border-slate-600 bg-slate-800 text-white hover:border-amber-400'
                }`}
              >
                <CellFace value={choice} />
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
          className="rounded-full border border-amber-500 bg-amber-400 px-5 py-2 font-medium text-slate-950 hover:border-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Submit
        </button>
      </div>
    </div>
  )
}
