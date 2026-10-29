import axios from 'axios'

const env = (import.meta as unknown as { env?: Record<string, string | undefined> }).env
// Local dev (Vite on :5173) talks to the API on :8000; the deployed single-URL build
// is served by the API itself, so it uses a same-origin path.
export const API_BASE = env?.VITE_API_URL
  || (['5173', '4173'].includes(window.location.port) ? 'http://localhost:8000/api/v1' : '/api/v1')

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('aicte_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !String(error.config?.url ?? '').includes('/auth/login')) {
      localStorage.removeItem('aicte_token')
      if (window.location.pathname !== '/login') window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export function apiError(err: unknown, fallback = 'Request failed'): string {
  const e = err as { response?: { data?: { detail?: unknown } }; message?: string }
  const d = e?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x: { msg?: string }) => x.msg).filter(Boolean).join('; ') || fallback
  return e?.message === 'Network Error' ? 'Cannot reach the NYAYA SETU API server' : fallback
}
