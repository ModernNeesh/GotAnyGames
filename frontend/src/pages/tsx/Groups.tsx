import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { api } from '../../lib/api'
import type { UserGroup } from '../../types'
import '../css/Groups.css'

export function Groups() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [groups, setGroups] = useState<UserGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retryAttempt, setRetryAttempt] = useState(0)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [groupName, setGroupName] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const createPending = useRef(false)
  const createButton = useRef<HTMLButtonElement>(null)

  async function createGroup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (createPending.current) return

    const name = groupName.trim()
    if (!name || name.length > 100) {
      setCreateError('Enter a group name between 1 and 100 characters.')
      return
    }

    createPending.current = true
    setCreating(true)
    setCreateError(null)

    try {
      const group = await api.post<UserGroup>('/create_group/', { name })
      navigate(`/groups/${group.id}`)
    } catch {
      setCreateError('We couldn’t create your group. Please try again.')
    } finally {
      createPending.current = false
      setCreating(false)
    }
  }

  function cancelCreate() {
    setShowCreateForm(false)
    setGroupName('')
    setCreateError(null)
    createButton.current?.focus()
  }

  useEffect(() => {
    let active = true

    async function fetchGroups() {
      setLoading(true)
      setError(null)
      setGroups([])

      try {
        const data = await api.get<UserGroup[]>('/my_groups/')
        if (active) setGroups(data)
      } catch {
        if (active) setError('We couldn’t load your groups. Please try again.')
      } finally {
        if (active) setLoading(false)
      }
    }

    fetchGroups()

    return () => {
      active = false
    }
  }, [user?.id, retryAttempt])

  return (
    <div className="groups-page">
      <header className="groups-header">
        <div className="groups-header-title-group">
          <Link to="/" className="groups-back-link">
            &larr; Back
          </Link>
          <h1 className="groups-title">Groups</h1>
        </div>
        <button onClick={signOut} className="groups-sign-out-button">
          Sign Out
        </button>
      </header>

      <main className="groups-content">
        <div className="groups-intro">
          <div>
            <h2 id="groups-list-heading" className="groups-list-heading">
              Your Groups{!loading && !error ? ` (${groups.length})` : ''}
            </h2>
            <p className="groups-description">The groups you're part of, all in one place.</p>
          </div>
          <button
            ref={createButton}
            type="button"
            className="groups-create-button"
            aria-expanded={showCreateForm}
            aria-controls="groups-create-form"
            disabled={creating}
            onClick={() => showCreateForm ? cancelCreate() : setShowCreateForm(true)}
          >
            <span aria-hidden="true">+ </span>Create Group
          </button>
        </div>

        {showCreateForm && (
          <form id="groups-create-form" className="groups-create-form" onSubmit={createGroup} aria-busy={creating}>
            <label htmlFor="groups-name" className="groups-name-label">Group name</label>
            <div className="groups-create-fields">
              <input
                id="groups-name"
                className="groups-name-input"
                value={groupName}
                onChange={event => {
                  setGroupName(event.target.value)
                  setCreateError(null)
                }}
                placeholder="e.g. Friday Night Squad"
                maxLength={100}
                required
                autoFocus
                disabled={creating}
                aria-invalid={Boolean(createError)}
                aria-describedby={createError ? 'groups-create-error' : undefined}
              />
              <button type="submit" className="groups-create-button" disabled={creating}>
                {creating ? 'Creating...' : 'Create Group'}
              </button>
              <button type="button" className="groups-cancel-button" onClick={cancelCreate} disabled={creating}>
                Cancel
              </button>
            </div>
            {createError && <p id="groups-create-error" className="groups-error-message" role="alert">{createError}</p>}
          </form>
        )}

        <section
          className="groups-scroll-area"
          aria-labelledby="groups-list-heading"
          aria-busy={loading}
          tabIndex={0}
        >
          {loading ? (
            <div className="groups-state" role="status">
              <p className="groups-state-description">Loading your groups...</p>
            </div>
          ) : error ? (
            <div className="groups-state">
              <p className="groups-error-message" role="alert">{error}</p>
              <button
                className="groups-retry-button"
                onClick={() => setRetryAttempt(attempt => attempt + 1)}
              >
                Try again
              </button>
            </div>
          ) : groups.length === 0 ? (
            <div className="groups-state" role="status">
              <span className="groups-card-icon" aria-hidden="true">👥</span>
              <h3 className="groups-state-title">No groups yet</h3>
              <p className="groups-state-description">
                Create a group to bring your friends together, or ask a friend to add you to theirs.
              </p>
            </div>
          ) : (
            <ul className="groups-grid">
              {groups.map(group => (
                <li key={group.id}>
                  <Link to={`/groups/${group.id}`} className="groups-card">
                    <span className="groups-card-icon" aria-hidden="true">👥</span>
                    <h3 className="groups-card-name" title={group.name}>{group.name}</h3>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  )
}
