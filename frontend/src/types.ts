export interface Quote {
  code: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  open: number;
  high: number;
  low: number;
  prev_close: number;
  volume: number;
  amount: number;
  ts: string;
}
export interface NewsItem {
  id: string;
  source: string;
  title: string;
  url: string;
  published_at: string;
  news_type: 'individual' | 'global';
  related_codes: string[];
  read: boolean;
}
export interface Status {
  sources: Record<string, string>;
}
export type WsEvent =
  | { type: 'quotes'; data: Record<string, Quote> }
  | { type: 'news'; data: NewsItem[] }
  | { type: 'source_status'; data: Record<string, string> };

export interface WatchItem {
  code: string;
  name: string;
}
export interface WatchGroup {
  name: string;
  stocks: WatchItem[];
}
export interface WatchlistData {
  version: number;
  groups: WatchGroup[];
}
