import { useState } from 'react'
import type { UserRatedGame } from '../../types'
import '../css/GameList.css'

interface Props {
  games: UserRatedGame[]
  onUpdateRating: (gameId: number, rating: number) => Promise<void>
  onDelete: (gameId: number) => Promise<void>
}

export function GameList({ games, onUpdateRating, onDelete }: Props) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editRating, setEditRating] = useState(0)
  const [busy, setBusy] = useState(false)

  function startEdit(game: UserRatedGame) {
    setEditingId(game.game_id)
    setEditRating(game.rating)
  }

  async function saveEdit(gameId: number) {
    setBusy(true)
    await onUpdateRating(gameId, editRating)
    setEditingId(null)
    setBusy(false)
  }

  async function handleDelete(gameId: number) {
    if (!confirm('Remove this game from your list?')) return
    setBusy(true)
    await onDelete(gameId)
    setBusy(false)
  }

  if (games.length === 0) {
    return (
      <p className="game-list-empty-message">
        Your game list is empty. Search for games above to get started!
      </p>
    )
  }

  return (
    <ul className="game-list">
      {games.map(game => (
        <li
          key={game.game_id}
          className="game-list-item"
        >
          <img
            src={game.cover_url}
            alt={game.game_name}
            className="game-list-cover"
          />
          <div className="game-list-details">
            <p className="game-list-name">{game.game_name}</p>
            <p className="game-list-platforms">
              {game.platforms.join(', ')}
            </p>
          </div>

          {editingId === game.game_id ? (
            <div className="game-list-edit-controls">
              <input
                type="number"
                min={0}
                max={100}
                value={editRating}
                onChange={e => setEditRating(Number(e.target.value))}
                className="game-list-rating-input"
              />
              <button
                onClick={() => saveEdit(game.game_id)}
                disabled={busy}
                className="game-list-save-button"
              >
                Save
              </button>
              <button
                onClick={() => setEditingId(null)}
                className="game-list-cancel-button"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="game-list-actions">
              <span className="game-list-rating">{game.rating}</span>
              <button
                onClick={() => startEdit(game)}
                disabled={busy}
                className="game-list-edit-button"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(game.game_id)}
                disabled={busy}
                className="game-list-remove-button"
              >
                Remove
              </button>
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}
