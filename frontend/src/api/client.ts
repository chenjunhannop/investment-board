import type { NewsItem, Quote, Status, WatchlistData } from '../types';

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

export const getStatus = () => json<Status>('/api/status');
export const getQuotes = () => json<Record<string, Quote>>('/api/quotes');
export const getNews = (type: string) => json<NewsItem[]>(`/api/news?type=${type}`);
export const markNewsRead = (id: string) =>
  json<{ ok: boolean }>(`/api/news/${id}/read`, { method: 'POST' });
export const getWatchlist = () => json<WatchlistData>('/api/watchlist');
export const addGroup = (name: string) =>
  json<WatchlistData>('/api/watchlist/groups', {
    method: 'POST',
    body: JSON.stringify({ name }),
  });
export const renameGroup = (name: string, newName: string) =>
  json<WatchlistData>(`/api/watchlist/groups/${encodeURIComponent(name)}`, {
    method: 'PUT',
    body: JSON.stringify({ new_name: newName }),
  });
export const removeGroup = (name: string) =>
  json<WatchlistData>(`/api/watchlist/groups/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  });
export const addStock = (group: string, code: string) =>
  json<WatchlistData>('/api/watchlist/stocks', {
    method: 'POST',
    body: JSON.stringify({ group, code }),
  });
export const removeStock = (group: string, code: string) =>
  json<WatchlistData>(`/api/watchlist/stocks/${encodeURIComponent(group)}/${code}`, {
    method: 'DELETE',
  });

export interface IndexSnapshot {
  code: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  high: number;
  low: number;
  open: number;
  prev_close: number;
  kline: Array<Array<string | number>>;
}
export interface SectorRow {
  secid: string;
  name: string;
  change_pct: number;
  fund_flow: number;
  leader: string;
  leader_code: string;
  stocks: number;
}
export interface SectorKline {
  secid: string;
  name: string;
  change_pct: number;
  klines: Array<Array<string | number>>;
}
export interface DashboardData {
  indices: IndexSnapshot[];
  market: { up: number; down: number };
  sectors: {
    top_gainers: SectorRow[];
    top_losers: SectorRow[];
    fund_flow: SectorRow[];
  };
  kline: { top3_gainers: SectorKline[]; top3_losers: SectorKline[] };
}
export const getDashboard = () => json<DashboardData>('/api/dashboard');
