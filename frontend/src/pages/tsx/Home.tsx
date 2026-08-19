import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import '../css/Home.css'

export function Home() {
  const { user, signOut } = useAuth()

  return (
    <div className="home-page">
      <header className="home-header">
        <h1 className="home-title">GotAnyGames</h1>
        <div className="home-account">
          <span className="home-user-email">{user?.email}</span>
          <button
            onClick={signOut}
            className="home-sign-out-button"
          >
            Sign Out
          </button>
        </div>
      </header>

      <main className="home-content">
        <h2 className="home-welcome-title">Welcome back!</h2>
        <p className="home-welcome-prompt">What would you like to do?</p>

        <div className="home-action-grid">
          <Link
            to="/my-games"
            className="home-action-card"
          >
            <div className="home-card-icon">🎮</div>
            <h3 className="home-card-title">
              My Games
            </h3>
            <p className="home-card-description">
              Search for games, build your list, and rate them.
            </p>
          </Link>

          <div className="home-coming-soon-card">
            <div className="home-card-icon">👥</div>
            <h3 className="home-card-title">Groups</h3>
            <p className="home-card-description">
              Create groups and get recommendations together.
            </p>
            <span className="home-coming-soon-badge">
              Coming Soon
            </span>
          </div>
        </div>
      </main>
    </div>
  )
}
