import { useState, useEffect, useRef } from 'react'
import { api } from '../../lib/api'
import type { SearchbarGameData } from '../../types'
import '../css/GameSearch.css'

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
    <div ref={containerRef} className="game-search">
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        onFocus={() => { if (results.length > 0) setOpen(true) }}
        placeholder="Search for a game..."
        className="game-search-input"
      />
      {loading && (
        <div className="game-search-status">
          Searching...
        </div>
      )}

      {open && results.length > 0 && (
        <ul className="game-search-results">
          {results.map(game => (
            <li key={game.id}>
              <button
                onClick={() => handleSelect(game)}
                className="game-search-result-button"
              >
                <img
                  src={game.cover_url}
                  alt={game.name}
                  className="game-search-cover"
                />
                <div className="game-search-details">
                  <p className="game-search-name">{game.name}</p>
                  <p className="game-search-platforms">
                    {game.platforms.join(', ')}
                  </p>
                </div>
                <span className="game-search-score">
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
