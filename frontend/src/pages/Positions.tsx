import { useApp } from '../store';

export default function Positions() {
  const positions = useApp((s) => s.positions);
  return (
    <div className="page">
      <h2>持仓明细</h2>
      <table className="tbl">
        <thead>
          <tr>
            <th>代码</th>
            <th>名称</th>
            <th>持股</th>
            <th>可用</th>
            <th>成本</th>
            <th>现价</th>
            <th>市值</th>
            <th>累计盈亏</th>
            <th>盈亏%</th>
            <th>当日盈亏</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr key={p.code}>
              <td>{p.code}</td>
              <td>{p.name}</td>
              <td>{p.quantity}</td>
              <td>{p.available}</td>
              <td>{p.cost_price.toFixed(2)}</td>
              <td>{p.current_price.toFixed(2)}</td>
              <td>¥{p.market_value.toFixed(2)}</td>
              <td style={{ color: p.profit >= 0 ? 'var(--up)' : 'var(--down)' }}>
                {p.profit >= 0 ? '+' : ''}
                {p.profit.toFixed(2)}
              </td>
              <td style={{ color: p.profit_pct >= 0 ? 'var(--up)' : 'var(--down)' }}>
                {p.profit_pct.toFixed(2)}%
              </td>
              <td style={{ color: p.day_change >= 0 ? 'var(--up)' : 'var(--down)' }}>
                {p.day_change >= 0 ? '+' : ''}
                {p.day_change.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {positions.length === 0 && <div className="muted">暂无持仓（未登录或账号无持仓）</div>}
    </div>
  );
}
