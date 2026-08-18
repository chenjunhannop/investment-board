import { create } from 'zustand';
import { getNews, getPositions, getQuotes, getStatus, markNewsRead } from './api/client';
import { connectWS } from './api/ws';
import type { NewsItem, Position, Quote, Status } from './types';

interface AppState {
  quotes: Record<string, Quote>;
  positions: Position[];
  news: NewsItem[];
  status: Status | null;
  connected: boolean;
  init: () => void;
  setQuotes: (q: Record<string, Quote>) => void;
  setPositions: (p: Position[]) => void;
  setNews: (n: NewsItem[]) => void;
  markRead: (id: string) => void;
  refresh: () => Promise<void>;
}

export const useApp = create<AppState>((set, get) => ({
  quotes: {},
  positions: [],
  news: [],
  status: null,
  connected: false,
  init() {
    connectWS((ev) => {
      const s = get();
      if (ev.type === 'quotes') s.setQuotes(ev.data as Record<string, Quote>);
      if (ev.type === 'positions') s.setPositions(ev.data as Position[]);
      if (ev.type === 'news') s.setNews(ev.data as NewsItem[]);
    });
    get().refresh();
  },
  setQuotes: (q) => set({ quotes: q }),
  setPositions: (p) => set({ positions: p }),
  setNews: (n) => set({ news: n }),
  markRead(id) {
    set({ news: get().news.map((x) => (x.id === id ? { ...x, read: true } : x)) });
    markNewsRead(id);
  },
  async refresh() {
    const [quotes, positions, news, status] = await Promise.all([
      getQuotes(),
      getPositions(),
      getNews('all'),
      getStatus(),
    ]);
    set({ quotes, positions, news, status, connected: true });
  },
}));
