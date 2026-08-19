import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { api } from '../../lib/api'
import { GameSearch } from '../../components/tsx/GameSearch'
import { GameList } from '../../components/tsx/GameList'
import type { SearchbarGameData, UserRatedGame } from '../../types'
import '../css/MyGames.css'

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
    <div className="my-games-page">
      <header className="my-games-header">
        <div className="my-games-header-title-group">
          <Link to="/" className="my-games-back-link">
            &larr; Back
          </Link>
          <h1 className="my-games-title">My Games</h1>
        </div>
        <button
          onClick={signOut}
          className="my-games-sign-out-button"
        >
          Sign Out
        </button>
      </header>

      <main className="my-games-content">
        <GameSearch onSelect={game => { setSelectedGame(game); setNewRating(50) }} />

        {selectedGame && (
          <div className="my-games-selected-card">
            <img
              src={selectedGame.cover_url}
              alt={selectedGame.name}
              className="my-games-selected-cover"
            />
            <div className="my-games-selected-details">
              <p className="my-games-selected-name">{selectedGame.name}</p>
              <p className="my-games-selected-platforms">
                {selectedGame.platforms.join(', ')}
              </p>
            </div>
            <div className="my-games-selected-controls">
              <label className="my-games-rating-label">Rating:</label>
              <input
                type="number"
                min={0}
                max={100}
                value={newRating}
                onChange={e => setNewRating(Number(e.target.value))}
                className="my-games-rating-input"
              />
              <button
                onClick={handleAdd}
                disabled={adding}
                className="my-games-add-button"
              >
                {adding ? 'Adding...' : 'Add'}
              </button>
              <button
                onClick={() => setSelectedGame(null)}
                className="my-games-cancel-button"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {error && <p className="my-games-error-message">{error}</p>}

        <div>
          <h2 className="my-games-list-heading">
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
