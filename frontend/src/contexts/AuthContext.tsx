import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import type { User, Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { api } from '../lib/api'

interface AuthContextType {
  // Data handed down to children by AuthContext provider (through useAuth hook)
  user: User | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<string | null>
  signUp: (email: string, password: string) => Promise<string | null>
  signInWithOAuth: (provider: 'google' | 'github') => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

function autoDisplayName(session: Session): string {
  /*
  Automatically generate display name for user based on metadata

  Inputs:
  - session: Supabase session object

  Returns: 
  - Display name string
  */
  const meta = session.user.user_metadata
  return meta?.full_name ?? meta?.name ?? session.user.email?.split('@')[0] ?? 'User'
}

async function syncUser(session: Session) {
  /*
  Creates user if they don't already exist

  Inputs:
  - session: Supabase session object

  Returns:
  - None
  */
  try {
    await api.post(`/auth/sync?auto_display_name=${encodeURIComponent(autoDisplayName(session))}`)
  } catch {
    // sync failure shouldn't block the app
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  /*
  Provides authentication context to children components

  Inputs:
  - children: React components that will have access to AuthContext

  Returns:
  - AuthContext.Provider wrapping children components
  */


  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    //On initial load, check if user is already logged in and sync
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      if (session) syncUser(session)
      setLoading(false)
    })

    //When auth state changes (login, logout, etc.), update user and sync.
    //This is done by a subscription to the auth state change event
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      if (session) syncUser(session)
    })

    //Remove the subscription on unmount (in this case, when the app is closed or refreshed)
    return () => subscription.unsubscribe()
  }, [])

  async function signIn(email: string, password: string): Promise<string | null> {
    /*
    Sign in user with email and password

    Inputs:
    - email: User's email
    - password: User's password

    Returns:
    - Error message string if sign in fails, or null if successful
    */
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    return error ? error.message : null
  }

  async function signUp(email: string, password: string): Promise<string | null> {
    /*
    Sign up user with email and password
    Inputs:
    - email: User's email
    - password: User's password
    Returns:
    - Error message string if sign up fails, or null if successful
    */
    const { error } = await supabase.auth.signUp({ email, password })
    return error ? error.message : null
  }

  async function signInWithOAuth(provider: 'google' | 'github') {
    /*
    Sign in user with OAuth provider (Google or GitHub)
    Inputs:
    - provider: OAuth provider ('google' or 'github')
    Returns:
    - None
    */

    await supabase.auth.signInWithOAuth({ provider })
  }

  async function signOut() {
    //i cannot possibly need a comment here
    await supabase.auth.signOut()
  }

  return (
    <AuthContext.Provider value={{ user, loading, signIn, signUp, signInWithOAuth, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  /*
  Hook to access authentication context in child components
  Inputs:
  - None

  Returns:
  - AuthContext value (user, loading, signIn, signUp, signInWithOAuth, signOut)
  */

  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
