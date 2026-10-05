import { Route, Routes } from 'react-router-dom'
import { AuthModal } from '@/components/AuthModal.tsx'
import { Navbar } from '@/components/Navbar.tsx'
import { PuzzleContainer } from '@/components/PuzzleContainer.tsx'
import { useAuth } from '@/hooks/useAuth.ts'

export default function App() {
  return (
    <div className="min-h-svh">
      <Navbar />
      <main className="px-4 pb-12">
        <Routes>
          <Route path="/" element={<PuzzleContainer mode="daily" />} />
          <Route path="/archive" element={<ArchiveRoute />} />
        </Routes>
      </main>
      <AuthModal />
    </div>
  )
}

function ArchiveRoute() {
  const { isAuthenticated, openAuthModal } = useAuth()

  if (!isAuthenticated) {
    return (
      <section className="mx-auto mt-8 max-w-xl rounded-2xl border border-slate-800 bg-slate-900 p-6 text-center">
        <h1 className="text-xl font-semibold text-white">Archive is for signed-in players</h1>
        <p className="mt-2 text-slate-300">
          Sign in to catch up on past daily puzzles you have not finished.
        </p>
        <button
          type="button"
          onClick={openAuthModal}
          className="mt-4 rounded-full bg-amber-400 px-4 py-2 text-sm font-medium text-slate-950"
        >
          Sign in
        </button>
      </section>
    )
  }

  return <PuzzleContainer mode="archive" />
}
