import { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import type { GroupPreferenceSummaryData } from '../../types'
import '../css/GroupPreferenceSummary.css'

interface GroupPreferenceSummaryProps {
  groupId: number
  revision: number
}

const percentageFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 })

function percentage(value: number) {
  return `${percentageFormatter.format(value)}%`
}

export function GroupPreferenceSummary({ groupId, revision }: GroupPreferenceSummaryProps) {
  const [summary, setSummary] = useState<GroupPreferenceSummaryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [retryAttempt, setRetryAttempt] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError(false)
    setSummary(null)

    async function loadSummary() {
      try {
        const data = await api.get<GroupPreferenceSummaryData>(`/groups/${groupId}/preferences/summary`)
        if (active) setSummary(data)
      } catch {
        if (active) setError(true)
      } finally {
        if (active) setLoading(false)
      }
    }

    loadSummary()
    return () => { active = false }
  }, [groupId, revision, retryAttempt])

  return (
    <div className="group-preference-summary">
      <div className="group-preference-summary-heading">
        <h2>Group preferences</h2>
        <p>See which platforms and ways to play your group shares.</p>
      </div>
      {loading ? (
        <p className="group-preference-summary-state" role="status">Loading group preferences…</p>
      ) : error ? (
        <div className="group-preference-summary-state">
          <p className="group-detail-error" role="alert">We couldn’t load the group preferences. Please try again.</p>
          <button className="group-detail-button" onClick={() => setRetryAttempt(value => value + 1)}>Try again</button>
        </div>
      ) : summary && summary.platforms.length === 0 ? (
        <div className="group-preference-summary-state">
          <p>No group preferences yet.</p>
          <p>Once members choose their platforms and ways to play, the group’s preferences will appear here.</p>
        </div>
      ) : summary && (
        <>
          <div className="group-preference-summary-explanation">
            <p>Platform percentages include all {summary.member_count} group {summary.member_count === 1 ? 'member' : 'members'}, even those who haven’t set preferences.</p>
            <p>Online and local percentages are among members who selected that platform. Members can choose both, so these percentages may add up to more than 100%.</p>
          </div>
          <ul className="group-preference-summary-platforms">
            {summary.platforms.map(platform => (
              <li key={platform.platform_id} className="group-preference-summary-platform">
                <div className="group-preference-summary-platform-heading">
                  <h3>{platform.platform_name}</h3>
                  <span className="group-preference-summary-percentage">{percentage(platform.member_percentage)}</span>
                </div>
                <p className="group-preference-summary-platform-count">{platform.member_count} of {summary.member_count} group members selected this platform</p>
                <div className="group-preference-summary-bar" aria-hidden="true">
                  <span style={{ width: `${platform.member_percentage}%` }} />
                </div>
                <dl className="group-preference-summary-modes">
                  <div>
                    <dt>Online</dt>
                    <dd><strong>{percentage(platform.online_percentage)}</strong><span>{platform.online_count} of {platform.member_count} platform members</span></dd>
                  </div>
                  <div>
                    <dt>Local / in person</dt>
                    <dd><strong>{percentage(platform.offline_percentage)}</strong><span>{platform.offline_count} of {platform.member_count} platform members</span></dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
