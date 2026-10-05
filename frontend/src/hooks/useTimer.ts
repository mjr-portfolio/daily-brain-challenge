import { useCallback, useEffect, useRef, useState } from 'react'

export function useTimer(running: boolean) {
  const [seconds, setSeconds] = useState(0)
  const startRef = useRef<number | null>(null)
  const secondsRef = useRef(0)

  useEffect(() => {
    if (!running) return

    const origin = Date.now() - secondsRef.current * 1000
    startRef.current = origin
    const id = window.setInterval(() => {
      const next = Math.floor((Date.now() - origin) / 1000)
      secondsRef.current = next
      setSeconds(next)
    }, 200)

    return () => window.clearInterval(id)
  }, [running])

  const stop = useCallback(() => {
    if (startRef.current != null) {
      const next = Math.floor((Date.now() - startRef.current) / 1000)
      secondsRef.current = next
      setSeconds(next)
    }
    return secondsRef.current
  }, [])

  return { seconds, stop }
}
