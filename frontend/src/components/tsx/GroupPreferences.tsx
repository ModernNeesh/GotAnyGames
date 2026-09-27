import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api } from '../../lib/api'
import type { GroupMember, GroupPlatform, GroupPreferencesData } from '../../types'
import { GroupDialog } from './GroupDialog'
import '../css/GroupPreferences.css'

interface GroupPreferencesProps {
  groupId: number
  member: GroupMember
  editable: boolean
  onClose: () => void
  onSaved: () => void
}

export function GroupPreferences({ groupId, member, editable, onClose, onSaved }: GroupPreferencesProps) {
  const [platforms, setPlatforms] = useState<GroupPlatform[]>([])
  const [preferences, setPreferences] = useState<GroupPreferencesData>({ platform_ids: [], online: false, offline: false })
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [retryAttempt, setRetryAttempt] = useState(0)
  const submitting = useRef(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    setLoadError(false)
    setError(null)

    async function loadPreferences() {
      try {
        const [options, saved] = await Promise.all([
          api.get<GroupPlatform[]>('/group_platforms/'),
          api.get<GroupPreferencesData>(`/groups/${groupId}/members/${member.id}/preferences`),
        ])
        if (active) {
          setPlatforms(options)
          setPreferences(saved)
        }
      } catch {
        if (active) setLoadError(true)
      } finally {
        if (active) setLoading(false)
      }
    }

    loadPreferences()
    return () => { active = false }
  }, [groupId, member.id, retryAttempt])

  function togglePlatform(id: number) {
    setPreferences(current => ({
      ...current,
      platform_ids: current.platform_ids.includes(id)
        ? current.platform_ids.filter(platformId => platformId !== id)
        : [...current.platform_ids, id],
    }))
    setError(null)
  }

  async function savePreferences(event: FormEvent) {
    event.preventDefault()
    if (!editable || submitting.current) return
    if (preferences.platform_ids.length === 0 || (!preferences.online && !preferences.offline)) {
      setError('Choose at least one platform and one way to play.')
      return
    }
    submitting.current = true
    setSaving(true)
    setError(null)
    try {
      await api.patch(`/groups/${groupId}/preferences`, preferences)
      onSaved()
    } catch {
      setError('We couldn’t save your preferences. Please try again.')
    } finally {
      submitting.current = false
      setSaving(false)
    }
  }

  const visiblePlatforms = platforms.filter(platform => platform.name.toLowerCase().includes(filter.trim().toLowerCase()))
  const selectedPlatforms = platforms.filter(platform => preferences.platform_ids.includes(platform.id))

  return (
    <GroupDialog title={editable ? 'Your group preferences' : `${member.name}’s preferences`} onClose={onClose} busy={saving}>
      {loading ? (
        <p className="group-dialog-status" role="status">Loading preferences…</p>
      ) : loadError ? (
        <>
          <p className="group-dialog-error" role="alert">We couldn’t load these preferences. Please try again.</p>
          <div className="group-dialog-actions">
            <button className="group-dialog-button" onClick={() => setRetryAttempt(value => value + 1)}>Try again</button>
          </div>
        </>
      ) : !editable ? (
        <>
          <p className="group-dialog-description">Platforms and play styles for this group.</p>
          {selectedPlatforms.length === 0 ? (
            <p className="group-dialog-status">This member hasn’t set their preferences yet.</p>
          ) : (
            <dl className="group-preferences-summary">
              <dt>Platforms</dt>
              <dd>{selectedPlatforms.map(platform => platform.name).join(', ')}</dd>
              <dt>Ways to play</dt>
              <dd>{[preferences.online && 'Online', preferences.offline && 'Local / in person'].filter(Boolean).join(' · ')}</dd>
            </dl>
          )}
          <div className="group-dialog-actions"><button className="group-dialog-button" onClick={onClose}>Done</button></div>
        </>
      ) : (
        <form onSubmit={savePreferences}>
          <p className="group-dialog-description">Choose the platforms and ways you want to play with this group.</p>
          <fieldset disabled={saving} className="group-preferences-fieldset">
            <legend>Platforms ({preferences.platform_ids.length} selected)</legend>
            <label htmlFor="group-platform-filter" className="group-dialog-label">Find a platform</label>
            <input id="group-platform-filter" type="search" className="group-dialog-input" value={filter} onChange={event => setFilter(event.target.value)} placeholder="Search platforms…" />
            <div className="group-preferences-platforms">
              {visiblePlatforms.map(platform => (
                <label key={platform.id} className="group-preferences-option">
                  <input type="checkbox" checked={preferences.platform_ids.includes(platform.id)} onChange={() => togglePlatform(platform.id)} />
                  <span>{platform.name}</span>
                </label>
              ))}
              {visiblePlatforms.length === 0 && (
                <p className="group-dialog-status">{platforms.length === 0 ? 'No platforms are available yet.' : 'No platforms match your search.'}</p>
              )}
            </div>
          </fieldset>
          <fieldset disabled={saving} className="group-preferences-fieldset">
            <legend>Ways to play</legend>
            <label className="group-preferences-option">
              <input type="checkbox" checked={preferences.online} onChange={event => setPreferences(current => ({ ...current, online: event.target.checked }))} />
              <span>Online</span>
            </label>
            <label className="group-preferences-option">
              <input type="checkbox" checked={preferences.offline} onChange={event => setPreferences(current => ({ ...current, offline: event.target.checked }))} />
              <span>Local / in person</span>
            </label>
          </fieldset>
          {error && <p className="group-dialog-error" role="alert">{error}</p>}
          <div className="group-dialog-actions">
            <button type="button" className="group-dialog-button" disabled={saving} onClick={onClose}>Cancel</button>
            <button className="group-dialog-button group-dialog-button-primary" disabled={saving || platforms.length === 0}>
              {saving ? 'Saving…' : 'Save preferences'}
            </button>
          </div>
        </form>
      )}
    </GroupDialog>
  )
}
