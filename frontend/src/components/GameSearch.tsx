import { useState, useEffect, useRef } from 'react'
import { api } from '../lib/api'
import type { SearchbarGameData } from '../types'

interface Props {
  onSelect: (game: SearchbarGameData) => void
}

export function GameSearch({ onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchbarGameData[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (query.length < 2) {
      setResults([])
      setOpen(false)
      return
    }

    const timeout = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await api.get<SearchbarGameData[]>(
          `/search_game/${encodeURIComponent(query)}?limit=5`
        )
        setResults(data)
        setOpen(true)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300)

    return () => clearTimeout(timeout)
  }, [query])

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  function handleSelect(game: SearchbarGameData) {
    onSelect(game)
    setQuery('')
    setResults([])
    setOpen(false)
  }

  return (
    <div ref={containerRef} className="relative">
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        onFocus={() => { if (results.length > 0) setOpen(true) }}
        placeholder="Search for a game..."
        className="w-full px-4 py-3 rounded-xl bg-gray-700 text-white border border-gray-600 focus:border-indigo-500 focus:outline-none text-lg"
      />
      {loading && (
        <div className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 text-sm">
          Searching...
        </div>
      )}

      {open && results.length > 0 && (
        <ul className="absolute z-10 w-full mt-2 bg-gray-800 border border-gray-700 rounded-xl overflow-hidden shadow-2xl">
          {results.map(game => (
            <li key={game.id}>
              <button
                onClick={() => handleSelect(game)}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 transition-colors text-left"
              >
                <img
                  src={game.cover_url}
                  alt={game.name}
                  className="w-10 h-14 object-cover rounded"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-white font-medium truncate">{game.name}</p>
                  <p className="text-gray-400 text-xs truncate">
                    {game.platforms.join(', ')}
                  </p>
                </div>
                <span className="text-gray-400 text-sm shrink-0">
                  {game.total_rating > 0 ? `${Math.round(game.total_rating)}%` : 'N/A'}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
