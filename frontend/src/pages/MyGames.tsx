import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../lib/api'
import { GameSearch } from '../components/GameSearch'
import { GameList } from '../components/GameList'
import type { SearchbarGameData, UserRatedGame } from '../types'

export function MyGames() {
  const { signOut } = useAuth()
  const [games, setGames] = useState<UserRatedGame[]>([])
  const [selectedGame, setSelectedGame] = useState<SearchbarGameData | null>(null)
  const [newRating, setNewRating] = useState(50)
  const [error, setError] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)

  const fetchRatings = useCallback(async () => {
    try {
      const data = await api.get<UserRatedGame[]>('/my_ratings/')
      setGames(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load ratings')
    }
  }, [])

  useEffect(() => {
    fetchRatings()
  }, [fetchRatings])

  async function handleAdd() {
    if (!selectedGame) return
    setAdding(true)
    setError(null)
    try {
      await api.post('/rate_game/', { game_id: selectedGame.id, rating: newRating })
      setSelectedGame(null)
      setNewRating(50)
      await fetchRatings()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add game')
    } finally {
      setAdding(false)
    }
  }

  async function handleUpdateRating(gameId: number, rating: number) {
    setError(null)
    try {
      await api.post('/rate_game/', { game_id: gameId, rating })
      await fetchRatings()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update rating')
    }
  }

  async function handleDelete(gameId: number) {
    setError(null)
    try {
      await api.del(`/delete_rating/${gameId}`)
      await fetchRatings()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete rating')
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-gray-400 hover:text-white transition-colors">
            &larr; Back
          </Link>
          <h1 className="text-2xl font-bold">My Games</h1>
        </div>
        <button
          onClick={signOut}
          className="px-4 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm transition-colors"
        >
          Sign Out
        </button>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        <GameSearch onSelect={game => { setSelectedGame(game); setNewRating(50) }} />

        {selectedGame && (
          <div className="flex items-center gap-4 bg-gray-800 rounded-xl p-4 border border-indigo-500">
            <img
              src={selectedGame.cover_url}
              alt={selectedGame.name}
              className="w-12 h-16 object-cover rounded"
            />
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium truncate">{selectedGame.name}</p>
              <p className="text-gray-400 text-xs truncate">
                {selectedGame.platforms.join(', ')}
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <label className="text-sm text-gray-300">Rating:</label>
              <input
                type="number"
                min={0}
                max={100}
                value={newRating}
                onChange={e => setNewRating(Number(e.target.value))}
                className="w-16 px-2 py-1 rounded bg-gray-700 text-white text-center border border-gray-600"
              />
              <button
                onClick={handleAdd}
                disabled={adding}
                className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm disabled:opacity-50 transition-colors"
              >
                {adding ? 'Adding...' : 'Add'}
              </button>
              <button
                onClick={() => setSelectedGame(null)}
                className="px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <div>
          <h2 className="text-lg font-semibold mb-4">
            Your Rated Games ({games.length})
          </h2>
          <GameList
            games={games}
            onUpdateRating={handleUpdateRating}
            onDelete={handleDelete}
          />
        </div>
      </main>
    </div>
  )
}
