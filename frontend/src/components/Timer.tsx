import { formatTime } from '@/utils/time.ts'

export function Timer({ seconds }: { seconds: number }) {
  return (
    <p className="font-mono text-2xl tracking-widest text-amber-300" aria-live="polite">
      {formatTime(seconds)}
    </p>
  )
}
