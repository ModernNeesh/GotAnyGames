import { useEffect, useRef, useState } from 'react'
import { api } from '../../lib/api'
import type { GroupDetailData, GroupMember } from '../../types'
import { GroupDialog } from './GroupDialog'
import '../css/AddGroupMember.css'

interface AddGroupMemberProps {
  groupId: number
  onAdded: (group: GroupDetailData) => void
  onClose: () => void
}

export function AddGroupMember({ groupId, onAdded, onClose }: AddGroupMemberProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GroupMember[]>([])
  const [searching, setSearching] = useState(false)
  const [addingId, setAddingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [retryAttempt, setRetryAttempt] = useState(0)
  const submitting = useRef(false)
  const search = query.trim()

  useEffect(() => {
    let active = true
    setResults([])
    setError(null)
    setSearching(search.length >= 2)
    if (search.length < 2) return

    const timer = window.setTimeout(async () => {
      try {
        const users = await api.get<GroupMember[]>(`/groups/${groupId}/users?query=${encodeURIComponent(search)}`)
        if (active) setResults(users)
      } catch {
        if (active) setError('We couldn’t search for users. Please try again.')
      } finally {
        if (active) setSearching(false)
      }
    }, 300)

    return () => {
      active = false
      window.clearTimeout(timer)
    }
  }, [groupId, search, retryAttempt])

  async function addMember(member: GroupMember) {
    if (submitting.current) return
    submitting.current = true
    setAddingId(member.id)
    setError(null)
    try {
      const group = await api.post<GroupDetailData>(`/groups/${groupId}/members`, { user_id: member.id })
      onAdded(group)
    } catch {
      setError('We couldn’t add this user. They may already be a member. Try searching again.')
    } finally {
      submitting.current = false
      setAddingId(null)
    }
  }

  return (
    <GroupDialog title="Add a user" onClose={onClose} busy={addingId !== null}>
      <p className="group-dialog-description">Find a friend by their display name to add them to this group.</p>
      <label htmlFor="group-user-search" className="group-dialog-label">Display name</label>
      <input
        id="group-user-search"
        className="group-dialog-input"
        data-dialog-autofocus
        type="search"
        autoComplete="off"
        value={query}
        maxLength={100}
        disabled={addingId !== null}
        onChange={event => setQuery(event.target.value)}
        placeholder="Search for a friend…"
      />
      <div aria-live="polite" aria-busy={searching}>
        {search.length < 2 ? (
          <p className="group-dialog-status">Enter at least 2 characters to search.</p>
        ) : searching ? (
          <p className="group-dialog-status">Searching for users…</p>
        ) : results.length === 0 && !error ? (
          <p className="group-dialog-status">No users found. Try another name. Existing members are already in your group.</p>
        ) : (
          <ul className="group-user-results">
            {results.map(member => (
              <li key={member.id}>
                <span>{member.name}</span>
                <button
                  className="group-dialog-button group-dialog-button-primary"
                  disabled={addingId !== null}
                  aria-label={`Add ${member.name}`}
                  onClick={() => addMember(member)}
                >
                  {addingId === member.id ? 'Adding…' : 'Add'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      {error && <p className="group-dialog-error" role="alert">{error}</p>}
      <div className="group-dialog-actions">
        {error && <button className="group-dialog-button" disabled={addingId !== null} onClick={() => setRetryAttempt(value => value + 1)}>Try again</button>}
        <button className="group-dialog-button" disabled={addingId !== null} onClick={onClose}>Cancel</button>
      </div>
    </GroupDialog>
  )
}
