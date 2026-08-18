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
export interface Position {
  code: string;
  name: string;
  quantity: number;
  cost_price: number;
  available: number;
  current_price: number;
  market_value: number;
  profit: number;
  profit_pct: number;
  day_change: number;
  day_change_pct: number;
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
  logged_in: boolean;
  sources: Record<string, string>;
  ths: { status: string };
}
export interface WsEvent {
  type: string;
  data: unknown;
}
