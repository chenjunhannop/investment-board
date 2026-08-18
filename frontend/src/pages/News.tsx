import { useState } from 'react';
import NewsCard from '../components/NewsCard';
import { useApp } from '../store';

type NewsTab = 'all' | 'individual' | 'global';

const TAB_LABELS: Record<NewsTab, string> = {
  all: '全部',
  individual: '个股',
  global: '全局快讯',
};

export default function News() {
  const news = useApp((s) => s.news);
  const markRead = useApp((s) => s.markRead);
  const [tab, setTab] = useState<NewsTab>('all');
  const items = news.filter((n) => tab === 'all' || n.news_type === tab);
  return (
    <div className="page">
      <h2>新闻</h2>
      <div className="tabs">
        {(['all', 'individual', 'global'] as const).map((t) => (
          <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>
      <div className="news-list">
        {items.map((n) => (
          <NewsCard key={n.id} item={n} onRead={() => markRead(n.id)} />
        ))}
        {items.length === 0 && <div className="muted">暂无新闻</div>}
      </div>
    </div>
  );
}
