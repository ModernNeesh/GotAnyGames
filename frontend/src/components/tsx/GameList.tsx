import { useState } from 'react'
import type { UserRatedGame } from '../../types'
import '../css/GameList.css'

interface Props {
  games: UserRatedGame[]
  onUpdateRating: (gameId: number, rating: number) => Promise<void>
  onDelete: (gameId: number) => Promise<void>
}

export function GameList({ games, onUpdateRating, onDelete }: Props) {
  /*
  Component that renders the list of games the user has already rated

  Inputs:
  - games: An array of UserRatedGame objects representing the user's rated games
  - onUpdateRating: A function (passed by parent) that handles updates to a game's rating; takes gameId and new rating as arguments
  - onDelete: A function (passed by parent) that handles deletions of games from the list; takes gameId as an argument


  */
  const [editingId, setEditingId] = useState<number | null>(null) // Identifies which game is currently being edited (null if none)
  const [editRating, setEditRating] = useState(0) // Holds the new rating value while editing
  const [busy, setBusy] = useState(false) // Indicates whether an update or delete operation is in progress; turns off buttons if so

  function startEdit(game: UserRatedGame) {
    /*
    Start editing the rating of a game.

    Inputs:
    - game: The UserRatedGame object representing the game to be edited

    Returns:
    - None
    */
    setEditingId(game.game_id)
    setEditRating(game.rating)
  }

  async function saveEdit(gameId: number) {
    /*
    Function triggered when a new rating is saved for a game

    Inputs:
    - gameId: The ID of the game being edited

    Returns:
    - None
    */
    setBusy(true)
    await onUpdateRating(gameId, editRating)
    setEditingId(null)
    setBusy(false)
  }

  async function handleDelete(gameId: number) {
    /*
    Function triggered when a game is deleted from the list

    Inputs:
    - gameId: The ID of the game to be deleted

    Returns:
    - None
    */
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
                disabled={busy}
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
