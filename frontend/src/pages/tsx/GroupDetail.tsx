import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { api } from '../../lib/api'
import { AddGroupMember } from '../../components/tsx/AddGroupMember'
import { GroupDialog } from '../../components/tsx/GroupDialog'
import { GroupPreferences } from '../../components/tsx/GroupPreferences'
import { GroupPreferenceSummary } from '../../components/tsx/GroupPreferenceSummary'
import type { GroupDetailData, GroupMember } from '../../types'
import '../css/GroupDetail.css'

const groupTabs = [
  { id: 'members', label: 'Members' },
  { id: 'preferences', label: 'Group preferences' },
] as const

type GroupTab = typeof groupTabs[number]['id']

export function GroupDetail() {
  const { groupId = '' } = useParams()
  const { user } = useAuth()
  return <GroupDetailContent key={`${user?.id}:${groupId}`} groupId={groupId} />
}

function GroupDetailContent({ groupId }: { groupId: string }) {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [group, setGroup] = useState<GroupDetailData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [unavailable, setUnavailable] = useState(false)
  const [retryAttempt, setRetryAttempt] = useState(0)
  const [addingMember, setAddingMember] = useState(false)
  const [preferencesMember, setPreferencesMember] = useState<GroupMember | null>(null)
  const [confirmLeave, setConfirmLeave] = useState(false)
  const [leaving, setLeaving] = useState(false)
  const [leaveError, setLeaveError] = useState<string | null>(null)
  const [memberToRemove, setMemberToRemove] = useState<GroupMember | null>(null)
  const [removing, setRemoving] = useState(false)
  const [removeError, setRemoveError] = useState<string | null>(null)
  const [notice, setNotice] = useState('')
  const [activeTab, setActiveTab] = useState<GroupTab>('members')
  const [summaryRevision, setSummaryRevision] = useState(0)
  const tabButtons = useRef<Partial<Record<GroupTab, HTMLButtonElement | null>>>({})
  const leaveInFlight = useRef(false)
  const removeInFlight = useRef(false)
  const addMemberButton = useRef<HTMLButtonElement>(null)
  const focusAfterRemoval = useRef(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    setUnavailable(false)

    async function loadGroup() {
      if (!/^[1-9]\d*$/.test(groupId) || !Number.isSafeInteger(Number(groupId))) {
        setUnavailable(true)
        setLoading(false)
        return
      }
      try {
        const data = await api.get<GroupDetailData>(`/groups/${groupId}`)
        if (active) setGroup(data)
      } catch (err) {
        if (!active) return
        if (err instanceof Error && /^API (403|404):/.test(err.message)) {
          setUnavailable(true)
        } else {
          setError('We couldn’t load this group. Please try again.')
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    loadGroup()
    return () => { active = false }
  }, [groupId, retryAttempt])

  useEffect(() => {
    if (!memberToRemove && focusAfterRemoval.current) {
      focusAfterRemoval.current = false
      addMemberButton.current?.focus()
    }
  }, [memberToRemove])

  function openLeaveDialog() {
    setLeaveError(null)
    setConfirmLeave(true)
  }

  async function leaveGroup() {
    if (!group || leaveInFlight.current) return
    leaveInFlight.current = true
    setLeaving(true)
    setLeaveError(null)
    try {
      await api.del('/leave_group/', { group_id: group.id })
      navigate('/groups', { replace: true })
    } catch {
      setLeaveError('We couldn’t leave this group. Please try again.')
    } finally {
      leaveInFlight.current = false
      setLeaving(false)
    }
  }

  async function removeMember() {
    if (!group || !memberToRemove || memberToRemove.id === user?.id || removeInFlight.current) return
    removeInFlight.current = true
    setRemoving(true)
    setRemoveError(null)
    try {
      const updated = await api.del<GroupDetailData>(`/groups/${group.id}/members/${memberToRemove.id}`)
      setGroup(updated)
      setSummaryRevision(value => value + 1)
      setNotice(`${memberToRemove.name} has been removed from the group.`)
      focusAfterRemoval.current = true
      setMemberToRemove(null)
    } catch {
      setRemoveError('We could not remove this member. Please try again.')
    } finally {
      removeInFlight.current = false
      setRemoving(false)
    }
  }

  const currentMember = group?.members.find(member => member.id === user?.id)

  return (
    <div className="group-detail-page">
      <header className="group-detail-header">
        <div className="group-detail-header-links">
          <Link to="/groups" className="group-detail-back-link">&larr; Groups</Link>
          <span className="group-detail-header-title">Your group</span>
        </div>
        <button onClick={signOut} className="group-detail-button group-detail-sign-out">Sign Out</button>
      </header>

      <main className="group-detail-content">
        {loading ? (
          <div className="group-detail-state" role="status"><p>Loading your group…</p></div>
        ) : unavailable ? (
          <div className="group-detail-state">
            <h1>Group unavailable</h1>
            <p>This group doesn’t exist or you’re no longer a member.</p>
            <Link to="/groups" className="group-detail-button">Back to your groups</Link>
          </div>
        ) : error ? (
          <div className="group-detail-state">
            <p role="alert" className="group-detail-error">{error}</p>
            <button className="group-detail-button" onClick={() => setRetryAttempt(value => value + 1)}>Try again</button>
          </div>
        ) : group && (
          <>
            <div className="group-detail-intro">
              <h1>{group.name}</h1>
              <p>Your friends. Your next game night.</p>
            </div>

            <div className="group-detail-layout">
              <div className="group-detail-main-column">
                <div className="group-detail-tabs" role="tablist" aria-label="Group details">
                  {groupTabs.map((tab, index) => (
                    <button
                      key={tab.id}
                      ref={button => { tabButtons.current[tab.id] = button }}
                      id={`group-${tab.id}-tab`}
                      role="tab"
                      aria-selected={activeTab === tab.id}
                      aria-controls={`group-${tab.id}-panel`}
                      tabIndex={activeTab === tab.id ? 0 : -1}
                      className="group-detail-tab"
                      onClick={() => setActiveTab(tab.id)}
                      onKeyDown={event => {
                        let nextIndex: number
                        if (event.key === 'ArrowRight') nextIndex = (index + 1) % groupTabs.length
                        else if (event.key === 'ArrowLeft') nextIndex = (index + groupTabs.length - 1) % groupTabs.length
                        else if (event.key === 'Home') nextIndex = 0
                        else if (event.key === 'End') nextIndex = groupTabs.length - 1
                        else return
                        event.preventDefault()
                        const nextTab = groupTabs[nextIndex].id
                        setActiveTab(nextTab)
                        tabButtons.current[nextTab]?.focus()
                      }}
                    >{tab.label}</button>
                  ))}
                </div>
                <section
                  id="group-members-panel"
                  role="tabpanel"
                  aria-labelledby="group-members-tab"
                  tabIndex={0}
                  hidden={activeTab !== 'members'}
                  className="group-detail-members"
                >
                  <div className="group-detail-members-heading">
                    <h2 id="group-members-heading">Members</h2>
                    <span className="group-detail-member-count">{group.members.length}</span>
                  </div>
                  <ul className="group-detail-member-list">
                    {group.members.map(member => (
                      <li key={member.id} className="group-detail-member-row">
                        <span className="group-detail-avatar" aria-hidden="true">{Array.from(member.name.trim())[0]?.toUpperCase() || '?'}</span>
                        <span className="group-detail-member-name">{member.name}</span>
                        {member.id === user?.id && <span className="group-detail-you">You</span>}
                        <details
                          className="group-detail-member-actions"
                          onBlur={event => {
                            if (!event.currentTarget.contains(event.relatedTarget as Node | null)) event.currentTarget.open = false
                          }}
                          onKeyDown={event => {
                            if (event.key === 'Escape') {
                              event.currentTarget.open = false
                              event.currentTarget.querySelector('summary')?.focus()
                            }
                          }}
                        >
                          <summary aria-label={`Actions for ${member.name}`}><span aria-hidden="true">⋮</span></summary>
                          <div className="group-detail-member-menu">
                            <button onClick={event => {
                              const menu = event.currentTarget.closest('details')
                              menu?.querySelector('summary')?.focus()
                              menu?.removeAttribute('open')
                              setPreferencesMember(member)
                            }}>
                              {member.id === user?.id ? 'Edit your preferences' : 'View preferences'}
                            </button>
                            {member.id === user?.id && (
                              <button className="group-detail-menu-danger" onClick={event => {
                                const menu = event.currentTarget.closest('details')
                                menu?.querySelector('summary')?.focus()
                                menu?.removeAttribute('open')
                                openLeaveDialog()
                              }}>Leave group</button>
                            )}
                            {member.id !== user?.id && (
                              <button className="group-detail-menu-danger" onClick={event => {
                                const menu = event.currentTarget.closest('details')
                                menu?.querySelector('summary')?.focus()
                                menu?.removeAttribute('open')
                                setRemoveError(null)
                                setMemberToRemove(member)
                              }}>Remove member</button>
                            )}
                          </div>
                        </details>
                      </li>
                    ))}
                  </ul>
                  <button ref={addMemberButton} className="group-detail-add-member" onClick={() => setAddingMember(true)}>
                    <span className="group-detail-add-icon" aria-hidden="true">+</span>
                    Add user
                  </button>
                </section>

                <section
                  id="group-preferences-panel"
                  role="tabpanel"
                  aria-labelledby="group-preferences-tab"
                  tabIndex={0}
                  hidden={activeTab !== 'preferences'}
                >
                  {activeTab === 'preferences' && <GroupPreferenceSummary groupId={group.id} revision={summaryRevision} />}
                </section>

                <div className="group-detail-recommendations">
                  <button className="group-detail-button group-detail-primary" disabled aria-describedby="group-recommendations-status">
                    Get recommendations
                  </button>
                  <p id="group-recommendations-status">Coming soon — discover your next game together.</p>
                </div>
              </div>

              <aside className="group-detail-sidebar" aria-label="Group actions">
                <section className="group-detail-action-card">
                  <span className="group-detail-action-icon" aria-hidden="true">⚙</span>
                  <h2>Make it your game night</h2>
                  <p>Set the platforms and ways you want to play with this group.</p>
                  <button className="group-detail-button" disabled={!currentMember} onClick={() => currentMember && setPreferencesMember(currentMember)}>
                    Edit your preferences
                  </button>
                </section>
                <section className="group-detail-action-card group-detail-leave-card">
                  <h2>Taking a break?</h2>
                  <p>You can leave this group at any time.</p>
                  <button className="group-detail-button group-detail-danger" onClick={openLeaveDialog}>Leave group</button>
                </section>
              </aside>
            </div>
            <p className="group-detail-notice" role="status">{notice}</p>

            {addingMember && <AddGroupMember groupId={group.id} onClose={() => setAddingMember(false)} onAdded={updated => {
              setGroup(updated)
              setSummaryRevision(value => value + 1)
              setAddingMember(false)
              setNotice('Group members updated.')
            }} />}
            {preferencesMember && <GroupPreferences
              groupId={group.id}
              member={preferencesMember}
              editable={preferencesMember.id === user?.id}
              onClose={() => setPreferencesMember(null)}
              onSaved={() => {
                setPreferencesMember(null)
                setSummaryRevision(value => value + 1)
                setNotice('Your preferences for this group have been saved.')
              }}
            />}
            {confirmLeave && <GroupDialog title="Leave this group?" busy={leaving} onClose={() => setConfirmLeave(false)}>
              <p className="group-dialog-description">You’ll leave <strong>{group.name}</strong> and your preferences for this group will be removed. A member will need to add you again to rejoin.</p>
              {leaveError && <p className="group-dialog-error" role="alert">{leaveError}</p>}
              <div className="group-dialog-actions">
                <button className="group-dialog-button" disabled={leaving} data-dialog-autofocus onClick={() => setConfirmLeave(false)}>Cancel</button>
                <button className="group-dialog-button group-dialog-button-danger" disabled={leaving} onClick={leaveGroup}>{leaving ? 'Leaving…' : 'Leave group'}</button>
              </div>
            </GroupDialog>}
            {memberToRemove && <GroupDialog title="Remove this member?" busy={removing} onClose={() => setMemberToRemove(null)}>
              <p className="group-dialog-description">Remove <strong>{memberToRemove.name}</strong> from <strong>{group.name}</strong>? Their preferences for this group will also be removed. A member can add them again to rejoin.</p>
              {removeError && <p className="group-dialog-error" role="alert">{removeError}</p>}
              <div className="group-dialog-actions">
                <button className="group-dialog-button" disabled={removing} data-dialog-autofocus onClick={() => setMemberToRemove(null)}>Cancel</button>
                <button className="group-dialog-button group-dialog-button-danger" disabled={removing} onClick={removeMember}>{removing ? 'Removing…' : 'Remove member'}</button>
              </div>
            </GroupDialog>}
          </>
        )}
      </main>
    </div>
  )
}
