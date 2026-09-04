import { supabase } from './supabase'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function authHeaders(): Promise<Record<string, string>> {
  /*
  Returns headers for API requests

  Inputs: 
  - None

  Returns: 
  - Headers object; includes content type and authorization header
  */
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }
  return headers
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  /*
  General function to make an API request

  Inputs: 
  - method: HTTP method (GET, POST, PATCH, DELETE)
  - path: API endpoint path
  - body: Request body (optional)

  Returns: 
  - Response data as JSON promise (<T> allows for flexible response typing)
  */
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: await authHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`API ${res.status}: ${detail}`)
  }
  return res.json()
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
}
