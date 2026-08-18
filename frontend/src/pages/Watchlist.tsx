import { useState } from 'react';
import PriceCard from '../components/PriceCard';
import { useApp } from '../store';

export default function Watchlist() {
  const quotes = useApp((s) => s.quotes);
  const watchlist = useApp((s) => s.watchlist);
  const addToWatchlist = useApp((s) => s.addToWatchlist);
  const removeFromWatchlist = useApp((s) => s.removeFromWatchlist);
  const [code, setCode] = useState('');

  const submit = async () => {
    if (!/^\d{6}$/.test(code.trim())) return;
    await addToWatchlist(code.trim());
    setCode('');
  };

  return (
    <div className="page">
      <h2>自选</h2>
      <div className="watchlist-add">
        <input
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="输入 6 位股票代码，如 600519"
          maxLength={6}
        />
        <button onClick={submit}>添加</button>
      </div>
      <div className="grid">
        {watchlist.map((w) => {
          const q = quotes[w.code];
          if (!q) return null;
          return (
            <div key={w.code} className="cell">
              <PriceCard q={q} />
              <button className="remove" onClick={() => removeFromWatchlist(w.code)}>
                删除
              </button>
            </div>
          );
        })}
      </div>
      {watchlist.length === 0 && <div className="muted">暂无自选，输入代码添加</div>}
    </div>
  );
}
