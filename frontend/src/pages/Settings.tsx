import { useApp } from '../store';

export default function Settings() {
  const status = useApp((s) => s.status);
  return (
    <div className="page">
      <h2>设置</h2>
      <section className="panel">
        <h3>数据源健康</h3>
        <ul>
          <li>行情源：{status?.sources?.market ?? '—'}</li>
          <li>新闻源：{status?.sources?.news ?? '—'}</li>
        </ul>
        <p className="muted">
          行情来源：新浪财经 / 腾讯财经（公开接口）；新闻来源：东方财富公告 / 财联社电报
        </p>
      </section>
    </div>
  );
}
