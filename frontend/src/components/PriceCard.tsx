import type { Quote } from '../types';

interface PriceCardProps {
  q: Quote;
}

export default function PriceCard({ q }: PriceCardProps) {
  const up = q.change >= 0;
  return (
    <div className="price-card">
      <div className="name">
        {q.name}
        <span className="code">{q.code}</span>
      </div>
      <div className="price" style={{ color: up ? 'var(--up)' : 'var(--down)' }}>
        {q.price.toFixed(2)}
      </div>
      <div className="change" style={{ color: up ? 'var(--up)' : 'var(--down)' }}>
        {up ? '+' : ''}
        {q.change.toFixed(2)} ({up ? '+' : ''}
        {q.change_pct.toFixed(2)}%)
      </div>
      <div className="muted">数据来源：新浪/腾讯</div>
    </div>
  );
}
