import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function Home() {
  const { user, signOut } = useAuth()

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <h1 className="text-2xl font-bold">GotAnyGames</h1>
        <div className="flex items-center gap-4">
          <span className="text-gray-400 text-sm">{user?.email}</span>
          <button
            onClick={signOut}
            className="px-4 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm transition-colors"
          >
            Sign Out
          </button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold text-center mb-2">Welcome back!</h2>
        <p className="text-gray-400 text-center mb-12">What would you like to do?</p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <Link
            to="/my-games"
            className="block p-8 rounded-2xl bg-gray-800 hover:bg-gray-750 border border-gray-700 hover:border-indigo-500 transition-colors group"
          >
            <div className="text-4xl mb-4">🎮</div>
            <h3 className="text-xl font-semibold mb-2 group-hover:text-indigo-400 transition-colors">
              My Games
            </h3>
            <p className="text-gray-400 text-sm">
              Search for games, build your list, and rate them.
            </p>
          </Link>

          <div className="block p-8 rounded-2xl bg-gray-800 border border-gray-700 opacity-50 cursor-not-allowed">
            <div className="text-4xl mb-4">👥</div>
            <h3 className="text-xl font-semibold mb-2">Groups</h3>
            <p className="text-gray-400 text-sm">
              Create groups and get recommendations together.
            </p>
            <span className="inline-block mt-3 px-3 py-1 rounded-full bg-gray-700 text-xs text-gray-400">
              Coming Soon
            </span>
          </div>
        </div>
      </main>
    </div>
  )
}
