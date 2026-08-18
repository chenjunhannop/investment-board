import type { Position } from '../types';

interface PositionsSummaryProps {
  positions: Position[];
}

export default function PositionsSummary({ positions }: PositionsSummaryProps) {
  const totalProfit = positions.reduce((s, p) => s + p.profit, 0);
  const totalValue = positions.reduce((s, p) => s + p.market_value, 0);
  return (
    <div className="summary-card">
      <div>
        持仓市值 <b>¥{totalValue.toFixed(2)}</b>
      </div>
      <div style={{ color: totalProfit >= 0 ? 'var(--up)' : 'var(--down)' }}>
        累计盈亏{' '}
        <b>
          {totalProfit >= 0 ? '+' : ''}
          {totalProfit.toFixed(2)}
        </b>
      </div>
    </div>
  );
}
