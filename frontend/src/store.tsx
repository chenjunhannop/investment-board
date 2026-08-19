import { create } from 'zustand';
import {
  addGroup,
  addStock,
  getNews,
  getQuotes,
  getStatus,
  getWatchlist,
  markNewsRead,
  removeGroup,
  removeStock,
  renameGroup,
} from './api/client';
import { connectWS } from './api/ws';
import type { NewsItem, Quote, Status, WatchlistData } from './types';

interface AppState {
  quotes: Record<string, Quote>;
  watchlist: WatchlistData;
  news: NewsItem[];
  status: Status | null;
  connected: boolean;
  init: () => void;
  setQuotes: (q: Record<string, Quote>) => void;
  setNews: (n: NewsItem[]) => void;
  markRead: (id: string) => void;
  loadWatchlist: () => Promise<void>;
  addGroup: (name: string) => Promise<void>;
  renameGroup: (name: string, newName: string) => Promise<void>;
  removeGroup: (name: string) => Promise<void>;
  addToWatchlist: (group: string, code: string) => Promise<void>;
  removeFromWatchlist: (group: string, code: string) => Promise<void>;
  refresh: () => Promise<void>;
}

let wsStarted = false;

export const useApp = create<AppState>((set, get) => ({
  quotes: {},
  watchlist: { version: 2, groups: [] },
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
  async addGroup(name) {
    set({ watchlist: await addGroup(name) });
  },
  async renameGroup(name, newName) {
    set({ watchlist: await renameGroup(name, newName) });
  },
  async removeGroup(name) {
    set({ watchlist: await removeGroup(name) });
  },
  async addToWatchlist(group, code) {
    set({ watchlist: await addStock(group, code) });
  },
  async removeFromWatchlist(group, code) {
    set({ watchlist: await removeStock(group, code) });
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
