import type { ReactNode } from 'react'

const SPARKS = [
  { left: '12%', top: '18%', delay: '0ms' },
  { left: '28%', top: '10%', delay: '80ms' },
  { left: '48%', top: '14%', delay: '40ms' },
  { left: '68%', top: '9%', delay: '120ms' },
  { left: '84%', top: '16%', delay: '60ms' },
  { left: '18%', top: '32%', delay: '160ms' },
  { left: '78%', top: '30%', delay: '100ms' },
]

export function ModalFrame({
  title,
  subtitle,
  onClose,
  children,
  wide = false,
  celebrate = false,
}: {
  title: string
  subtitle?: ReactNode
  onClose: () => void
  children: ReactNode
  wide?: boolean
  celebrate?: boolean
}) {
  return (
    <div
      className="fixed inset-0 z-40 flex items-start justify-center bg-black/60 px-4 pb-4 pt-20"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className={`relative max-h-[90svh] w-full overflow-y-auto rounded-2xl border bg-slate-900 shadow-xl ${
          celebrate
            ? 'celebrate-modal border-amber-400/70'
            : 'border-slate-700'
        } ${wide ? 'max-w-lg' : 'max-w-md'}`}
        onClick={(event) => event.stopPropagation()}
      >
        {celebrate
          ? SPARKS.map((spark) => (
              <span
                key={`${spark.left}-${spark.top}`}
                className="celebrate-spark"
                style={{ left: spark.left, top: spark.top, animationDelay: spark.delay }}
                aria-hidden="true"
              />
            ))
          : null}
        <div className="relative flex items-start justify-between gap-3 border-b border-slate-800 px-5 py-4">
          <div className="min-w-0">
            <h2
              id="modal-title"
              className={`text-xl font-semibold ${
                celebrate ? 'text-amber-200' : 'text-white'
              }`}
            >
              {title}
            </h2>
            {subtitle ? <div className="mt-1 text-sm text-slate-400">{subtitle}</div> : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-full px-3 py-1 text-sm text-slate-400 hover:text-white"
          >
            Close
          </button>
        </div>
        <div className="relative px-5 py-4">{children}</div>
      </div>
    </div>
  )
}
