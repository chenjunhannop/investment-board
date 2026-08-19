import { useEffect, useState } from 'react';
import { getDashboard } from '../api/client';
import type { DashboardData } from '../api/client';
import BigScreenPanel from '../components/BigScreenPanel';
import FundFlowChart from '../components/FundFlowChart';
import IndexMiniChart from '../components/IndexMiniChart';
import PriceCard from '../components/PriceCard';
import SectorKlineChart from '../components/SectorKlineChart';
import { useCountUp } from '../hooks/useCountUp';
import { useApp } from '../store';

const DASHBOARD_REFRESH_MS = 30000;

function IndexCard({ index }: { index: DashboardData['indices'][number] }) {
  const price = useCountUp(index.price);
  const up = index.change_pct >= 0;
  const color = up ? 'var(--up)' : 'var(--down)';
  return (
    <div className="index-card">
      <div className="index-name">{index.name}</div>
      <div className="index-price" style={{ color }}>
        {price.toFixed(2)}
      </div>
      <div className="index-change" style={{ color }}>
        {up ? '+' : ''}
        {index.change_pct.toFixed(2)}%
      </div>
      <IndexMiniChart
        points={[index.prev_close, index.open, index.price]}
        color={up ? '#e5484d' : '#2e9e6b'}
      />
    </div>
  );
}

export default function Dashboard() {
  const quotes = useApp((s) => s.quotes);
  const news = useApp((s) => s.news);
  const connected = useApp((s) => s.connected);
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
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
  const stamp = now.toLocaleString('zh-CN', { hour12: false });
  const upCount = useCountUp(dash?.market.up ?? 0);
  const downCount = useCountUp(dash?.market.down ?? 0);
  const total = upCount + downCount || 1;
  return (
    <div className="page bigscreen">
      {/* 顶部大标题区 */}
      <div className="bs-header">
        <span className={`bs-header-conn ${connected ? 'on' : ''}`}>
          ● {connected ? '实时连接' : '连接断开'}
        </span>
        <h1>市场数据中心</h1>
        <span className="bs-header-time">{stamp}</span>
      </div>
      {/* A + G：指数带 + 市场温度 */}
      <div className="bs-indices">
        {dash?.indices.map((ix) => (
          <IndexCard key={ix.code} index={ix} />
        ))}
        <div className="market-temp">
          <div className="temp-title">市场温度</div>
          <div className="temp-bar">
            <div className="temp-up" style={{ width: `${(upCount / total) * 100}%` }} />
          </div>
          <div className="temp-nums">
            <span style={{ color: 'var(--up)' }}>↑ {Math.round(upCount)}</span>
            <span style={{ color: 'var(--down)' }}>↓ {Math.round(downCount)}</span>
          </div>
        </div>
      </div>
      {/* 对称三分区：左排行 / 中K线主视觉 / 右资金 */}
      <div className="bs-main">
        <div className="bs-left">
          <BigScreenPanel title="板块涨幅榜">
            <table className="tbl sector-rank">
              <tbody>
                {dash?.sectors.top_gainers.map((s) => (
                  <tr key={s.secid}>
                    <td>{s.name}</td>
                    <td style={{ color: 'var(--up)' }}>+{s.change_pct.toFixed(2)}%</td>
                    <td className="muted">{s.leader}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </BigScreenPanel>
          <BigScreenPanel title="板块跌幅榜">
            <table className="tbl sector-rank">
              <tbody>
                {dash?.sectors.top_losers.map((s) => (
                  <tr key={s.secid}>
                    <td>{s.name}</td>
                    <td style={{ color: 'var(--down)' }}>{s.change_pct.toFixed(2)}%</td>
                    <td className="muted">{s.leader}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </BigScreenPanel>
        </div>
        <BigScreenPanel title="重点板块走势（涨幅前三 / 跌幅前三）">
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
        </BigScreenPanel>
        <div className="bs-right">
          <BigScreenPanel title="板块资金流向（主力净流入 TOP）">
            <FundFlowChart data={dash?.sectors.fund_flow ?? []} />
          </BigScreenPanel>
        </div>
      </div>
      {/* 底部：E 自选滚动 + F 新闻 */}
      <div className="bs-bottom">
        <BigScreenPanel title="自选实时行情" className="self-strip">
          <div className="marquee">
            <div className="marquee-inner">
              {Object.values(quotes).map((q) => (
                <div
                  key={q.code}
                  className="cell"
                  style={{ display: 'inline-block', marginRight: 10 }}
                >
                  <PriceCard q={q} />
                </div>
              ))}
            </div>
          </div>
        </BigScreenPanel>
        <BigScreenPanel title="新闻快讯">
          <div className="news-feed">
            {news.slice(0, 12).map((n) => (
              <div key={n.id} className="news-line">
                <span className="muted">{n.source}</span> {n.title}
              </div>
            ))}
          </div>
        </BigScreenPanel>
      </div>
    </div>
  );
}
