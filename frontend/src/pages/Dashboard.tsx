import { useEffect, useState } from 'react';
import { getDashboard } from '../api/client';
import type { DashboardData } from '../api/client';
import FundFlowChart from '../components/FundFlowChart';
import IndexMiniChart from '../components/IndexMiniChart';
import PriceCard from '../components/PriceCard';
import SectorKlineChart from '../components/SectorKlineChart';
import { useApp } from '../store';

const DASHBOARD_REFRESH_MS = 30000;

export default function Dashboard() {
  const quotes = useApp((s) => s.quotes);
  const news = useApp((s) => s.news);
  const connected = useApp((s) => s.connected);
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 60000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const d = await getDashboard();
        if (alive) setDash(d);
      } catch {
        /* 保留上次快照 */
      }
    };
    load();
    const t = setInterval(load, DASHBOARD_REFRESH_MS);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);
  const stamp = now.toLocaleTimeString('zh-CN', { hour12: false });
  const upCount = dash?.market.up ?? 0;
  const downCount = dash?.market.down ?? 0;
  const total = upCount + downCount || 1;
  const trend = (p: number[]) => (p.length >= 2 ? p : [0, 0]);
  return (
    <div className="page bigscreen">
      <div className="status-bar">
        <span className={`dot ${connected ? 'on' : ''}`} />
        <span className="conn">{connected ? '实时连接中' : '连接断开，重连中…'}</span>
        <span className="stamp">{stamp}</span>
      </div>
      {/* A. 指数区 + G. 温度条 */}
      <div className="bigscreen-top">
        {dash?.indices.map((ix) => (
          <div key={ix.code} className="index-card">
            <div className="index-name">{ix.name}</div>
            <div
              className="index-price"
              style={{ color: ix.change_pct >= 0 ? 'var(--up)' : 'var(--down)' }}
            >
              {ix.price.toFixed(2)}
            </div>
            <div
              className="index-change"
              style={{ color: ix.change_pct >= 0 ? 'var(--up)' : 'var(--down)' }}
            >
              {ix.change_pct >= 0 ? '+' : ''}
              {ix.change_pct.toFixed(2)}%
            </div>
            <IndexMiniChart
              points={trend([ix.prev_close, ix.open, ix.price])}
              color={ix.change_pct >= 0 ? '#e5484d' : '#2e9e6b'}
            />
          </div>
        ))}
        <div className="market-temp">
          <div className="temp-title">市场温度</div>
          <div className="temp-bar">
            <div className="temp-up" style={{ width: `${(upCount / total) * 100}%` }} />
          </div>
          <div className="temp-nums">
            <span style={{ color: 'var(--up)' }}>↑ {upCount}</span>
            <span style={{ color: 'var(--down)' }}>↓ {downCount}</span>
          </div>
        </div>
      </div>
      {/* 中部：D 走势图（主区） + 侧边 B/C */}
      <div className="bigscreen-mid">
        <div className="kline-area">
          <h3>重点板块走势（涨幅前三 / 跌幅前三）</h3>
          <div className="kline-grid">
            {dash?.kline.top3_gainers.map((k) => (
              <div key={k.secid} className="kline-card">
                <div className="kline-title" style={{ color: 'var(--up)' }}>
                  {k.name} +{k.change_pct.toFixed(2)}%
                </div>
                <SectorKlineChart name={k.name} klines={k.klines} up />
              </div>
            ))}
            {dash?.kline.top3_losers.map((k) => (
              <div key={k.secid} className="kline-card">
                <div className="kline-title" style={{ color: 'var(--down)' }}>
                  {k.name} {k.change_pct.toFixed(2)}%
                </div>
                <SectorKlineChart name={k.name} klines={k.klines} up={false} />
              </div>
            ))}
          </div>
        </div>
        <div className="side-area">
          <div className="panel">
            <h3>板块涨跌排行</h3>
            <table className="tbl sector-rank">
              <thead>
                <tr>
                  <th>板块</th>
                  <th>涨跌幅</th>
                  <th>领涨</th>
                </tr>
              </thead>
              <tbody>
                {dash?.sectors.top_gainers.map((s) => (
                  <tr key={s.secid}>
                    <td>{s.name}</td>
                    <td style={{ color: 'var(--up)' }}>+{s.change_pct.toFixed(2)}%</td>
                    <td className="muted">{s.leader}</td>
                  </tr>
                ))}
                {dash?.sectors.top_losers.map((s) => (
                  <tr key={s.secid}>
                    <td>{s.name}</td>
                    <td style={{ color: 'var(--down)' }}>{s.change_pct.toFixed(2)}%</td>
                    <td className="muted">{s.leader}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="panel">
            <h3>板块资金流向（主力净流入 TOP）</h3>
            <FundFlowChart data={dash?.sectors.fund_flow ?? []} />
          </div>
        </div>
      </div>
      {/* 底部：E 自选 + F 新闻 */}
      <div className="bigscreen-bottom">
        <div className="panel self-strip">
          <h3>自选实时行情</h3>
          <div className="grid">
            {Object.values(quotes)
              .slice(0, 12)
              .map((q) => (
                <div key={q.code} className="cell">
                  <PriceCard q={q} />
                </div>
              ))}
          </div>
        </div>
        <div className="panel news-strip">
          <h3>新闻快讯</h3>
          <div className="news-feed">
            {news.slice(0, 12).map((n) => (
              <div key={n.id} className="news-line">
                <span className="muted">{n.source}</span> {n.title}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
