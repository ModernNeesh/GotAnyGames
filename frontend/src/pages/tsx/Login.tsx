import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import '../css/Login.css'

export function Login() {
  const { user, loading, signIn, signUp, signInWithOAuth } = useAuth()
  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  //If loading, replaces component with a loading screen
  if (loading) {
    return (
      <div className="login-loading">
        Loading...
      </div>
    )
  }

  //When user signs in, redirects them to home page
  if (user) return <Navigate to="/" replace />

  async function handleSubmit(e: FormEvent) {
    /*
    Handles the form submission for signing in or signing up.

    Inputs:
    - e: The form submission event

    Returns:
    - None
    */
    e.preventDefault()
    setError(null)
    setSubmitting(true)

    //Sign the user in/up
    const signInError = isSignUp
      ? await signUp(email, password)
      : await signIn(email, password)

    //If an error occurred during sign in/up, display it to the user
    if (signInError) setError(signInError)
    setSubmitting(false)
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h1 className="login-title">GotAnyGames</h1>
        <p className="login-subtitle">
          {isSignUp ? 'Create your account' : 'Sign in to your account'}
        </p>

        {/*Email and password block*/}
        <form onSubmit={handleSubmit} className="login-form">
          <div>
            <label className="login-label">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="login-input"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="login-label">Password</label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="login-input"
              placeholder="••••••••"
            />
          </div>  

          {/*Display error message from latest sign-in/sign-up attempt (if it exists)*/}
          {error && <p className="login-error-message">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="login-submit-button"
          >
            {submitting ? 'Please wait...' : isSignUp ? 'Sign Up' : 'Sign In'}
          </button>
        </form>

        <div className="login-divider">
          <div className="login-divider-line">
            <div className="login-divider-rule" />
          </div>
          <div className="login-divider-label-row">
            <span className="login-divider-label">or continue with</span>
          </div>
        </div>

        <button
          onClick={() => signInWithOAuth('google')}
          className="login-oauth-button"
        >
          Google
        </button>

        <p className="login-mode-prompt">
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            onClick={() => { setIsSignUp(!isSignUp); setError(null) }}
            className="login-mode-button"
          >
            {isSignUp ? 'Sign In' : 'Sign Up'}
          </button>
        </p>
      </div>
    </div>
  )
}
