import { useEffect, useId, useRef, useState } from 'react'

export function UserMenuDropdown({
  email,
  displayName,
  streak,
  onOpenStats,
  onOpenSettings,
  onLogout,
  busy = false,
}: {
  email: string | null
  displayName: string | null
  streak: number
  onOpenStats: () => void
  onOpenSettings: () => void
  onLogout: () => void
  busy?: boolean
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const firstItemRef = useRef<HTMLButtonElement>(null)
  const menuId = useId()
  const label = displayName || email || 'Account'

  useEffect(() => {
    if (busy) setOpen(false)
  }, [busy])

  useEffect(() => {
    if (!open) return
    firstItemRef.current?.focus()
    function onPointer(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    function onKey(event: KeyboardEvent) {
      if (event.key !== 'Escape') return
      setOpen(false)
      triggerRef.current?.focus()
    }
    document.addEventListener('mousedown', onPointer)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onPointer)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  function choose(action: () => void) {
    setOpen(false)
    action()
  }

  return (
    <div className="relative" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={busy ? 'Logging out' : `Account, ${label}`}
        aria-busy={busy}
        disabled={busy}
        onClick={() => setOpen((current) => !current)}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-700 text-slate-200 hover:border-amber-400 disabled:cursor-wait"
      >
        {busy ? <Spinner /> : <UserIcon />}
      </button>
      {open && !busy ? (
        <div
          id={menuId}
          role="menu"
          aria-label="Account"
          className="absolute right-0 z-30 mt-2 w-64 rounded-xl border border-slate-700 bg-slate-900 py-2 shadow-xl"
        >
          <div className="border-b border-slate-800 px-3 pb-2">
            <p className="truncate text-sm font-medium text-white">{label}</p>
            {displayName && email ? (
              <p className="truncate text-xs text-slate-400">{email}</p>
            ) : null}
            <p className="mt-1 flex items-center gap-1 text-sm text-amber-300">
              <FlameIcon />
              <span>Streak {streak}</span>
            </p>
          </div>
          <button
            ref={firstItemRef}
            type="button"
            role="menuitem"
            onClick={() => choose(onOpenStats)}
            className="block w-full px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800"
          >
            Stats Dashboard
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => choose(onOpenSettings)}
            className="block w-full px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800"
          >
            Settings & Preferences
          </button>
          <div className="my-1 border-t border-slate-800" role="separator" />
          <button
            type="button"
            role="menuitem"
            onClick={() => choose(onLogout)}
            className="block w-full px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800"
          >
            Log out
          </button>
        </div>
      ) : null}
    </div>
  )
}

function Spinner() {
  return (
    <span
      className="h-4 w-4 animate-spin rounded-full border-2 border-slate-500 border-t-amber-300"
      aria-hidden="true"
    />
  )
}

function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden="true">
      <path d="M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-4.4 0-8 2.2-8 5v1h16v-1c0-2.8-3.6-5-8-5z" />
    </svg>
  )
}

function FlameIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-amber-400" aria-hidden="true">
      <path d="M12 2s1.5 3 1.5 5.2c0 1.3-.7 2.2-1.5 2.8.8-.2 2.2-.2 3.2.8 1.2 1.2 1.8 2.8 1.8 4.7A6.5 6.5 0 0 1 10.5 22 6.5 6.5 0 0 1 7 12.6c0-1.6.6-3 1.6-4.2C10 6.6 12 2 12 2z" />
    </svg>
  )
}
