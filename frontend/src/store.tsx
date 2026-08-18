import { create } from 'zustand';
import {
  addWatchlist,
  getNews,
  getQuotes,
  getStatus,
  getWatchlist,
  markNewsRead,
  removeWatchlist,
} from './api/client';
import type { WatchItem } from './api/client';
import { connectWS } from './api/ws';
import type { NewsItem, Quote, Status } from './types';

interface AppState {
  quotes: Record<string, Quote>;
  watchlist: WatchItem[];
  news: NewsItem[];
  status: Status | null;
  connected: boolean;
  init: () => void;
  setQuotes: (q: Record<string, Quote>) => void;
  setNews: (n: NewsItem[]) => void;
  markRead: (id: string) => void;
  loadWatchlist: () => Promise<void>;
  addToWatchlist: (code: string) => Promise<void>;
  removeFromWatchlist: (code: string) => Promise<void>;
  refresh: () => Promise<void>;
}

let wsStarted = false;

export const useApp = create<AppState>((set, get) => ({
  quotes: {},
  watchlist: [],
  news: [],
  status: null,
  connected: false,
  init() {
    // init 幂等：只在首次调用时建立 WebSocket，避免 StrictMode 双调用重复连接
    if (!wsStarted) {
      wsStarted = true;
      connectWS((ev) => {
        const s = get();
        if (ev.type === 'quotes') s.setQuotes(ev.data);
        if (ev.type === 'news') s.setNews(ev.data);
      });
    }
    get().refresh();
  },
  setQuotes: (q) => set({ quotes: q }),
  setNews: (n) => set({ news: n }),
  markRead(id) {
    set({ news: get().news.map((x) => (x.id === id ? { ...x, read: true } : x)) });
    markNewsRead(id);
  },
  async loadWatchlist() {
    set({ watchlist: await getWatchlist() });
  },
  async addToWatchlist(code) {
    set({ watchlist: await addWatchlist(code) });
  },
  async removeFromWatchlist(code) {
    set({ watchlist: await removeWatchlist(code) });
  },
  async refresh() {
    const [quotes, news, status, watchlist] = await Promise.all([
      getQuotes(),
      getNews('all'),
      getStatus(),
      getWatchlist(),
    ]);
    set({ quotes, news, status, watchlist, connected: true });
  },
}));
