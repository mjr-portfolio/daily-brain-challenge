export function originFromServer(startedAtIso: string, serverNowIso: string): number {
  const offset = Date.parse(serverNowIso) - Date.now()
  return Date.parse(startedAtIso) - offset
}

export function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}
