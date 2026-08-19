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
const NEWS_PAGE_MS = 8000;
const NEWS_PAGE_SIZE = 4;

function IndexCard({ index }: { index: DashboardData['indices'][number] }) {
  const price = useCountUp(index.price);
  const up = index.change_pct >= 0;
  const color = up ? 'var(--up)' : 'var(--down)';
  const priceText = price.toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return (
    <div className="index-card">
      <div className="index-name">{index.name}</div>
      <div className="index-price" style={{ color }}>
        {priceText}
      </div>
      <div className="index-change" style={{ color }}>
        {up ? '+' : ''}
        {index.change_pct.toFixed(2)}%
      </div>
      <div className="index-ohlc">
        今开 {index.open.toFixed(2)} · 昨收 {index.prev_close.toFixed(2)}
      </div>
      <IndexMiniChart
        points={[index.prev_close, index.open, index.price]}
        color={up ? '#e5484d' : '#2e9e6b'}
      />
    </div>
  );
}

function SectorRankTable({
  rows,
  up,
}: {
  rows: DashboardData['sectors']['top_gainers'];
  up: boolean;
}) {
  const color = up ? 'var(--up)' : 'var(--down)';
  const sign = up ? '+' : '';
  return (
    <table className="tbl sector-rank">
      <tbody>
        {rows.map((s, i) => (
          <tr key={s.secid}>
            <td className="rank-num">{(i + 1).toString().padStart(2, '0')}</td>
            <td>{s.name}</td>
            <td className="rank-pct" style={{ color }}>
              {sign}
              {s.change_pct.toFixed(2)}%
            </td>
            <td className="muted rank-leader">{s.leader}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function Dashboard() {
  const quotes = useApp((s) => s.quotes);
  const news = useApp((s) => s.news);
  const watchlist = useApp((s) => s.watchlist);
  const connected = useApp((s) => s.connected);
  const [dash, setDash] = useState<DashboardData | null>(null);
  const [now, setNow] = useState(() => new Date());
  const [newsPage, setNewsPage] = useState(0);

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

  // 持仓过滤：底部自选行情只看"持仓"文件夹
  const holdingsGroup = watchlist.groups.find((g) => g.name === '持仓');
  const holdingCodes = new Set((holdingsGroup?.stocks ?? []).map((s) => s.code));
  const holdings = Object.values(quotes).filter((q) => holdingCodes.has(q.code));

  // 新闻翻页轮播（8s/页，4 条/页）
  const newsList = news.slice(0, 12);
  const newsPages = Math.max(1, Math.ceil(newsList.length / NEWS_PAGE_SIZE));
  useEffect(() => {
    const t = setInterval(() => setNewsPage((p) => (p + 1) % newsPages), NEWS_PAGE_MS);
    return () => clearInterval(t);
  }, [newsPages]);
  const pageNews = newsList.slice(newsPage * NEWS_PAGE_SIZE, (newsPage + 1) * NEWS_PAGE_SIZE);

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
      {/* KPI 带：指数 + 市场温度（严格等高） */}
      <div className="bs-indices">
        {dash?.indices.map((ix) => (
          <IndexCard key={ix.code} index={ix} />
        ))}
        <div className="market-temp">
          <div className="temp-title">市场温度 · 涨跌家数</div>
          <div className="temp-bar">
            <div className="temp-up" style={{ width: `${(upCount / total) * 100}%` }} />
          </div>
          <div className="temp-nums">
            <span style={{ color: 'var(--up)' }}>↑ {Math.round(upCount)}</span>
            <span style={{ color: 'var(--down)' }}>↓ {Math.round(downCount)}</span>
          </div>
        </div>
      </div>
      {/* 中部主区：左排行 / 中K线主视觉 / 右资金（等高） */}
      <div className="bs-main">
        <div className="bs-left">
          <BigScreenPanel title="板块涨幅榜">
            <SectorRankTable rows={dash?.sectors.top_gainers ?? []} up />
          </BigScreenPanel>
          <BigScreenPanel title="板块跌幅榜">
            <SectorRankTable rows={dash?.sectors.top_losers ?? []} up={false} />
          </BigScreenPanel>
        </div>
        <BigScreenPanel title="重点板块走势（涨幅前三 / 跌幅前三）" className="bs-kline-panel">
          <div className="kline-block">
            <div className="kline-block-label" style={{ color: 'var(--up)' }}>
              涨幅前三
            </div>
            <div className="kline-grid">
              {dash?.kline.top3_gainers.map((k) => (
                <div key={k.secid} className="kline-card">
                  <div className="kline-title" style={{ color: 'var(--up)' }}>
                    {k.name} +{k.change_pct.toFixed(2)}%
                  </div>
                  <div className="chart-wrap">
                    <SectorKlineChart name={k.name} klines={k.klines} up />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="kline-block">
            <div className="kline-block-label" style={{ color: 'var(--down)' }}>
              跌幅前三
            </div>
            <div className="kline-grid">
              {dash?.kline.top3_losers.map((k) => (
                <div key={k.secid} className="kline-card">
                  <div className="kline-title" style={{ color: 'var(--down)' }}>
                    {k.name} {k.change_pct.toFixed(2)}%
                  </div>
                  <div className="chart-wrap">
                    <SectorKlineChart name={k.name} klines={k.klines} up={false} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </BigScreenPanel>
        <div className="bs-right">
          <BigScreenPanel title="板块资金流向（主力净流入 · 亿元）">
            <FundFlowChart data={dash?.sectors.fund_flow ?? []} />
          </BigScreenPanel>
        </div>
      </div>
      {/* 底部：持仓行情（静态）+ 新闻（翻页轮播） */}
      <div className="bs-bottom">
        <BigScreenPanel title="我的持仓" className="self-strip">
          <div className="holdings-grid">
            {holdings.map((q) => {
              const up = q.change >= 0;
              const color = up ? 'var(--up)' : 'var(--down)';
              return (
                <div key={q.code} className="holdings-card">
                  <div className="holdings-name">{q.name}</div>
                  <div className="holdings-price" style={{ color }}>
                    {q.price.toFixed(2)}
                  </div>
                  <div className="holdings-change" style={{ color }}>
                    {up ? '+' : ''}
                    {q.change_pct.toFixed(2)}%
                  </div>
                </div>
              );
            })}
          </div>
          {holdings.length === 0 && <div className="muted">暂无持仓行情</div>}
        </BigScreenPanel>
        <BigScreenPanel title={`新闻快讯（${newsPage + 1}/${newsPages}）`}>
          <div className="news-feed">
            {pageNews.map((n) => (
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
