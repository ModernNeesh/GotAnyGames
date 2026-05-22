import { useState } from 'react'
import type { UserRatedGame } from '../types'

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
      <p className="text-gray-500 text-center py-12">
        Your game list is empty. Search for games above to get started!
      </p>
    )
  }

  return (
    <ul className="space-y-3">
      {games.map(game => (
        <li
          key={game.game_id}
          className="flex items-center gap-4 bg-gray-800 rounded-xl p-4 border border-gray-700"
        >
          <img
            src={game.cover_url}
            alt={game.game_name}
            className="w-12 h-16 object-cover rounded"
          />
          <div className="flex-1 min-w-0">
            <p className="text-white font-medium truncate">{game.game_name}</p>
            <p className="text-gray-400 text-xs truncate">
              {game.platforms.join(', ')}
            </p>
          </div>

          {editingId === game.game_id ? (
            <div className="flex items-center gap-2 shrink-0">
              <input
                type="number"
                min={0}
                max={100}
                value={editRating}
                onChange={e => setEditRating(Number(e.target.value))}
                className="w-16 px-2 py-1 rounded bg-gray-700 text-white text-center border border-gray-600"
              />
              <button
                onClick={() => saveEdit(game.game_id)}
                disabled={busy}
                className="px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-700 text-white text-sm disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={() => setEditingId(null)}
                className="px-3 py-1 rounded bg-gray-700 hover:bg-gray-600 text-white text-sm"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3 shrink-0">
              <span className="text-indigo-400 font-semibold text-lg">{game.rating}</span>
              <button
                onClick={() => startEdit(game)}
                disabled={busy}
                className="px-3 py-1 rounded bg-gray-700 hover:bg-gray-600 text-white text-sm"
              >
                Edit
              </button>
              <button
                onClick={() => handleDelete(game.game_id)}
                disabled={busy}
                className="px-3 py-1 rounded bg-red-800 hover:bg-red-700 text-white text-sm disabled:opacity-50"
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
