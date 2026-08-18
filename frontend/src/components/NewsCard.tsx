import type { NewsItem } from '../types'

export default function NewsCard({ item, onRead }: { item: NewsItem; onRead: () => void }) {
  return (
    <a className={`news-card ${item.read ? 'read' : ''}`}
       href={item.url} target="_blank" rel="noreferrer" onClick={onRead}>
      <div className="news-title">{item.title}</div>
      <div className="news-meta">
        <span>{item.source === 'cls' ? '财联社' : '东财公告'}</span>
        <span>{item.published_at}</span>
        {item.related_codes.length > 0 &&
          <span>相关：{item.related_codes.join(', ')}</span>}
      </div>
    </a>
  )
}
