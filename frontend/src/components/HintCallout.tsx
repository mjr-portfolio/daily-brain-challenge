export function HintCallout({ hint }: { hint: string }) {
  return (
    <aside
      className="rounded-xl border border-amber-400/50 bg-amber-400/10 px-4 py-3 text-center"
      aria-label="Hint"
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-amber-300">Hint</p>
      <p className="mt-1 text-sm font-medium leading-relaxed text-amber-50">{hint}</p>
    </aside>
  )
}
