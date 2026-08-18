import type { NewsItem, Position, Quote, Status } from '../types';

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

export interface LoginQrcode {
  qrid: string;
  qrcode_img: string;
  error?: string;
}
export interface LoginPoll {
  ok: boolean;
  reason?: 'expired' | 'waiting' | 'confirmed';
}
export const getStatus = () => json<Status>('/api/status');
export const startLogin = () => json<LoginQrcode>('/api/login/qrcode', { method: 'POST' });
export const pollLogin = (qrid: string) =>
  json<LoginPoll>('/api/login/poll', { method: 'POST', body: JSON.stringify({ qrid }) });
export const logout = () => json<{ ok: boolean }>('/api/logout', { method: 'POST' });
export const getQuotes = () => json<Record<string, Quote>>('/api/quotes');
export const getPositions = () => json<Position[]>('/api/positions');
export const getNews = (type: string) => json<NewsItem[]>(`/api/news?type=${type}`);
export const markNewsRead = (id: string) =>
  json<{ ok: boolean }>(`/api/news/${id}/read`, { method: 'POST' });
