import { useCallback, useEffect, useState } from 'react'

function elapsed(startedAtMs: number): number {
  return Math.max(0, Math.floor((Date.now() - startedAtMs) / 1000))
}

export function useTimer(running: boolean, startedAtMs: number) {
  const [seconds, setSeconds] = useState(() => elapsed(startedAtMs))

  useEffect(() => {
    if (!running) return
    const tick = () => setSeconds(elapsed(startedAtMs))
    tick()
    const id = window.setInterval(tick, 200)
    return () => window.clearInterval(id)
  }, [running, startedAtMs])

  const stop = useCallback(() => {
    const next = elapsed(startedAtMs)
    setSeconds(next)
    return next
  }, [startedAtMs])

  return { seconds, stop }
}
