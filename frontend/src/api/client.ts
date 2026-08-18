import type { NewsItem, Quote, Status } from '../types';

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

export interface WatchItem {
  code: string;
  name: string;
}
export const getStatus = () => json<Status>('/api/status');
export const getQuotes = () => json<Record<string, Quote>>('/api/quotes');
export const getNews = (type: string) => json<NewsItem[]>(`/api/news?type=${type}`);
export const markNewsRead = (id: string) =>
  json<{ ok: boolean }>(`/api/news/${id}/read`, { method: 'POST' });
export const getWatchlist = () => json<WatchItem[]>('/api/watchlist');
export const addWatchlist = (code: string) =>
  json<WatchItem[]>('/api/watchlist', { method: 'POST', body: JSON.stringify({ code }) });
export const removeWatchlist = (code: string) =>
  json<WatchItem[]>(`/api/watchlist/${code}`, { method: 'DELETE' });
