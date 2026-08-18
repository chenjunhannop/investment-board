import { useEffect, useState } from 'react';
import PriceCard from '../components/PriceCard';
import PositionsSummary from '../components/PositionsSummary';
import Sparkline from '../components/Sparkline';
import { useApp } from '../store';

export default function Dashboard() {
  const quotes = useApp((s) => s.quotes);
  const positions = useApp((s) => s.positions);
  const connected = useApp((s) => s.connected);
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(t);
  }, []);
  const stamp = now.toLocaleTimeString('zh-CN', { hour12: false });
  const list = Object.values(quotes);
  return (
    <div className="page">
      <div className="status-bar">
        <span className={`dot ${connected ? 'on' : ''}`} />
        <span className="conn">{connected ? '实时连接中' : '连接断开，重连中…'}</span>
        <span className="stamp">源: 新浪·腾讯 · {stamp}</span>
      </div>
      <PositionsSummary positions={positions} />
      <h2>自选实时行情</h2>
      <div className="grid">
        {list.map((q) => (
          <div key={q.code} className="cell">
            <PriceCard q={q} />
            <Sparkline data={[q.prev_close, q.open, q.price]} />
          </div>
        ))}
        {list.length === 0 && <div className="muted">暂无行情数据（未登录时无自选，行情为空）</div>}
      </div>
    </div>
  );
}
