import type { NewsItem, Position, Quote, Status } from '../types'

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!r.ok) throw new Error(`${path}: ${r.status}`)
  return r.json() as Promise<T>
}

export const getStatus = () => json<Status>('/api/status')
export const startLogin = () => json<{ qrcode_data: string }>('/api/login/qrcode', { method: 'POST' })
export const pollLogin = () => json<{ ok: boolean }>('/api/login/poll', { method: 'POST' })
export const logout = () => json<{ ok: boolean }>('/api/logout', { method: 'POST' })
export const getQuotes = () => json<Record<string, Quote>>('/api/quotes')
export const getPositions = () => json<Position[]>('/api/positions')
export const getNews = (type: string) => json<NewsItem[]>(`/api/news?type=${type}`)
export const markNewsRead = (id: string) =>
  json<{ ok: boolean }>(`/api/news/${id}/read`, { method: 'POST' })
