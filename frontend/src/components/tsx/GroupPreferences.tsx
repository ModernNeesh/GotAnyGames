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
  const [preferences, setPreferences] = useState<GroupPreferencesData>({ platforms: [] })
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
      platforms: current.platforms.some(platform => platform.platform_id === id)
        ? current.platforms.filter(platform => platform.platform_id !== id)
        : [...current.platforms, { platform_id: id, online: false, offline: false }],
    }))
    setError(null)
  }

  function togglePlayMode(id: number, mode: 'online' | 'offline', checked: boolean) {
    setPreferences(current => ({
      platforms: current.platforms.map(platform => platform.platform_id === id
        ? { ...platform, [mode]: checked }
        : platform),
    }))
    setError(null)
  }

  async function savePreferences(event: FormEvent) {
    event.preventDefault()
    if (!editable || submitting.current) return
    if (preferences.platforms.length === 0) {
      setError('Choose at least one platform.')
      return
    }
    if (preferences.platforms.some(platform => !platform.online && !platform.offline)) {
      setError('Choose at least one way to play for each platform.')
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
  const selectedPlatforms = preferences.platforms.map(preference => ({
    ...preference,
    name: platforms.find(platform => platform.id === preference.platform_id)?.name ?? `Platform ${preference.platform_id}`,
  }))

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
              {selectedPlatforms.map(platform => (
                <div key={platform.platform_id}>
                  <dt>{platform.name}</dt>
                  <dd>{[platform.online && 'Online', platform.offline && 'Local / in person'].filter(Boolean).join(' · ')}</dd>
                </div>
              ))}
            </dl>
          )}
          <div className="group-dialog-actions"><button className="group-dialog-button" onClick={onClose}>Done</button></div>
        </>
      ) : (
        <form onSubmit={savePreferences}>
          <p className="group-dialog-description">Choose your platforms, then select how you want to play on each one with this group.</p>
          <fieldset disabled={saving} className="group-preferences-fieldset">
            <legend>Platforms ({preferences.platforms.length} selected)</legend>
            <label htmlFor="group-platform-filter" className="group-dialog-label">Find a platform</label>
            <input id="group-platform-filter" type="search" className="group-dialog-input" value={filter} onChange={event => setFilter(event.target.value)} placeholder="Search platforms…" />
            <div className="group-preferences-platforms">
              {visiblePlatforms.map(platform => (
                <label key={platform.id} className="group-preferences-option">
                  <input type="checkbox" checked={preferences.platforms.some(preference => preference.platform_id === platform.id)} onChange={() => togglePlatform(platform.id)} />
                  <span>{platform.name}</span>
                </label>
              ))}
              {visiblePlatforms.length === 0 && (
                <p className="group-dialog-status">{platforms.length === 0 ? 'No platforms are available yet.' : 'No platforms match your search.'}</p>
              )}
            </div>
          </fieldset>
          {selectedPlatforms.length > 0 && (
            <fieldset disabled={saving} className="group-preferences-fieldset">
              <legend>Ways to play by platform</legend>
              <p className="group-dialog-description">Choose one or both for each platform.</p>
              <div className="group-preferences-play-modes">
                {selectedPlatforms.map(platform => (
                  <fieldset key={platform.platform_id} className="group-preferences-platform-modes">
                    <legend>{platform.name}</legend>
                    <div className="group-preferences-mode-options">
                      <label className="group-preferences-option">
                        <input type="checkbox" checked={platform.online} onChange={event => togglePlayMode(platform.platform_id, 'online', event.target.checked)} />
                        <span>Online</span>
                      </label>
                      <label className="group-preferences-option">
                        <input type="checkbox" checked={platform.offline} onChange={event => togglePlayMode(platform.platform_id, 'offline', event.target.checked)} />
                        <span>Local / in person</span>
                      </label>
                    </div>
                  </fieldset>
                ))}
              </div>
            </fieldset>
          )}
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
