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

type GroupTab = typeof groupTabs[number]['id'] // Values that a group tab can have (currently only two)

export function GroupDetail() {
  const { groupId = '' } = useParams()
  const { user } = useAuth()
  return <GroupDetailContent key={`${user?.id}:${groupId}`} groupId={groupId} />
}

function GroupDetailContent({ groupId }: { groupId: string }) {
  /*
  Page showing the details for a given group
  */
  const { user, signOut } = useAuth() //Current user
  const navigate = useNavigate() //Navigation functionality
  const [group, setGroup] = useState<GroupDetailData | null>(null) //Current group
  const [loading, setLoading] = useState(true) //Overall group loading state hook
  const [error, setError] = useState<string | null>(null) // Error state hook
  const [unavailable, setUnavailable] = useState(false) //Toggles user's access to the current page
  const [retryAttempt, setRetryAttempt] = useState(0) //Triggers a retry of page loading when this hook is changed
  const [addingMember, setAddingMember] = useState(false) //Keeps track of whether the member adding dialog is open
  const [preferencesMember, setPreferencesMember] = useState<GroupMember | null>(null) //Keeps track of current member whose preferences are being viewed (null if the tab is closed)
  const [confirmLeave, setConfirmLeave] = useState(false) //Keeps track of whether the leaving confirmation dialog is open
  const [leaving, setLeaving] = useState(false) //Keeps track of whether the user is currently trying to leave the group
  const [leaveError, setLeaveError] = useState<string | null>(null) //Leaving error state hook
  const [memberToRemove, setMemberToRemove] = useState<GroupMember | null>(null) //Current user on the chopping block when the user removal dialog is open
  const [removing, setRemoving] = useState(false) //Keeps track of whether the user removal dialog is open
  const [removeError, setRemoveError] = useState<string | null>(null) //Removal error state hook
  const [notice, setNotice] = useState('') //State of the current notice at the bottom of the screen
  const [activeTab, setActiveTab] = useState<GroupTab>('members') //Currently active tab on the page 
  const [summaryRevision, setSummaryRevision] = useState(0) //Triggers an update to the group summary when this hook is changed
  const tabButtons = useRef<Partial<Record<GroupTab, HTMLButtonElement | null>>>({}) //HTML references to member and preference tab buttons
  const addMemberButton = useRef<HTMLButtonElement>(null) //HTML reference for member button

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(null)
    setUnavailable(false)

    //Loads the data for the current group
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
    if (!memberToRemove) {
      addMemberButton.current?.focus()
    }
  }, [memberToRemove])

  //Opens "are you sure?" dialog for leaving a group
  function openLeaveDialog() {
    setLeaveError(null)
    setConfirmLeave(true)
  }

  //Removes current user from the group
  async function leaveGroup() {
    if (!group || leaving) return
    setLeaving(true)
    setLeaveError(null)
    try {
      await api.del('/leave_group/', { group_id: group.id })
      navigate('/groups', { replace: true })
    } catch {
      setLeaveError('Couldn’t leave this group. Please try again.')
    } finally {
      setLeaving(false)
    }
  }


  //Removes the member (specified by memberToRemove hook) from the group 
  async function removeMember() {
    if (!group || !memberToRemove || memberToRemove.id === user?.id || removing) return
    setRemoving(true)
    setRemoveError(null)
    try {
      const updated = await api.del<GroupDetailData>(`/groups/${group.id}/members/${memberToRemove.id}`)
      setGroup(updated)
      setSummaryRevision(value => value + 1)
      setNotice(`${memberToRemove.name} has been removed from the group.`)
      setMemberToRemove(null)
    } catch {
      setRemoveError('We could not remove this member. Please try again.')
    } finally {
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
            <p className="group-detail-error">{error}</p>
            <button className="group-detail-button" onClick={() => setRetryAttempt(value => value + 1)}>Try again</button>
          </div>
        ) : group && (
          <>
            <div className="group-detail-intro">
              <h1>{group.name}</h1>
            </div>

            <div className="group-detail-layout">
              <div className="group-detail-main-column">
                <div className="group-detail-tabs" role="group">
                  {groupTabs.map((tab, index) => (
                    <button
                      key={tab.id}
                      ref={button => { tabButtons.current[tab.id] = button }}
                      id={`group-${tab.id}-tab`}
                      tabIndex={activeTab === tab.id ? 0 : -1}
                      className={`group-detail-tab${activeTab === tab.id ? ' is-active' : ''}`}
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
                        <span className="group-detail-avatar">{Array.from(member.name.trim())[0]?.toUpperCase() || '?'}</span>
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
                          <summary><span>⋮</span></summary>
                          <div className="group-detail-member-menu">
                            <button onClick={event => {
                              const menu = event.currentTarget.closest('details')
                              menu?.querySelector('summary')?.focus()
                              menu?.removeAttribute('open')
                              setPreferencesMember(member)
                            }}>
                              {member.id === user?.id ? 'Edit your preferences' : 'View preferences'}
                            </button>
                            {member.id === user?.id ? (
                              <button className="group-detail-menu-danger" onClick={event => {
                                const menu = event.currentTarget.closest('details')
                                menu?.querySelector('summary')?.focus()
                                menu?.removeAttribute('open')
                                openLeaveDialog()
                              }}>Leave group</button>
                            ) :
                             (
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
                    <span className="group-detail-add-icon">+</span>
                    Add user
                  </button>
                </section>

                <section
                  id="group-preferences-panel"
                  tabIndex={0}
                  hidden={activeTab !== 'preferences'}
                >
                  <GroupPreferenceSummary groupId={group.id} revision={summaryRevision} />
                </section>

                <div className="group-detail-recommendations">
                  <button className="group-detail-button group-detail-primary" disabled>
                    Get recommendations
                  </button>
                  <p id="group-recommendations-status">Coming soon.</p>
                </div>
              </div>

              <aside className="group-detail-sidebar">
                <section className="group-detail-action-card">
                  <span className="group-detail-action-icon">⚙</span>
                  <h2>Personal Preferences</h2>
                  <p>Set the platforms and ways you want to play with this group.</p>
                  <button className="group-detail-button" disabled={!currentMember} onClick={() => currentMember && setPreferencesMember(currentMember)}>
                    Edit your preferences
                  </button>
                </section>
                <section className="group-detail-action-card group-detail-leave-card">
                  <h2>Leave Group</h2>
                  <p>You can rejoin if invited again.</p>
                  <button className="group-detail-button group-detail-danger" onClick={openLeaveDialog}>Leave group</button>
                </section>
              </aside>
            </div>
            <p className="group-detail-notice">{notice}</p>

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
              {leaveError && <p className="group-dialog-error">{leaveError}</p>}
              <div className="group-dialog-actions">
                <button className="group-dialog-button" disabled={leaving} data-dialog-autofocus onClick={() => setConfirmLeave(false)}>Cancel</button>
                <button className="group-dialog-button group-dialog-button-danger" disabled={leaving} onClick={leaveGroup}>{leaving ? 'Leaving…' : 'Leave group'}</button>
              </div>
            </GroupDialog>}
            {memberToRemove && <GroupDialog title="Remove this member?" busy={removing} onClose={() => setMemberToRemove(null)}>
              <p className="group-dialog-description">Remove <strong>{memberToRemove.name}</strong> from <strong>{group.name}</strong>? Their preferences for this group will also be removed. A member can add them again to rejoin.</p>
              {removeError && <p className="group-dialog-error">{removeError}</p>}
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
