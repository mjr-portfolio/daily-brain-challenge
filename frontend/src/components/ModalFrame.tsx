import type { ReactNode } from 'react'

export function ModalFrame({
  title,
  subtitle,
  onClose,
  children,
  wide = false,
}: {
  title: string
  subtitle?: ReactNode
  onClose: () => void
  children: ReactNode
  wide?: boolean
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
        className={`max-h-[90svh] w-full overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 shadow-xl ${
          wide ? 'max-w-lg' : 'max-w-md'
        }`}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-slate-800 px-5 py-4">
          <div className="min-w-0">
            <h2 id="modal-title" className="text-xl font-semibold text-white">
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
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  )
}
