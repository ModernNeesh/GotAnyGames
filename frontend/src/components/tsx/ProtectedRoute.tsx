import { Navigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import '../css/ProtectedRoute.css'

export function ProtectedRoute({ children }: { children: React.ReactNode }) { 
  /*
  Redirects user if they're unauthenticated or still loading
  - If unauthenticated, redirects them to login
  - If loading, replaces component with a loading screen
  */

  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="protected-route-loading">
        Loading...
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />

  return <>{children}</>
}
