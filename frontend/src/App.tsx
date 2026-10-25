import { useCallback, useEffect, useState } from 'react'
import { Route, Routes, useNavigate } from 'react-router-dom'
import { ArchiveModal } from '@/components/ArchiveModal.tsx'
import { AuthModal } from '@/components/AuthModal.tsx'
import { Navbar } from '@/components/Navbar.tsx'
import { PuzzleContainer } from '@/components/PuzzleContainer.tsx'
import { useAuth } from '@/hooks/useAuth.ts'
import type { ArchivePuzzleItem } from '@/types/puzzle.ts'

export default function App() {
  const navigate = useNavigate()
  const { isAuthenticated, sessionPending } = useAuth()
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [playback, setPlayback] = useState<ArchivePuzzleItem | null>(null)
  const [homeKey, setHomeKey] = useState(0)

  const openArchive = useCallback(() => {
    if (sessionPending) return
    if (!isAuthenticated) {
      void navigate('/archive')
      return
    }
    setArchiveOpen(true)
  }, [isAuthenticated, navigate, sessionPending])

  function returnHome() {
    setPlayback(null)
    setHomeKey((key) => key + 1)
    void navigate('/')
  }

  function selectArchive(item: ArchivePuzzleItem) {
    if (item.is_completed || !isAuthenticated) {
      setArchiveOpen(false)
      if (!isAuthenticated) void navigate('/archive')
      return
    }
    setPlayback(item)
    setArchiveOpen(false)
    void navigate('/archive')
  }

  function clearPlayback() {
    setPlayback(null)
    void navigate('/')
  }

  return (
    <div className="min-h-svh">
      <Navbar onOpenArchive={openArchive} />
      <main className="px-4 pb-12">
        <Routes>
          <Route
            path="/"
            element={
              <PuzzleContainer
                key={homeKey}
                mode="daily"
                onOpenArchive={openArchive}
                onLeaveResult={returnHome}
              />
            }
          />
          <Route
            path="/archive"
            element={
              <ArchiveRoute
                playback={playback}
                onClearPlayback={clearPlayback}
                onOpenArchive={openArchive}
                onLeaveResult={returnHome}
              />
            }
          />
        </Routes>
      </main>
      <ArchiveModal open={archiveOpen} onClose={() => setArchiveOpen(false)} onSelect={selectArchive} />
      <AuthModal />
    </div>
  )
}

function ArchiveRoute({
  playback,
  onClearPlayback,
  onOpenArchive,
  onLeaveResult,
}: {
  playback: ArchivePuzzleItem | null
  onClearPlayback: () => void
  onOpenArchive: () => void
  onLeaveResult: () => void
}) {
  const navigate = useNavigate()
  const { isAuthenticated, sessionPending, openAuthModal } = useAuth()

  useEffect(() => {
    if (sessionPending || !isAuthenticated || playback) return
    onOpenArchive()
    void navigate('/', { replace: true })
  }, [isAuthenticated, sessionPending, playback, navigate, onOpenArchive])

  if (sessionPending) return null

  if (!isAuthenticated) {
    return (
      <section className="mx-auto mt-8 max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 text-center">
        <ArchiveSignInPrompt onSignIn={openAuthModal} />
      </section>
    )
  }

  if (!playback) return null

  return (
    <PuzzleContainer
      mode="archive"
      playback={playback}
      onClearPlayback={onClearPlayback}
      onOpenArchive={onOpenArchive}
      onLeaveResult={onLeaveResult}
    />
  )
}

function ArchiveSignInPrompt({ onSignIn }: { onSignIn: () => void }) {
  return (
    <>
      <h1 className="text-xl font-semibold text-white">
        Archive is for signed-in players
      </h1>
      <p className="mt-2 text-slate-300">
        Sign in to catch up on past daily puzzles you have not finished.
      </p>
      <button
        type="button"
        onClick={onSignIn}
        className="mt-4 rounded-full border border-amber-500 bg-amber-400 px-4 py-2 text-sm font-medium text-slate-950 hover:border-slate-950"
      >
        Sign in
      </button>
    </>
  )
}
